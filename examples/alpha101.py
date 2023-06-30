# File > Settings... > Editor > Code Style > Hard wrap at > 300
import os

from sympy import symbols, Symbol, Function, numbered_symbols, Eq

from expr_codegen.expr import ExprInspectByPrefix, ExprInspectByName
# TODO: 生成pandas代码的codegen，多个codegen只保留一个
from expr_codegen.pandas.code import codegen
# TODO: 生成polars代码的codegen，多个codegen只保留一个
# from expr_codegen.polars.code import codegen
# codegen工具类
from expr_codegen.tool import ExprTool

# !!! 所有新补充的`Function`都需要在`printer.py`中添加对应的处理代码

# TODO: 因子。请根据需要补充
OPEN, HIGH, LOW, CLOSE, VOLUME, AMOUNT, = symbols('OPEN, HIGH, LOW, CLOSE, VOLUME, AMOUNT, ', cls=Symbol)
RETURNS, VWAP, ADV20, = symbols('RETURNS, VWAP, ADV20, ', cls=Symbol)

sw_l1, = symbols('sw_l1, ', cls=Symbol)

# TODO: 通用算子。时序、横截面和整体都能使用的算子。请根据需要补充
log, sign, abs, if_else, signed_power, = symbols('log, sign, abs, if_else, signed_power, ', cls=Function)

# TODO: 时序算子。需要提前按资产分组，组内按时间排序。请根据需要补充。必需以`ts_`开头
ts_delay, ts_delta, ts_mean, ts_corr, ts_covariance, = symbols('ts_delay, ts_delta, ts_mean, ts_corr, ts_covariance,', cls=Function)
ts_arg_max, ts_arg_min, ts_max, ts_min, = symbols('ts_arg_max, ts_arg_min, ts_max, ts_min, ', cls=Function)
ts_std_dev, ts_rank, = symbols('ts_std_dev, ts_rank, ', cls=Function)
ts_sum, = symbols('ts_sum, ', cls=Function)

# TODO: 横截面算子。需要提前按时间分组。请根据需要补充。必需以`cs_`开头
cs_rank, cs_scale, = symbols('cs_rank, cs_scale, ', cls=Function)

# TODO: 分组算子。需要提前按时间、行业分组。必需以`gp_`开头
gp_rank, = symbols('gp_rank, ', cls=Function)

