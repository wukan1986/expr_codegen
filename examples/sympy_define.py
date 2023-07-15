# !!! 所有新补充的`Function`都需要在`printer.py`中添加对应的处理代码

from sympy import Eq, Abs, Max, Min, log
from sympy import symbols, Symbol, Function, Add, Mul, Pow

# 引用一次，防止被IDE格式化。因为之后表达式中可能因为==被换成了Eq
_ = Add, Mul, Pow
# 容易冲突的算子还是用sympy中预定义 !!!注意 Abs, Max, Min是首字母大写
_ = Eq, Abs, Max, Min, log,

# TODO: 通用算子。时序、横截面和整体都能使用的算子。请根据需要补充
# sign由于会被翻译成Piecewise，所以使用自义函数
if_else, signed_power, sign, = symbols('if_else, signed_power, sign, ', cls=Function)

# TODO: 因子。请根据需要补充
OPEN, HIGH, LOW, CLOSE, VOLUME, AMOUNT, = symbols('OPEN, HIGH, LOW, CLOSE, VOLUME, AMOUNT, ', cls=Symbol)
RETURNS, VWAP, CAP, = symbols('RETURNS, VWAP, CAP, ', cls=Symbol)
ADV5, ADV10, ADV15, ADV20, ADV30, ADV40, ADV50, ADV60, ADV81, ADV120, ADV150, ADV180, = symbols('ADV5, ADV10, ADV15, ADV20, ADV30, ADV40, ADV50, ADV60, ADV81, ADV120, ADV150, ADV180,', cls=Symbol)

SECTOR, INDUSTRY, SUBINDUSTRY, = symbols('SECTOR, INDUSTRY, SUBINDUSTRY, ', cls=Symbol)

# TODO: 时序算子。需要提前按资产分组，组内按时间排序。请根据需要补充。必需以`ts_`开头
ts_delay, ts_delta, = symbols('ts_delay, ts_delta, ', cls=Function)
ts_arg_max, ts_arg_min, ts_max, ts_min, = symbols('ts_arg_max, ts_arg_min, ts_max, ts_min, ', cls=Function)
ts_sum, ts_mean, ts_decay_linear, ts_product, = symbols('ts_sum, ts_mean, ts_decay_linear, ts_product, ', cls=Function)
ts_std_dev, ts_corr, ts_covariance, = symbols('ts_std_dev, ts_corr, ts_covariance,', cls=Function)
ts_rank, = symbols('ts_rank, ', cls=Function)

# TODO: 横截面算子。需要提前按时间分组。请根据需要补充。必需以`cs_`开头
cs_rank, cs_scale, = symbols('cs_rank, cs_scale, ', cls=Function)

# TODO: 分组算子。需要提前按时间、行业分组。必需以`gp_`开头
gp_neutralize, = symbols('gp_neutralize, ', cls=Function)
