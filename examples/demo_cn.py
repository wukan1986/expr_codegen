from black import format_str, Mode
from sympy import symbols, Symbol, Function, numbered_symbols

from expr_codegen.expr import ExprInspectByPrefix, ExprInspectByName
# codegen工具类
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
    "expr_2": cs_rank(ts_mean(OPEN, 10)) - abs(log(ts_mean(CLOSE, 10))) + gp_rank(sw_l1, CLOSE),  # + gp_rank(OPEN, CLOSE),
    "expr_3": ts_mean(cs_rank(ts_mean(OPEN, 10)), 10),
    "expr_4": cs_rank(ts_mean(cs_rank(OPEN), 10)),
    "expr_5": -ts_corr(OPEN, CLOSE, 10),
    "expr_6": ts_delta(OPEN, 10),
    "expr_7": ts_delta(OPEN + 1, 10),
}

# 根据算子前缀进行算子分类
inspect1 = ExprInspectByPrefix()

# TODO: 根据算子名称进行算子分类，名称不确定，所以需指定。如没有用到可不管理
inspect2 = ExprInspectByName(
    ts_names={ts_delay, ts_delta, ts_mean, ts_corr, },
    cs_names={cs_rank, },
    gp_names={gp_rank, },
)

# TODO: 一定要正确设定时间列名和资产列名，以及表达式识别类
tool = ExprTool(date='date', asset='asset', inspect=inspect1)

# 子表达式在前，原表式在最后
exprs_dst = tool.merge(**exprs_src)

# 提取公共表达式
graph_dag, graph_key, graph_exp = tool.cse(exprs_dst, symbols_repl=numbered_symbols('x_'), symbols_redu=exprs_src.keys())
# 有向无环图流转
exprs_ldl = tool.dag_ready(graph_dag, graph_key, graph_exp)
# 是否优化
exprs_ldl.optimize(back_opt=True, chains_opt=True)

# 生成代码
is_polars = False
if is_polars:
    from expr_codegen.polars.code import codegen

    output_file = 'output_polars.py'
else:
    from expr_codegen.pandas.code import codegen

    output_file = 'output_pandas.py'

codes = codegen(exprs_ldl, exprs_src)

# TODO: reformat & output
res = format_str(codes, mode=Mode(line_length=500))
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(res)