# TODO: 等待简化的表达式。多个表达式一起能简化最终表达式
exprs_src = {
    "alpha_001": (cs_rank(ts_arg_max(signed_power(if_else((RETURNS < 0), ts_std_dev(RETURNS, 20), CLOSE), 2.), 5)) - 0.5),
    "alpha_002": (-1 * ts_corr(cs_rank(ts_delta(log(VOLUME), 2)), cs_rank(((CLOSE - OPEN) / OPEN)), 6)),
    "alpha_003": (-1 * ts_corr(cs_rank(OPEN), cs_rank(VOLUME), 10)),
    "alpha_004": (-1 * ts_rank(cs_rank(LOW), 9)),
    "alpha_005": (cs_rank((OPEN - (ts_sum(VWAP, 10) / 10))) * (-1 * abs(cs_rank((CLOSE - VWAP))))),
    "alpha_006": -1 * ts_corr(OPEN, VOLUME, 10),
    "alpha_007": if_else((ADV20 < VOLUME), ((-1 * ts_rank(abs(ts_delta(CLOSE, 7)), 60)) * sign(ts_delta(CLOSE, 7))), (-1 * 1)),
    "alpha_008": (-1 * cs_rank(((ts_sum(OPEN, 5) * ts_sum(RETURNS, 5)) - ts_delay((ts_sum(OPEN, 5) * ts_sum(RETURNS, 5)), 10)))),
    "alpha_009": if_else((0 < ts_min(ts_delta(CLOSE, 1), 5)), ts_delta(CLOSE, 1), if_else((ts_max(ts_delta(CLOSE, 1), 5) < 0), ts_delta(CLOSE, 1), (-1 * ts_delta(CLOSE, 1)))),
    "alpha_010": cs_rank(if_else((0 < ts_min(ts_delta(CLOSE, 1), 4)), ts_delta(CLOSE, 1), if_else((ts_max(ts_delta(CLOSE, 1), 4) < 0), ts_delta(CLOSE, 1), (-1 * ts_delta(CLOSE, 1))))),
    "alpha_011": ((cs_rank(ts_max((VWAP - CLOSE), 3)) + cs_rank(ts_min((VWAP - CLOSE), 3))) * cs_rank(ts_delta(VOLUME, 3))),
    "alpha_012": (sign(ts_delta(VOLUME, 1)) * (-1 * ts_delta(CLOSE, 1))),
    "alpha_013": (-1 * cs_rank(ts_covariance(cs_rank(CLOSE), cs_rank(VOLUME), 5))),
    "alpha_014": ((-1 * cs_rank(ts_delta(RETURNS, 3))) * ts_corr(OPEN, VOLUME, 10)),
    "alpha_015": (-1 * ts_sum(cs_rank(ts_corr(cs_rank(HIGH), cs_rank(VOLUME), 3)), 3)),
    "alpha_016": (-1 * cs_rank(ts_covariance(cs_rank(HIGH), cs_rank(VOLUME), 5))),
    "alpha_017": (((-1 * cs_rank(ts_rank(CLOSE, 10))) * cs_rank(ts_delta(ts_delta(CLOSE, 1), 1))) * cs_rank(ts_rank((VOLUME / ADV20), 5))),
    "alpha_018": (-1 * cs_rank(((ts_std_dev(abs((CLOSE - OPEN)), 5) + (CLOSE - OPEN)) + ts_corr(CLOSE, OPEN, 10)))),
    "alpha_019": ((-1 * sign(((CLOSE - ts_delay(CLOSE, 7)) + ts_delta(CLOSE, 7)))) * (1 + cs_rank((1 + ts_sum(RETURNS, 250))))),
    "alpha_020": (((-1 * cs_rank((OPEN - ts_delay(HIGH, 1)))) * cs_rank((OPEN - ts_delay(CLOSE, 1)))) * cs_rank((OPEN - ts_delay(LOW, 1)))),
    "alpha_021": if_else((((ts_sum(CLOSE, 8) / 8) + ts_std_dev(CLOSE, 8)) < (ts_sum(CLOSE, 2) / 2)), (-1 * 1), if_else(((ts_sum(CLOSE, 2) / 2) < ((ts_sum(CLOSE, 8) / 8) - ts_std_dev(CLOSE, 8))), 1, if_else(((1 < (VOLUME / ADV20)) | Eq((VOLUME / ADV20), 1)), 1, (-1 * 1)))),
    "alpha_022": (-1 * (ts_delta(ts_corr(HIGH, VOLUME, 5), 5) * cs_rank(ts_std_dev(CLOSE, 20)))),
    "alpha_023": if_else(((ts_sum(HIGH, 20) / 20) < HIGH), (-1 * ts_delta(HIGH, 2)), 0),
    "alpha_024": if_else((((ts_delta((ts_sum(CLOSE, 100) / 100), 100) / ts_delay(CLOSE, 100)) < 0.05) | ((ts_delta((ts_sum(CLOSE, 100) / 100), 100) / ts_delay(CLOSE, 100)) == 0.05)), (-1 * (CLOSE - ts_min(CLOSE, 100))), (-1 * ts_delta(CLOSE, 3))),
    "alpha_025": cs_rank(((((-1 * RETURNS) * ADV20) * VWAP) * (HIGH - CLOSE))),
    "alpha_026": (-1 * ts_max(ts_corr(ts_rank(VOLUME, 5), ts_rank(HIGH, 5), 5), 3)),
    "alpha_027": if_else((0.5 < cs_rank((ts_sum(ts_corr(cs_rank(VOLUME), cs_rank(VWAP), 6), 2) / 2.0))), (-1 * 1), 1),
    "alpha_028": cs_scale(((ts_corr(ADV20, LOW, 5) + ((HIGH + LOW) / 2)) - CLOSE)),
    # "alpha_029": (min(product(cs_rank(cs_rank(cs_scale(log(ts_sum(ts_min(cs_rank(cs_rank((-1 * cs_rank(ts_delta((CLOSE - 1), 5))))), 2), 1))))), 1), 5) + ts_rank(ts_delay((-1 * RETURNS), 6), 5)),
    "alpha_030": (((1.0 - cs_rank(((sign((CLOSE - ts_delay(CLOSE, 1))) + sign((ts_delay(CLOSE, 1) - ts_delay(CLOSE, 2)))) + sign((ts_delay(CLOSE, 2) - ts_delay(CLOSE, 3)))))) * ts_sum(VOLUME, 5)) / ts_sum(VOLUME, 20)),
    # "alpha_031": ((rank(rank(rank(decay_linear((-1 * rank(rank(delta(close, 10)))), 10)))) + rank((-1 *delta(close, 3)))) + sign(scale(correlation(adv20, low, 12)))),
    "alpha_032": (cs_scale(((ts_sum(CLOSE, 7) / 7) - CLOSE)) + (20 * cs_scale(ts_corr(VWAP, ts_delay(CLOSE, 5), 230)))),
    "alpha_033": cs_rank((-1 * ((1 - (OPEN / CLOSE)) ** 1))),
    "alpha_034": cs_rank(((1 - cs_rank((ts_std_dev(RETURNS, 2) / ts_std_dev(RETURNS, 5)))) + (1 - cs_rank(ts_delta(CLOSE, 1))))),
    "alpha_035": ((ts_rank(VOLUME, 32) * (1 - ts_rank(((CLOSE + HIGH) - LOW), 16))) * (1 - ts_rank(RETURNS, 32))),
    # "alpha_036": (((((2.21 * cs_rank(ts_corr((CLOSE - OPEN), ts_delay(VOLUME, 1), 15))) + (0.7 * cs_rank((OPEN - CLOSE)))) + (0.73 * cs_rank(ts_rank(ts_delay((-1 * RETURNS), 6), 5)))) + cs_rank(abs(ts_corr(VWAP, ADV20, 6)))) + (0.6 * cs_rank((((ts_sum(CLOSE, 200) / 200) - OPEN) * (CLOSE - OPEN))))),
    "alpha_037": (cs_rank(ts_corr(ts_delay((OPEN - CLOSE), 1), CLOSE, 200)) + cs_rank((OPEN - CLOSE))),
    "alpha_038": ((-1 * cs_rank(ts_rank(CLOSE, 10))) * cs_rank((CLOSE / OPEN))),
    # "alpha_039": ((-1 * cs_rank((ts_delta(CLOSE, 7) * (1 - rank(decay_linear((VOLUME / adv20), 9)))))) * (1 +rank(sum(returns, 250)))),
    "alpha_040": ((-1 * cs_rank(ts_std_dev(HIGH, 10))) * ts_corr(HIGH, VOLUME, 10)),
    "alpha_041": (((HIGH * LOW) ** 0.5) - VWAP),
    "alpha_042": (cs_rank((VWAP - CLOSE)) / cs_rank((VWAP + CLOSE))),
    "alpha_043": (ts_rank((VOLUME / ADV20), 20) * ts_rank((-1 * ts_delta(CLOSE, 7)), 8)),
    "alpha_044": (-1 * ts_corr(HIGH, cs_rank(VOLUME), 5)),
    "alpha_045": (-1 * ((cs_rank((ts_sum(ts_delay(CLOSE, 5), 20) / 20)) * ts_corr(CLOSE, VOLUME, 2)) * cs_rank(ts_corr(ts_sum(CLOSE, 5), ts_sum(CLOSE, 20), 2)))),
    "alpha_046": if_else((0.25 < (((ts_delay(CLOSE, 20) - ts_delay(CLOSE, 10)) / 10) - ((ts_delay(CLOSE, 10) - CLOSE) / 10))), (-1 * 1),
                         if_else(((((ts_delay(CLOSE, 20) - ts_delay(CLOSE, 10)) / 10) - ((ts_delay(CLOSE, 10) - CLOSE) / 10)) < 0), 1, ((-1 * 1) * (CLOSE - ts_delay(CLOSE, 1))))),
    "alpha_047": ((((cs_rank((1 / CLOSE)) * VOLUME) / ADV20) * ((HIGH * cs_rank((HIGH - CLOSE))) / (ts_sum(HIGH, 5) / 5))) - cs_rank((VWAP - ts_delay(VWAP, 5)))),

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
codes = codegen(exprs_ldl, exprs_src)

# TODO: 保存文件
output_file = 'output_alpha101.py'
with open(output_file, 'w') as f:
    f.write(codes)

# reformat
os.system(f'python -m black -l 500 {output_file}')
