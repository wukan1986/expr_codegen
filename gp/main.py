import os
import sys
from pathlib import Path

# 修改当前目录到上层目录，方便跨不同IDE中使用
pwd = str(Path(__file__).parents[1])
os.chdir(pwd)
sys.path.append(pwd)
# ===============
import operator
import pickle
import random
import time
from itertools import count

import numpy as np
import polars as pl
import polars.selectors as cs
from deap import base, creator, gp, tools
from loguru import logger

from examples.sympy_define import *
from expr_codegen.expr import safe_eval, is_meaningless
from expr_codegen.tool import ExprTool
from gp.custom import add_constants, add_operators, add_factors
from gp.helper import stringify_for_sympy, is_invalid

_ = Eq
# ======================================
# 每代计数
GEN_COUNT = count()
# 日志路径
LOG_DIR = Path('log')
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ======================================
# TODO: 数据准备，脚本将取df_input，可运行`data/prepare_date.py`生成
df_input = pl.read_parquet('data/data.parquet')
# 从脚本获取数据
df_output: pl.DataFrame = pl.DataFrame()

IC = {}
IR = {}

# 添加下期收益率标签
tool = ExprTool(date='date', asset='asset')
# ======================================

pset = gp.PrimitiveSetTyped("MAIN", [], np.ndarray)
pset = add_constants(pset)
pset = add_operators(pset)
pset = add_factors(pset)

# 多目标优化、单目标优化
creator.create("FitnessMulti", base.Fitness, weights=(1.0,))
creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMulti)

