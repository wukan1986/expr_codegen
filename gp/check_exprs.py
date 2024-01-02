# !!! 以下代码在VSCode或Notebook中执行更好，能显示LATEX表达式和画表达式树状图
# %%
import os
import sys
from pathlib import Path

# 修改当前目录到上层目录，方便跨不同IDE中使用
pwd = str(Path(__file__).parents[1])
os.chdir(pwd)
sys.path.append(pwd)
# ===============
# %%
# 从main中导入，可以大大减少代码
from main import *

with open(LOG_DIR / f'exprs_0000.pkl', 'rb') as f:
    population = pickle.load(f)

for i, h in enumerate(population):
    print(f'{i:03d}', '\t', h.fitness, '\t', h)

# %%
expr_dict = {f'GP_{i:04d}': stringify_for_sympy(expr) for i, expr in enumerate(population)}
expr_dict = {k: safe_eval(v, globals()) for k, v in expr_dict.items()}

for i, (k, v) in enumerate(expr_dict.items()):
    print(f'{i:03d}', k, v)
# %%
expr = expr_dict['GP_0007']
# expr = ((OPEN / CLOSE) - 1) ** (-1 / 2)

# 这部分Latex代码放在VSCode中显示更直观
from expr_codegen.latex.printer import display_latex

display_latex(expr)
# %%
# 生成代码和有向无环图
tool = ExprTool()
codes, G = tool.all(expr_dict, style='polars', template_file='template.py.j2',
                    replace=False, regroup=False, format=False,
                    date='date', asset='asset')
# %%
from expr_codegen.model import draw_expr_tree

# 画某树
draw_expr_tree(G, 'GP_0007')

# %%
# 打印代码
# print(codes)
# %%
