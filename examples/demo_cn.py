from black import format_str, Mode
from sympy import numbered_symbols

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

# 子表达式在前，原表式在最后
exprs_dst, syms_dst = tool.merge(**exprs_src)

# 提取公共表达式
exprs_dict = tool.cse(exprs_dst, symbols_repl=numbered_symbols('x_'), symbols_redu=exprs_src.keys())
# 有向无环图流转
exprs_ldl = tool.dag()
# 是否优化
exprs_ldl.optimize(back_opt=True, chain_opt=True)

# 生成代码
is_polars = True
if is_polars:
    from expr_codegen.polars.code import codegen

    output_file = 'output_polars.py'
else:
    from expr_codegen.pandas.code import codegen

    output_file = 'output_pandas.py'

# 用户可根据自己需求指向其它模板
codes = codegen(exprs_ldl, exprs_src, syms_dst, filename='template.py.j2')

# TODO: reformat & output
res = format_str(codes, mode=Mode(line_length=500))
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(res)
