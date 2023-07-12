import operator
import pathlib
import pickle
import random
# abs在examples.sympy_define中已经被替换成了sympy的symbol，如果用后要用到正必需别名一下
from builtins import abs as _abs
from itertools import count

import numpy as np
import polars as pl
import polars.selectors as cs
from deap import base, creator, gp, tools
from loguru import logger

from examples.sympy_define import *
from expr_codegen.expr import safe_eval, meaningless__ts_xxx_1, meaningless__xx_xx
from expr_codegen.tool import ExprTool
from gp.custom import add_constants, add_operators, add_factors
from gp.helper import stringify_for_sympy, invalid_atom_infinite, invalid_number_type

_ = Eq, Add, Mul, Pow
# ======================================
# 每代计数
GEN_COUNT = count()
# 日志路径
LOG_DIR = pathlib.Path('log')
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ======================================
# 数据准备

# 向脚本输入数据
df_input = pl.read_parquet('data.parquet')
# 从脚本获取数据
df_output: pl.DataFrame = None

IC = None
IR = None

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
    df = df.groupby(by=['date'], maintain_order=False).agg(
        [rank_ic(x, label) for x in factors]
    )
    ic = df.select(cs.numeric().mean())
    ir = df.select(cs.numeric().mean() / cs.numeric().std(ddof=0))

    # 居然有部分算出来是None, fill_null虽然只有一行，但对几百列太慢，所以放在之后处理
    # ic = ic.fill_null(float('nan'))
    # ir = ir.fill_null(float('nan'))

    ic = ic.to_dicts()[0]
    ir = ir.to_dicts()[0]

    return ic, ir


def evaluate_expr(individual, points):
    """评估函数

    需要返回元组，
    """
    ind, col = individual
    if col not in df_output.columns:
        # 没有此表达式，表示之前表达式不合法，所以不参与计算
        return float('nan'),  # float('nan'),

    # print(col)
    # if col == 'GP_0022':
    #     test =1
    ic = IC.get(col, None)
    ir = IR.get(col, None)

    ic = float('nan') if ic is None else ic
    ir = float('nan') if ir is None else ir
    # IC绝对值越大越好
    return _abs(ic),  # ir,


def map_exprs(evaluate, invalid_ind):
    """原本是一个普通的map或多进程map，个体都是独立计算

    但这里考虑到表达式很相似，可以重复利用公共子表达式，所以决定种群一起进行计算，最后由其它地方取结果评估即可
    """
    g = next(GEN_COUNT)
    # 保存原始，方便复现
    with open(LOG_DIR / f'deap_exprs_{g:04d}.pkl', 'wb') as f:
        pickle.dump(invalid_ind, f)

    # TODO: test
    # with open(LOG_DIR / f'deap_exprs_0012_test.pkl', 'rb') as f:
    #     invalid_ind = pickle.load(f)

    logger.info("表达式转码...")
    # DEAP表达式转sympy表达式
    expr_dict = {f'GP_{i:04d}': stringify_for_sympy(expr) for i, expr in enumerate(invalid_ind)}
    expr_dict = {k: safe_eval(v, globals()) for k, v in expr_dict.items()}

    # 通过字典特性删除重复表达式
    expr_dict = {v: k for k, v in expr_dict.items()}
    expr_dict = {v: k for k, v in expr_dict.items()}

    # 清理非法表达式
    expr_dict = {k: v for k, v in expr_dict.items() if not (invalid_atom_infinite(v) or invalid_number_type(v, pset))}
    # 清理无意义表达式
    expr_dict = {k: v for k, v in expr_dict.items() if not (meaningless__ts_xxx_1(v) or meaningless__xx_xx(v))}

    # 表达式转脚本
    codes = tool.all(expr_dict, style='polars', template_file='template_gp.py.j2', fast=True)

    with open(LOG_DIR / f'codes_{g:04d}.py', 'w', encoding='utf-8') as f:
        f.write(codes)

    logger.info("代码执行...")
    # 执行，一定要带globals()
    exec(codes, globals())
    # print(df_input, '111')
    # print(df_output, '222')
    logger.info("执行完成")

    global IC
    global IR
    # 计算ic, ir，需指定对应的标签字段
    IC, IR = calc_ic_ir(df_output, expr_dict.keys(), 'LABEL_OO_1')

    # 封装，加传数据存储的字段名
    invalid_ind2 = [(expr, f'GP_{i:04d}') for i, expr in enumerate(invalid_ind)]
    # 调用评估函数
    return map(evaluate, invalid_ind2)


toolbox.register("evaluate", evaluate_expr, points=[x / 10. for x in range(-10, 10)])
toolbox.register('map', map_exprs)


def main():
    # 伪随机种子，同种子可复现
    random.seed(1015)

    pop = toolbox.population(n=300)
    hof = tools.HallOfFame(30)

    stats_fit = tools.Statistics(lambda ind: ind.fitness.values)
    stats_size = tools.Statistics(len)
    mstats = tools.MultiStatistics(fitness=stats_fit, size=stats_size)
    mstats.register("avg", np.nanmean)
    mstats.register("std", np.nanstd)
    mstats.register("min", np.nanmin)
    mstats.register("max", np.nanmax)

    pop, log = gp.harm(pop, toolbox,
                       cxpb=0.5, mutpb=0.1, ngen=50,
                       alpha=0.05, beta=10, gamma=0.25, rho=0.9,
                       stats=mstats, halloffame=hof, verbose=True)
    # print log
    return pop, log, hof


if __name__ == "__main__":
    pop, log, hof = main()
    print('=' * 60)
    for i, h in enumerate(hof):
        print(i, h)
