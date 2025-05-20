"""
估计最小数据长度

1. 停牌、上新股。都会对结果有影响
2. EMA算法特殊，参数10时，提供10个数据，和11个数据，结果是不一样的
3. MACD等不少指标底层是EMA
"""
import numpy as np
import pandas as pd
import polars as pl

from expr_codegen import codegen_exec

# TODO 预留500交易日
_N = 500
# TODO 可换成股票数
_K = 10

asset = [f's_{i:04d}' for i in range(_K)]
date = pd.date_range('2015-1-1', periods=_N)

df = pd.DataFrame({
    'VWAP': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'LOW': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'CLOSE': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
}, index=pd.MultiIndex.from_product([date, asset], names=['date', 'asset'])).reset_index()
# TODO 这里可以考虑替换成真实数据，但停牌会对结果有影响
df = pl.from_pandas(df)


def _code_block_1():
    # TODO 替换成自己的因子表达式
    A1 = ts_mean(CLOSE, 5)
    A2 = ts_returns(A1, 5)
    A3 = cs_rank(A2)
    A4 = ts_returns(A3, 10)


# TODO 可以用于事后检查计算得参数是否正确
df1: pl.DataFrame = codegen_exec(df, _code_block_1, over_null='partition_by')
# 检查null数量’
print(df1.null_count())
# 单股票时，时序上最大null数+1，就是tail理论最小参数
# 但部分截面因子无法在单票上得出有效值，所以还是得换成多股票版
n = df1.null_count().max_horizontal()[0] + _K
print("tail理论最小参数", n)

# 这里一定要排序后再tail
df2: pl.DataFrame = codegen_exec(df.sort('date', 'asset').tail(n), _code_block_1, over_null='partition_by')
# 如果设置正确，这里应当看到最后一行非null，倒数第二行null
print(df2.sort('asset', 'date').tail(3))
