"""
由于因子的计算步骤很多，又很耗时，如果能提前横截面过滤，只计算重要的品种，是否能加快计算？
"""
import time

import pandas as pd
import polars as pl
from polars_ta.prefix.wq import *

from expr_codegen import codegen_exec

_N = 50
_K = 5000

asset = [f's_{i:04d}' for i in range(_K)]
date = pd.date_range('2015-1-1', periods=_N)

df = pd.DataFrame({
    'RETURNS': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'VWAP': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'LOW': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'CLOSE': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
}, index=pd.MultiIndex.from_product([date, asset], names=['date', 'asset'])).reset_index()
df = pl.from_pandas(df)


def _code_block_1():
    cond1 = ts_returns(CLOSE, 5)
    cond2 = cond1 > 0


df1 = codegen_exec(df, _code_block_1, over_null='partition_by', ge_date_idx=-1).select('asset', 'cond2').filter(
    pl.col('cond2'))
print(df1)
# 后面只对cond2=true的计算


t1 = time.perf_counter()
# 方案1
df2 = pl.concat([df, df1], how='align_left').filter(pl.col('cond2'))
t2 = time.perf_counter()
# 方案2
df2 = df.join(df1, on=['asset'], how='left').filter(pl.col('cond2'))
t3 = time.perf_counter()
# 方案3
assets = set(df1['asset'].to_list())
df2 = df.filter(pl.col('asset').is_in(assets))
t4 = time.perf_counter()
print("耗时比较", t2 - t1, t3 - t2, t4 - t3)


def _code_block_2():
    MA1 = ts_mean(CLOSE, 5)
    MA2 = ts_mean(CLOSE, 10)
    MA3 = ts_mean(CLOSE, 20)


df3 = codegen_exec(df2, _code_block_2, over_null='partition_by', ge_date_idx=-1)
print(df3)
