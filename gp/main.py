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
from typing import Dict, Sequence

import numpy as np
import polars as pl
import polars.selectors as cs
from deap import base, creator, gp, tools
from loguru import logger

from examples.sympy_define import *  # noqa
from expr_codegen.expr import safe_eval, is_meaningless
from expr_codegen.tool import ExprTool
from gp.custom import add_constants, add_operators, add_factors
from gp.helper import stringify_for_sympy, is_invalid

# ======================================
# TODO 必须元组，1表示找最大值,-1表示找最小值
# FITNESS_WEIGHTS = (1.0, 1.0)
FITNESS_WEIGHTS = (1.0,)
# TODO 排序和统计时nan和inf都会导致结果异常，所以选一个**反向**的**离群值**当成无效值
# 前面FITNESS_WEIGHTS要找最大值，所以这里要用非常小的值，fitness函数计算IC，值在-1到1之前
FITNESS_NAN = -99.0

# TODO y表示类别标签、因变量、输出变量，需要与数据文件字段对应
LABEL_y = 'LABEL_OO_1'

# TODO: 数据准备，脚本将取df_input，可运行`data/prepare_date.py`生成
df_input = pl.read_parquet('data/data.parquet')

# 从脚本获取数据。注意，要与`template.py.j2`文件相对应
df_output: pl.DataFrame = pl.DataFrame()

# ======================================
# 当前种群的fitness目标，可添加多个目标
IC: Dict[str, float] = {}
IR: Dict[str, float] = {}

# 每代计数
GEN_COUNT = count()
# 日志路径
LOG_DIR = Path('log')
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ======================================
def fitness_individual(a: str, b: str) -> pl.Expr:
    """个体fitness函数"""
    # 这使用的是rank_ic
    return pl.corr(a, b, method='spearman', ddof=0, propagate_nans=False)


def fitness_population(df: pl.DataFrame, columns: Sequence[str]) -> None:
    """种群fitness函数"""
    df = df.group_by(by=['date']).agg(
        [fitness_individual(X, LABEL_y) for X in columns]
    )

    _expr = cs.numeric().fill_nan(None).drop_nulls()
    ic = df.select(_expr.mean())
    ir = df.select(_expr.mean() / _expr.std(ddof=0))

    # TODO 可添加多套适应度函数
    global IC
    global IR

    IC = ic.to_dicts()[0]
    IR = ir.to_dicts()[0]


def evaluate_expr(individual, points=None):
    """评估函数。需要返回元组"""
    ind, col = individual
    #  元组中不能使用nan，否则名人堂中排序错误，也不建议使用inf和-inf，因为统计时会警告
    ic, ir = FITNESS_NAN, FITNESS_NAN

    if col not in df_output.columns:
        # 如果没有此表达式，表示之前表达式 不合法或重复 没有参与计算
        pass
    else:
        # !!! IC内部的值可能是None或nan，都要处理, 全转nan
        ic = IC.get(col, None) or float('nan')
        ir = IR.get(col, None) or float('nan')

        # IC绝对值越大越好。使用==判断是否nan
        ic = abs(ic) if ic == ic else FITNESS_NAN
        ir = ir if ir == ir else FITNESS_NAN

    # TODO 需返回元组，数量必须与weights对应
    return ic,  # ir,


