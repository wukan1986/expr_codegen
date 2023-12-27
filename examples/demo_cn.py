import sys
from pathlib import Path

# 修改当前目录到上层目录，方便跨不同IDE中使用
pwd = str(Path(__file__).parents[1])
# os.chdir(pwd)
sys.path.append(pwd)

from examples.sympy_define import *
# codegen工具类
from expr_codegen.tool import ExprTool

# TODO: 因子。请根据需要补充
sw_l1, = symbols('sw_l1, ', cls=Symbol)

# TODO: 分组算子。需要提前按时间、行业分组。必需以`gp_`开头
gp_rank, = symbols('gp_rank, ', cls=Function)

# TODO: 中间变量必需定义成符号才能递归调用
expr_7, = symbols('expr_7, ', cls=Symbol)

# TODO: 等待简化的表达式。多个表达式一起能简化最终表达式
exprs_src = {
    "expr_1": -ts_corr(cs_rank(ts_mean(OPEN, 10)), cs_rank(ts_mean(CLOSE, 10)), 10),
    "expr_2": cs_rank(ts_mean(OPEN, 10)) - Abs(log(ts_mean(CLOSE, 10))),  # + gp_rank(sw_l1, CLOSE),  # + gp_rank(OPEN, CLOSE),
    "expr_3": ts_mean(cs_rank(ts_mean(OPEN, 10)), 10),
    "expr_4": cs_rank(ts_mean(cs_rank(OPEN), 10)),
    "expr_5": -ts_corr(OPEN, CLOSE, 10),
    "expr_6": ts_delta(OPEN, 10),

    # expr_7 为某步的中间变量
    "expr_8": ts_rank(expr_7 + 1, 10),
    "expr_7": ts_rank(OPEN + 1, 10),
}

# TODO: 一定要正确设定时间列名和资产列名
tool = ExprTool(date='date', asset='asset')
# 生成代码
codes, G = tool.all(exprs_src, style='polars', template_file='template.py.j2', regroup=False)

output_file = 'output_polars.py'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(codes)
