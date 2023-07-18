# !!! 以下代码在VSCode或Notebook中执行更好，能显示LATEX表达式和画表达式树状图
# %%
import os

os.chdir(os.path.dirname(__file__))
print(os.getcwd())

import sys

sys.path.append('..')
# %%
import operator
import pathlib
import pickle

from deap import base, creator, gp, tools

from expr_codegen.expr import safe_eval, is_meaningless
from expr_codegen.latex.printer import display_latex
from expr_codegen.tool import ExprTool
from examples.sympy_define import *

from gp.custom import add_constants, add_operators, add_factors
from gp.helper import stringify_for_sympy, is_invalid

_ = Eq

# %%
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
# %%

LOG_DIR = pathlib.Path('log')
with open(LOG_DIR / f'hall_of_fame.pkl', 'rb') as f:
    invalid_ind = pickle.load(f)

for i, ind in enumerate(invalid_ind):
    print(i, ind.fitness, ind)

# %%
expr_dict = {f'GP_{i:04d}': stringify_for_sympy(expr) for i, expr in enumerate(invalid_ind)}
expr_dict = {k: safe_eval(v, globals()) for k, v in expr_dict.items()}

# 通过字典特性删除重复表达式
expr_dict = {v: k for k, v in expr_dict.items()}
expr_dict = {v: k for k, v in expr_dict.items()}

# 清理非法表达式
expr_dict = {k: v for k, v in expr_dict.items() if not is_invalid(v, pset)}
# 清理无意义表达式
expr_dict = {k: v for k, v in expr_dict.items() if not is_meaningless(v)}

for i, (k, v) in enumerate(expr_dict.items()):
    print(i, k, v)
# %%
expr = expr_dict['GP_0007']
expr = ((OPEN / CLOSE) - 1) ** (-1 / 2)

# 这部分Latex代码放在VSCode中显示更直观
display_latex(expr)
# %%
# 生成代码和有向无环图
tool = ExprTool(date='date', asset='asset')
# 表达式转脚本
codes, G = tool.all(expr_dict, style='polars', template_file='template.py.j2', fast=True)
# %%
from expr_codegen.model import draw_expr_tree

# 画某树
draw_expr_tree(G, 'GP_0007')

# %%
# 打印代码
print(codes)
# %%