def map_exprs(evaluate, invalid_ind):
    """原本是一个普通的map或多进程map，个体都是独立计算
    但这里考虑到表达式很相似，可以重复利用公共子表达式，
    所以决定种群一起进行计算，将结果保存，最后其它地方取结果评估即可
    """
    g = next(GEN_COUNT)
    # 保存原始表达式，立即保存是防止崩溃后丢失信息, 注意：这里没有存fitness
    with open(LOG_DIR / f'exprs_{g:04d}.pkl', 'wb') as f:
        pickle.dump(invalid_ind, f)

    logger.info("表达式转码...")
    # DEAP表达式转sympy表达式。约定以GP_开头，表示遗传编程
    expr_dict = {f'GP_{i:04d}': stringify_for_sympy(expr) for i, expr in enumerate(invalid_ind)}
    expr_dict = {k: safe_eval(v, globals()) for k, v in expr_dict.items()}

    # 清理重复表达式，通过字典特性删除
    expr_dict = {v: k for k, v in expr_dict.items()}
    expr_dict = {v: k for k, v in expr_dict.items()}
    # 清理非法表达式
    expr_dict = {k: v for k, v in expr_dict.items() if not is_invalid(v, pset)}
    # 清理无意义表达式
    expr_dict = {k: v for k, v in expr_dict.items() if not is_meaningless(v)}

    # 注意：以上的简化操作并没有修改种群，只是是在计算前做了预处理。所以还是会出现不同代重复计算

    tool = ExprTool()
    # 表达式转脚本
    codes, G = tool.all(expr_dict, style='polars', template_file='template.py.j2',
                        replace=False, regroup=False, format=False,
                        date='date', asset='asset')

    # 备份生成的代码
    with open(LOG_DIR / f'codes_{g:04d}.py', 'w', encoding='utf-8') as f:
        f.write(codes)

    cnt = len(expr_dict)
    logger.info("代码执行。共 {} 条 表达式", cnt)
    tic = time.perf_counter()

    # 传globals()会导致sympy同名变量被修改，在第二代时再执行会报错，所以改成只转部分变量
    global df_output
    # TODO 只处理了两个变量，如果你要设置更多变量，请与 `template.py.j2` 一同修改
    _globals = {'df_input': df_input, 'df_output': df_output}
    exec(codes, _globals)
    df_output = _globals['df_output']

    elapsed_time = time.perf_counter() - tic
    logger.info("执行完成。共用时 {:.3f} 秒，平均 {:.3f} 秒/条，或 {:.3f} 条/秒", elapsed_time, elapsed_time / cnt, cnt / elapsed_time)

    # 计算种群适应度
    fitness_population(df_output, list(expr_dict.keys()))

    # 封装，加传数据存储的字段名
    invalid_ind2 = [(expr, f'GP_{i:04d}') for i, expr in enumerate(invalid_ind)]
    # 调用评估函数
    return map(evaluate, invalid_ind2)


# ======================================
from gp.deap_patch import generate

# 给deap打补针，解决pass_int层数过多问题
gp.generate = generate
# ======================================

pset = gp.PrimitiveSetTyped("MAIN", [], np.ndarray)
pset = add_constants(pset)
pset = add_operators(pset)
pset = add_factors(pset)

# 多目标优化
creator.create("FitnessMulti", base.Fitness, weights=FITNESS_WEIGHTS)
creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMulti)

toolbox = base.Toolbox()
toolbox.register("expr", gp.genHalfAndHalf, pset=pset, min_=2, max_=5)
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("select", tools.selTournament, tournsize=3)  # 目标优化
# toolbox.register("select", tools.selNSGA2)  # 多目标优化
toolbox.register("mate", gp.cxOnePoint)
toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)
toolbox.decorate("mate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))
toolbox.decorate("mutate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))
toolbox.register("evaluate", evaluate_expr, points=None)
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

    pop, _log = gp.harm(pop, toolbox,
                        # 交叉率、变异率，代数
                        cxpb=0.5, mutpb=0.1, ngen=2,
                        # 名人堂参数
                        alpha=0.05, beta=10, gamma=0.25, rho=0.9,
                        stats=mstats, halloffame=hof, verbose=True)

    return pop, _log, hof


if __name__ == "__main__":
    pop, _log, hof = main()

    # 保存名人堂
    with open(LOG_DIR / f'hall_of_fame.pkl', 'wb') as f:
        pickle.dump(hof, f)

    print('=' * 60)
    for i, e in enumerate(hof):
        # 小心globals()中的log等变量与内部函数冲突
        print(f'{i:03d}', '\t', e.fitness, '\t', e, end='\t<--->\t')
        # 分两行，冲突时可以知道是哪出错
        print(safe_eval(stringify_for_sympy(e), globals()))
