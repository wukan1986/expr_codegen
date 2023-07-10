import operator
import pathlib
import pickle
import random
from itertools import count

import numpy as np
import polars as pl
from deap import base, creator, gp, tools
from loguru import logger

from examples.sympy_define import *
from expr_codegen.expr import safe_eval, meaningless__ts_xxx_1, meaningless__xx_xx
from expr_codegen.tool import ExprTool
from gp.custom import add_constants, add_operators, add_factors
from gp.helper import stringify_for_sympy, invalid_atom_infinite, invalid_number_type

_ = Eq, Add, Mul, Pow
# ======================================
GEN_COUNT = count()
LOG_DIR = pathlib.Path('log')
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ======================================
# 数据准备

# 向脚本输入数据
df_input = pl.read_parquet('data.parquet')
# 从脚本获取数据
df_output: pl.DataFrame = None
# 添加下期收益率标签
tool = ExprTool(date='date', asset='asset')
# ======================================

pset = gp.PrimitiveSetTyped("MAIN", [], float)
pset = add_constants(pset)
pset = add_operators(pset)
pset = add_factors(pset)

creator.create("FitnessMulti", base.Fitness, weights=(1,))
creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMulti)

toolbox = base.Toolbox()
toolbox.register("expr", gp.genHalfAndHalf, pset=pset, min_=1, max_=2)
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
# toolbox.register("compile", gp.compile, pset=pset)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("mate", gp.cxOnePoint)
toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)
toolbox.decorate("mate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))
toolbox.decorate("mutate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))


def evaluate_expr(individual, points):
    """评估函数"""
    ind, col = individual
    if col not in df_output.columns:
        # 没有此表达式，表示之前表达式不合法，所以不参与计算
        return float('nan'),

    # 其实也可以将评估函数写在模板中，这里只取结果即可
    return random.random(),


def map_exprs(evaluate, invalid_ind):
    """原本是一个普通的map或多进程map，个体都是独立计算

    但这里考虑到表达式很相似，可以重复利用公共子表达式，所以决定种群一起进行计算，最后由其它地方取结果评估即可
    """
    g = next(GEN_COUNT)
    # 保存原始，方便复现
    with open(LOG_DIR / f'deap_exprs_{g:04d}.pkl', 'wb') as f:
        pickle.dump(invalid_ind, f)

    logger.info("表达式转码...")
    # DEAP表达式转sympy表达式
    expr_dict = {f'GP_{i}': stringify_for_sympy(expr) for i, expr in enumerate(invalid_ind)}
    expr_dict = {k: safe_eval(v, globals()) for k, v in expr_dict.items()}

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

    # 评估
    # df_output.groupby(by='date').apply(lambda x: x)

    # 封装，加传数据存储的字段名
    invalid_ind2 = [(expr, f'GP_{i}') for i, expr in enumerate(invalid_ind)]
    # 调用评估函数
    return map(evaluate, invalid_ind2)


toolbox.register("evaluate", evaluate_expr, points=[x / 10. for x in range(-10, 10)])
toolbox.register('map', map_exprs)


def main():
    # 伪随机种子，同种子可复现
    random.seed(318)

    pop = toolbox.population(n=50)
    hof = tools.HallOfFame(10)

    stats_fit = tools.Statistics(lambda ind: ind.fitness.values)
    stats_size = tools.Statistics(len)
    mstats = tools.MultiStatistics(fitness=stats_fit, size=stats_size)
    mstats.register("avg", np.nanmean)
    mstats.register("std", np.nanstd)
    mstats.register("min", np.nanmin)
    mstats.register("max", np.nanmax)

    pop, log = gp.harm(pop, toolbox, 0.5, 0.1, 40, alpha=0.05, beta=10, gamma=0.25, rho=0.9, stats=mstats,
                       halloffame=hof, verbose=True)
    # print log
    return pop, log, hof


if __name__ == "__main__":
    main()
