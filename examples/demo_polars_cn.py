import os

from sympy import symbols, Symbol, Function, numbered_symbols

from expr_codegen.polars.code import codegen
from expr_codegen.tool import ExprTool

# !!! 所有新补充的`Function`都需要在`printer.py`中添加对应的处理代码

# TODO: 因子。请根据需要补充
OPEN, HIGH, LOW, CLOSE, VOLUME, = symbols('OPEN, HIGH, LOW, CLOSE, VOLUME, ', cls=Symbol)
sw_l1, = symbols('sw_l1, ', cls=Symbol)

# TODO: 通用算子。时序、横截面和整体都能使用的算子。请根据需要补充
log, sign, abs, = symbols('log, sign, abs, ', cls=Function)

# TODO: 时序算子。需要提前按资产分组，组内按时间排序。请根据需要补充。必需以`ts_`开头
ts_delay, ts_delta, ts_mean, ts_corr, = symbols('ts_delay, ts_delta, ts_mean, ts_corr, ', cls=Function)

# TODO: 横截面算子。需要提前按时间分组。请根据需要补充。必需以`cs_`开头
cs_rank, = symbols('cs_rank, ', cls=Function)

# TODO: 分组算子。需要提前按时间、行业分组。必需以`gp_`开头
gp_rank, = symbols('gp_rank, ', cls=Function)

# TODO: 等待简化的表达式。多个表达式一起能简化最终表达式
exprs_src = {
    "expr_1": -ts_corr(cs_rank(ts_mean(OPEN, 10)), cs_rank(ts_mean(CLOSE, 10)), 10),
    "expr_2": cs_rank(ts_mean(OPEN, 10)) - abs(log(ts_mean(CLOSE, 10))),  # + gp_rank(sw_l1, CLOSE) + gp_rank(OPEN, CLOSE),
    "expr_3": ts_mean(cs_rank(ts_mean(OPEN, 10)), 10),
    "expr_4": cs_rank(ts_mean(cs_rank(OPEN), 10)),
    "expr_5": -ts_corr(OPEN, CLOSE, 10),
}

# 抽取时序与横截面子表达式
# TODO: 一定要正确设定时间列名和资产列名
tool = ExprTool(date='date', asset='asset')

# ############################

# 子表达式在前，原表式在最后
exprs_dst = tool.merge(**exprs_src)

# 提取公共表达式
exprs_ldl = tool.cse(exprs_dst, symbols_repl=numbered_symbols('x_'), symbols_redu=exprs_src.keys())

# 生成代码
codes = codegen(exprs_ldl, exprs_src)

# 保存
with open('output.py', 'w') as f:
    f.write(codes)

# reformat
os.system('python -m black -l 240 output.py')
