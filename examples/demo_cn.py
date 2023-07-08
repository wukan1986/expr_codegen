from examples.sympy_define import *
# codegen工具类
from expr_codegen.tool import ExprTool

# TODO: 因子。请根据需要补充
sw_l1, = symbols('sw_l1, ', cls=Symbol)

# TODO: 分组算子。需要提前按时间、行业分组。必需以`gp_`开头
gp_rank, = symbols('gp_rank, ', cls=Function)

# TODO: 等待简化的表达式。多个表达式一起能简化最终表达式
exprs_src = {
    "expr_1": -ts_corr(cs_rank(ts_mean(OPEN, 10)), cs_rank(ts_mean(CLOSE, 10)), 10),
    "expr_2": cs_rank(ts_mean(OPEN, 10)) - abs(log(ts_mean(CLOSE, 10))) + gp_rank(sw_l1, CLOSE),  # + gp_rank(OPEN, CLOSE),
    "expr_3": ts_mean(cs_rank(ts_mean(OPEN, 10)), 10),
    "expr_4": cs_rank(ts_mean(cs_rank(OPEN), 10)),
    "expr_5": -ts_corr(OPEN, CLOSE, 10),
    "expr_6": ts_delta(OPEN, 10),
    "expr_7": ts_delta(OPEN + 1, 10),
}

# TODO: 一定要正确设定时间列名和资产列名，以及表达式识别类
tool = ExprTool(date='date', asset='asset')
# 生成代码
tool = ExprTool(date='date', asset='asset')
codes = tool.all(exprs_src, style='polars', template_file='template.py.j2', fast=False)

output_file = 'output_polars.py'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(codes)
