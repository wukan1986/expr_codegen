"""
1. 准备数据
    date,asset,features,..., returns,...,labels

features建议提前做好预处理。因为在GP中计算效率低下，特别是行业中性化等操作强烈建议在提前做。因为
1. `ts_`。按5000次股票，要计算5000次
2. `cs_`。按1年250天算，要计算250次
3. `gp_`计算次数是`cs_`计算的n倍。按30个行业，1年250天，要计算30*250=7500次

ROCP=ts_return，不移动位置，用来做特征。前移shift(-x)就只能做标签了

returns是shift前移的简单收益率，用于事后求分组收益
1. 对数收益率方便进行时序上的累加
2. 简单收益率方便横截面上进行等权
log_return = ln(1+simple_return)

labels是因变量
1. 可能等于returns
2. 可能是超额收益率
3. 可能是0/1等分类标签

"""
import os
import sys
from pathlib import Path

# 修改当前目录到上层目录，方便跨不同IDE中使用
pwd = str(Path(__file__).parents[1])
print('pwd:', pwd)
os.chdir(pwd)
sys.path.append(pwd)
# ===============
import operator
import pickle
import time
from datetime import datetime
from itertools import count
from typing import Sequence, Dict

import polars as pl
import polars.selectors as cs
from deap import base, creator
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
FITNESS_WEIGHTS = (1.0, 1.0)

# TODO y表示类别标签、因变量、输出变量，需要与数据文件字段对应
LABEL_y = 'RETURN_OO_1'

# TODO: 数据准备，脚本将取df_input，可运行`data/prepare_date.py`生成
df_input = pl.read_parquet('data/data.parquet')
df_train = df_input.filter(pl.col('date') < datetime(2021, 1, 1))
df_vaild = df_input.filter(pl.col('date') >= datetime(2021, 1, 1))
del df_input  # 释放内存
# ======================================
# 日志路径
LOG_DIR = Path('log')
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ======================================
def fitness_individual(a: str, b: str) -> pl.Expr:
    """个体fitness函数"""
    # 这使用的是rank_ic
    return pl.corr(a, b, method='spearman', ddof=0, propagate_nans=False)


def fitness_population(df: pl.DataFrame, columns: Sequence[str], label: str):
    """种群fitness函数"""
    if df is None:
        return {}, {}

    df = df.group_by(by=['date']).agg(
        [fitness_individual(X, label) for X in columns]
    )

    _expr = cs.numeric().fill_nan(None).drop_nulls()
    ic = df.select(_expr.mean())
    ir = df.select(_expr.mean() / _expr.std(ddof=0))

    # 无效值用的None
    ic = ic.to_dicts()[0]
    ir = ir.to_dicts()[0]
    return ic, ir


def get_fitness(name: str, kv: Dict[str, float]) -> float:
    return kv.get(name, False) or float('nan')


def map_exprs(evaluate, invalid_ind, gen, label, input_train=None, input_vaild=None):
    """原本是一个普通的map或多进程map，个体都是独立计算
    但这里考虑到表达式很相似，可以重复利用公共子表达式，
    所以决定种群一起进行计算，返回结果评估即可
    """
    g = next(gen)
    # 保存原始表达式，立即保存是防止崩溃后丢失信息, 注意：这里没有存fitness
    with open(LOG_DIR / f'exprs_{g:04d}.pkl', 'wb') as f:
        pickle.dump(invalid_ind, f)

    logger.info("表达式转码...")
    # DEAP表达式转sympy表达式。约定以GP_开头，表示遗传编程
    expr_dict = {f'GP_{i:04d}': stringify_for_sympy(expr) for i, expr in enumerate(invalid_ind)}
    expr_keys = list(expr_dict.keys())
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
                        replace=False, regroup=True, format=True,
                        date='date', asset='asset')

    # 备份生成的代码
    path = LOG_DIR / f'codes_{g:04d}.py'
    import_path = f'log.codes_{g:04d}'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(codes)

    cnt = len(expr_dict)
    logger.info("代码执行。共 {} 条 表达式", cnt)
    tic = time.perf_counter()

    # exec和import都可以，import好处是内部代码可调试
    _lib = __import__(import_path, fromlist=['*'])

    # 因子计算
    output_train = None if input_train is None else _lib.main(input_train)
    output_vaild = None if input_vaild is None else _lib.main(input_vaild)

    elapsed_time = time.perf_counter() - tic
    logger.info("因子计算完成。共用时 {:.3f} 秒，平均 {:.3f} 秒/条，或 {:.3f} 条/秒", elapsed_time, elapsed_time / cnt, cnt / elapsed_time)

    # 计算种群适应度
    ic_train, ir_train = fitness_population(output_train, list(expr_dict.keys()), label=label)
    ic_vaild, ir_vaild = fitness_population(output_vaild, list(expr_dict.keys()), label=label)
    logger.info("适应度计算完成")

    # 取评估函数值，多目标。
    results1 = [(
        abs(get_fitness(key, ic_train)),
        abs(get_fitness(key, ic_vaild),  # 这只是为了同时显示样本外值
            )) for key in expr_keys]

    # TODO 样本内外过滤条件
    results2 = []
    for s0, s1 in results1:
        if s0 == s0:  # 非空
            if s0 > 0.001:  # 样本内打分要大
                if s0 * 0.8 < s1:  # 样本外打分大于样本内打分的80%
                    results2.append((s0, s1))
                    continue
        results2.append((np.nan, np.nan))

    return results2


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
toolbox.register("evaluate", print)  # 不单独做评估了，在map中一并做了
toolbox.register('map', map_exprs, gen=count(), label=LABEL_y, input_train=df_train, input_vaild=df_vaild)


def main():
    # TODO: 伪随机种子，同种子可复现
    random.seed(9527)

    # TODO: 初始种群大小
    pop = toolbox.population(n=100)
    # TODO: 名人堂，表示最终选优多少个体
    hof = tools.HallOfFame(50)

    # 只统计一个指标更清晰
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    # 打补丁后，名人堂可以用nan了
    stats.register("avg", np.nanmean, axis=0)
    stats.register("std", np.nanstd, axis=0)
    stats.register("min", np.nanmin, axis=0)
    stats.register("max", np.nanmax, axis=0)

    # 使用修改版的eaMuPlusLambda
    population, logbook = eaMuPlusLambda(pop, toolbox,
                                         # 选多少个做为下一代，每次生成多少新个体
                                         mu=150, lambda_=100,
                                         # 交叉率、变异率，代数
                                         cxpb=0.5, mutpb=0.1, ngen=2,
                                         # 名人堂参数
                                         # alpha=0.05, beta=10, gamma=0.25, rho=0.9,
                                         stats=stats, halloffame=hof, verbose=True,
                                         # 早停
                                         early_stopping_rounds=2)

    return population, logbook, hof


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
    print('另行执行`tensorboard --logdir=runs`，然后在浏览器中访问`http://localhost:6006/`，可跟踪运行情况')
    population, logbook, hof = main()

    # 保存名人堂
    with open(LOG_DIR / f'hall_of_fame.pkl', 'wb') as f:
        pickle.dump(hof, f)

    print('=' * 60)
    print(logbook)

    print('=' * 60)
    print_population(hof)
