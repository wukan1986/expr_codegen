# !!! 所有新补充的`Function`都需要在`printer.py`中添加对应的处理代码
from sympy import symbols, Symbol, Function, Add, Mul, Pow, Eq, Abs, Max, Min, log

# 容易冲突的算子还是用sympy中预定义 !!!注意 Abs, Max, Min是首字母大写
_ = Add, Mul, Pow, Eq, Abs, Max, Min, log,

# TODO: 通用算子。时序、横截面和整体都能使用的算子。请根据需要补充
# sign由于会被翻译成Piecewise，所以使用自义函数
if_else, signed_power, sign, = symbols('if_else, signed_power, sign, ', cls=Function)

# TODO: 时序算子。需要提前按资产分组，组内按时间排序。请根据需要补充。必需以`ts_`开头
ts_delay, ts_delta, = symbols('ts_delay, ts_delta, ', cls=Function)
ts_arg_max, ts_arg_min, ts_max, ts_min, = symbols('ts_arg_max, ts_arg_min, ts_max, ts_min, ', cls=Function)
ts_sum, ts_mean, ts_decay_linear, ts_product, = symbols('ts_sum, ts_mean, ts_decay_linear, ts_product, ', cls=Function)
ts_std_dev, ts_corr, ts_covariance, = symbols('ts_std_dev, ts_corr, ts_covariance,', cls=Function)
ts_rank, = symbols('ts_rank, ', cls=Function)

# TODO: 横截面算子。需要提前按时间分组。请根据需要补充。必需以`cs_`开头
cs_rank, cs_scale, = symbols('cs_rank, cs_scale, ', cls=Function)

# TODO: 分组算子。需要提前按时间、行业分组。必需以`gp_`开头
gp_rank, gp_demean, = symbols('gp_rank, gp_demean, ', cls=Function)

# TODO: 因子。请根据需要补充
OPEN, HIGH, LOW, CLOSE, VOLUME, AMOUNT, = symbols('OPEN, HIGH, LOW, CLOSE, VOLUME, AMOUNT, ', cls=Symbol)
