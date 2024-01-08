"""
!!! 所有新补充的`Function`, 如果表示方式特殊则需要在`printer.py`中添加对应的处理代码

# 由于与buildins中函数重复，所以重新定义max_, min_, abs_
# sign由于会被翻译成Piecewise，所以使用自义函数sign

"""
from sympy import Add, Mul, Pow, Eq  # noqa
from sympy import Symbol, Function, symbols  # noqa

# 由于实现了函数名自注册，现在只要import即可，如果你要使用其它库也可以修改此处
_ = 0  # 只要之前出现了语句，之后的import位置不参与调整
from polars_ta.prefix.talib import *  # noqa
from polars_ta.prefix.tdx import *  # noqa
from polars_ta.prefix.ta import *  # noqa
from polars_ta.prefix.wq import *  # noqa
from polars_ta.prefix.cdl import *  # noqa

# TODO: 通用算子。时序、横截面和整体都能使用的算子。请根据需要补充

# TODO: 时序算子。需要提前按资产分组，组内按时间排序。请根据需要补充。必需以`ts_`开头

# TODO: 横截面算子。需要提前按时间分组。请根据需要补充。必需以`cs_`开头

# TODO: 分组算子。需要提前按时间、行业分组。必需以`gp_`开头
gp_rank, gp_demean, = symbols('gp_rank, gp_demean, ', cls=Function)

# TODO: 因子。请根据需要补充
OPEN, HIGH, LOW, CLOSE, VOLUME, AMOUNT, OPEN_INTEREST, = symbols('OPEN, HIGH, LOW, CLOSE, VOLUME, AMOUNT, OPEN_INTEREST, ', cls=Symbol)
