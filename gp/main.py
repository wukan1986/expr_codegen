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
import time
from datetime import datetime
from itertools import count
from typing import Dict, Sequence

import polars as pl
import polars.selectors as cs
from deap import base, creator, tools
from loguru import logger

from expr_codegen.expr import safe_eval, is_meaningless, dict_to_exprs, function_to_Function
from expr_codegen.tool import ExprTool
from gp.custom import add_constants, add_operators, add_factors, RET_TYPE
from gp.helper import stringify_for_sympy, is_invalid
# !!! 非常重要。给deap打补丁
from gp.deap_patch import *  # noqa

# ======================================

# 引入OPEN等
from examples.sympy_define import *  # noqa

# ======================================
# TODO 必须元组，1表示找最大值,-1表示找最小值
FITNESS_WEIGHTS = (1.0,)

# TODO y表示类别标签、因变量、输出变量，需要与数据文件字段对应
LABEL_y = 'LABEL_OO_1'

# TODO: 数据准备，脚本将取df_input，可运行`data/prepare_date.py`生成
df_input = pl.read_parquet('data/data.parquet')
# TODO 样本内数据
df_input = df_input.filter(pl.col('date') < datetime(2021, 1, 1))
# ======================================
# 当前种群的fitness目标，可添加多个目标
IC: Dict[str, float] = {}
IR: Dict[str, float] = {}

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
    """评估函数。需要返回元组

    !!! 已经通过对deap打补丁的方式支持了nan
    """
    ind, col = individual

    # !!! IC内部的值可能是None或nan，都要处理, 全转nan
    ic = IC.get(col, False) or float('nan')
    ir = IR.get(col, False) or float('nan')

    # TODO 需返回元组，数量必须与weights对应
    return ic,  # ir


def map_exprs(evaluate, invalid_ind, gen, date_input):
    """原本是一个普通的map或多进程map，个体都是独立计算
    但这里考虑到表达式很相似，可以重复利用公共子表达式，
    所以决定种群一起进行计算，将结果保存，最后其它地方取结果评估即可
    """
    g = next(gen)
    # 保存原始表达式，立即保存是防止崩溃后丢失信息, 注意：这里没有存fitness
    with open(LOG_DIR / f'exprs_{g:04d}.pkl', 'wb') as f:
        pickle.dump(invalid_ind, f)

    logger.info("表达式转码...")
    # DEAP表达式转sympy表达式。约定以GP_开头，表示遗传编程
    expr_dict = {f'GP_{i:04d}': stringify_for_sympy(expr) for i, expr in enumerate(invalid_ind)}
    expr_dict = dict_to_exprs(expr_dict, globals().copy())

    # 清理重复表达式，通过字典特性删除
    expr_dict = {v: k for k, v in expr_dict.items()}
    expr_dict = {v: k for k, v in expr_dict.items()}
    # 清理非法表达式
    expr_dict = {k: v for k, v in expr_dict.items() if not is_invalid(v, pset, RET_TYPE)}
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
    # TODO 只处理了两个变量，如果你要设置更多变量，请与 `template.py.j2` 一同修改
    _globals = {'df_input': date_input}
    exec(codes, _globals)  # 这里调用时脚本__name__为"builtins"
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
# 这里的ret_type只要与addPrimitive对应即可
pset = gp.PrimitiveSetTyped("MAIN", [], RET_TYPE)
pset = add_constants(pset)
pset = add_operators(pset)
pset = add_factors(pset)

# 可支持多目标优化
creator.create("FitnessMulti", base.Fitness, weights=FITNESS_WEIGHTS)
creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMulti)

toolbox = base.Toolbox()
toolbox.register("expr", gp.genHalfAndHalf, pset=pset, min_=2, max_=5)
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("select", tools.selTournament, tournsize=3)  # 目标优化
# toolbox.register("select", tools.selNSGA2)  # 多目标优化 FITNESS_WEIGHTS = (1.0, 1.0)
toolbox.register("mate", gp.cxOnePoint)
toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)
toolbox.decorate("mate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))
toolbox.decorate("mutate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))
toolbox.register("evaluate", evaluate_expr, points=None)
toolbox.register('map', map_exprs, gen=count(), date_input=df_input)


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
    mstats.register("avg", np.nanmean)
    mstats.register("std", np.nanstd)
    mstats.register("min", np.nanmin)
    mstats.register("max", np.nanmax)

    pop, _log = gp.harm(pop, toolbox,
                        # 交叉率、变异率，代数
                        cxpb=0.5, mutpb=0.1, ngen=2,
                        # 名人堂参数
                        alpha=0.05, beta=10, gamma=0.25, rho=0.9,
                        stats=mstats, halloffame=hof, verbose=True)

    return pop, _log, hof


def print_population(pop):
    # !!!这句非常重要
    globals_ = globals().copy()
    globals_.update(function_to_Function(globals_))
    for i, e in enumerate(pop):
        # 小心globals()中的log等变量与内部函数冲突
        print(f'{i:03d}', '\t', e.fitness, '\t', e, '\t<--->\t', end='')
        # 分两行，冲突时可以知道是哪出错
        print(safe_eval(stringify_for_sympy(e), globals_))


if __name__ == "__main__":
    pop, _log, hof = main()

    # 保存名人堂
    with open(LOG_DIR / f'hall_of_fame.pkl', 'wb') as f:
        pickle.dump(hof, f)

    print('=' * 60)
    print_population(hof)