toolbox = base.Toolbox()
toolbox.register("expr", gp.genHalfAndHalf, pset=pset, min_=2, max_=5)
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
# toolbox.register("compile", gp.compile, pset=pset)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("mate", gp.cxOnePoint)
toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)
toolbox.decorate("mate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))
toolbox.decorate("mutate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))


def rank_ic(a, b):
    """计算RankIC"""
    return pl.corr(pl.col(a), pl.col(b), method='spearman', ddof=0, propagate_nans=False)


def calc_ic_ir(df: pl.DataFrame, factors, label):
    """计算IC和IR"""
    df = df.group_by(by=['date'], maintain_order=False).agg(
        [rank_ic(x, label) for x in factors]
    )
    # polars升级后，需要先drop_nans
    NUM_DROP = cs.numeric().fill_nan(None).drop_nulls()
    ic = df.select(NUM_DROP.mean())
    ir = df.select(NUM_DROP.mean() / NUM_DROP.std(ddof=0))
    # print(ic)
    # print(ic)

    # 居然有部分算出来是None, fill_null虽然只有一行，但对几百列太慢，所以放在之后处理
    # ic = ic.fill_null(float('nan'))
    # ir = ir.fill_null(float('nan'))

    ic = ic.to_dicts()[0]
    ir = ir.to_dicts()[0]

    return ic, ir


def evaluate_expr(individual, points):
    """评估函数，需要返回元组。

    !!! 元组中不能使用nan，否则名人堂中排序错误，也不建议使用inf和-inf，因为统计时会警告
    """
    ind, col = individual
    if col not in df_output.columns:
        # 没有此表达式，表示之前表达式不合法，所以不参与计算
        return float('-999'),  # float('-999'),

    # IC内部的值可能是None或nan，所以都要处理, 这里全转nan
    ic = IC.get(col, None) or float('nan')
    ir = IR.get(col, None) or float('nan')

    # IC绝对值越大越好。使用==判断是否nan
    ic = abs(ic) if ic == ic else float('-999')
    ir = ir if ir == ir else float('-999')

    return ic,  # ir,


def map_exprs(evaluate, invalid_ind):
    """原本是一个普通的map或多进程map，个体都是独立计算

    但这里考虑到表达式很相似，可以重复利用公共子表达式，所以决定种群一起进行计算，最后由其它地方取结果评估即可
    """
    g = next(GEN_COUNT)
    # 保存原始表达式，方便复现
    with open(LOG_DIR / f'deap_exprs_{g:04d}.pkl', 'wb') as f:
        pickle.dump(invalid_ind, f)

    logger.info("表达式转码...")
    # DEAP表达式转sympy表达式
    expr_dict = {f'GP_{i:04d}': stringify_for_sympy(expr) for i, expr in enumerate(invalid_ind)}
    expr_dict = {k: safe_eval(v, globals()) for k, v in expr_dict.items()}

    # 通过字典特性删除重复表达式
    expr_dict = {v: k for k, v in expr_dict.items()}
    expr_dict = {v: k for k, v in expr_dict.items()}

    # 清理非法表达式
    expr_dict = {k: v for k, v in expr_dict.items() if not is_invalid(v, pset)}
    # 清理无意义表达式
    expr_dict = {k: v for k, v in expr_dict.items() if not is_meaningless(v)}

    # 表达式转脚本
    codes, G = tool.all(expr_dict, style='polars', template_file='template.py.j2', replace=False, regroup=False, format=False)

    # 保存生成的代码
    with open(LOG_DIR / f'codes_{g:04d}.py', 'w', encoding='utf-8') as f:
        f.write(codes)

    # 使用两下划线，减少与生成代码间冲突可能性
    _cnt_ = len(expr_dict)
    logger.info(f"代码执行。共 {_cnt_} 条")

    _tic_ = time.time()

    # TODO 只处理了两个变量，如果你要设置更多，请与 `template.py.j2` 一同修改
    # 传globals()会导致sympy同名变量被修改，在第二代时再执行会报错，所以改成只转部分变量
    global df_output
    _globals = {'df_input': df_input, 'df_output': df_output}
    exec(codes, _globals)
    df_output = _globals['df_output']

    elapsed_time = time.time() - _tic_

    logger.info(f"执行完成。共用时 {elapsed_time:.3f} 秒，平均 {elapsed_time / _cnt_:.3f} 秒/条")

    global IC
    global IR
    # TODO: 计算ic, ir，需指定对应的标签字段
    IC, IR = calc_ic_ir(df_output, expr_dict.keys(), 'LABEL_OO_1')

    # 封装，加传数据存储的字段名
    invalid_ind2 = [(expr, f'GP_{i:04d}') for i, expr in enumerate(invalid_ind)]
    # 调用评估函数
    return map(evaluate, invalid_ind2)


toolbox.register("evaluate", evaluate_expr, points=[x / 10. for x in range(-10, 10)])
toolbox.register('map', map_exprs)


def main():
    # TODO: 伪随机种子，同种子可复现
    random.seed(9527)

    # TODO: 初始种群大小
    pop = toolbox.population(n=100)
    # TODO: 名人堂，表示最终选优多少个体
    hof = tools.HallOfFame(50)

    stats_fit = tools.Statistics(lambda ind: ind.fitness.values)
    stats_size = tools.Statistics(len)
    mstats = tools.MultiStatistics(fitness=stats_fit, size=stats_size)
    # 名人堂中不能出现nan, 无法比较排序
    mstats.register("avg", np.mean)
    mstats.register("std", np.std)
    mstats.register("min", np.min)
    mstats.register("max", np.max)

    pop, log = gp.harm(pop, toolbox,
                       # 交叉率、变异率，代数
                       cxpb=0.5, mutpb=0.1, ngen=2,
                       # 名人堂参数
                       alpha=0.05, beta=10, gamma=0.25, rho=0.9,
                       stats=mstats, halloffame=hof, verbose=True)
    # print log
    return pop, log, hof


if __name__ == "__main__":
    pop, log, hof = main()

    # 保存名人堂
    with open(LOG_DIR / f'hall_of_fame.pkl', 'wb') as f:
        pickle.dump(hof, f)

    print('=' * 60)
    for i, h in enumerate(hof):
        print(i, h.fitness, h)
