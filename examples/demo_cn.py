import os

from sympy import symbols, Symbol, Function, numbered_symbols

from sympy_polars.tool import ExprTool

# !!! 所有新补充的`Function`都需要在`printer.py`中添加对应的处理代码

# TODO: 因子。请根据需要补充
OPEN, HIGH, LOW, CLOSE, VOLUME, = symbols('OPEN, HIGH, LOW, CLOSE, VOLUME, ', cls=Symbol)

# TODO: 通用算子。时序、横截面和整体都能使用的算子。请根据需要补充
log, sign, = symbols('log, sign, ', cls=Function)

# TODO: 时序算子。需要提前按资产分组，组内按时间排序。请根据需要补充。必需以`ts_`开头
ts_delay, ts_delta, ts_mean, ts_corr, = symbols('ts_delay, ts_delta, ts_mean, ts_corr, ', cls=Function)

# TODO: 横截面算子。需要提前按时间分组。请根据需要补充。必需以`cs_`开头
cs_rank, = symbols('cs_rank, ', cls=Function)

# TODO: 等待简化的表达式。多个表达式一起能简化最终表达式
origin_exprs = {
    "expr_1": -ts_corr(cs_rank(ts_mean(OPEN, 10)), cs_rank(ts_mean(CLOSE, 10)), 10),
    "expr_2": cs_rank(ts_mean(OPEN, 10)) - ts_mean(CLOSE, 10),
    "expr_3": ts_mean(cs_rank(ts_mean(OPEN, 10)), 10),
    "expr_4": cs_rank(ts_mean(cs_rank(OPEN), 10)),
}

# 抽取时序与横截面子表达式
tool = ExprTool()
# 子表达式在前，原表式在最后
merged_exprs = tool.merge(**origin_exprs)

# 提取公共表达式
expr_2d, code_2d = tool.cse(merged_exprs,
                            symbols_repl=numbered_symbols('x_'),
                            symbols_redu=origin_exprs.keys())
# 生成代码
codes = tool.codegen(code_2d, expr_2d, origin_exprs)

# 保存
with open('output.py', 'w') as f:
    f.write(codes)

# reformat
os.system('python -m black -l 240 output.py')
