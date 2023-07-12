import operator
import pathlib
import pickle

from deap import base, creator, gp, tools

from examples.sympy_define import *
from expr_codegen.expr import safe_eval, meaningless__ts_xxx_1, meaningless__xx_xx
from expr_codegen.tool import ExprTool
from gp.custom import add_constants, add_operators, add_factors
from gp.helper import stringify_for_sympy, invalid_atom_infinite, invalid_number_type

_ = Eq, Add, Mul, Pow
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
# ======================================

LOG_DIR = pathlib.Path('log')
with open(LOG_DIR / f'deap_exprs_0004.pkl', 'rb') as f:
    invalid_ind = pickle.load(f)

for i, ind in enumerate(invalid_ind):
    print(i, ind)

# ======================================
expr_dict = {f'GP_{i:04d}': stringify_for_sympy(expr) for i, expr in enumerate(invalid_ind)}
expr_dict = {k: safe_eval(v, globals()) for k, v in expr_dict.items()}

# TODO: test
expr_dict = {'test': cs_scale(log(ts_rank(CLOSE, 20))) + sign(3*min(OPEN, HIGH*OPEN))}

# 通过字典特性删除重复表达式
expr_dict = {v: k for k, v in expr_dict.items()}
expr_dict = {v: k for k, v in expr_dict.items()}

# 清理非法表达式
expr_dict = {k: v for k, v in expr_dict.items() if not (invalid_atom_infinite(v) or invalid_number_type(v, pset))}
# 清理无意义表达式
expr_dict = {k: v for k, v in expr_dict.items() if not (meaningless__ts_xxx_1(v) or meaningless__xx_xx(v))}

tool = ExprTool(date='date', asset='asset')
# 表达式转脚本
codes = tool.all(expr_dict, style='polars', template_file='template_gp.py.j2', fast=True)
print(codes)
