"""
准备测试数据，可用于遗传算法

"""
import numpy as np
import pandas as pd
import polars as pl

_N = 250 * 10
_K = 500

asset = [f's_{i:04d}' for i in range(_K)]
date = pd.date_range('2015-1-1', periods=_N)

df = pd.DataFrame({
    'OPEN': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'HIGH': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'LOW': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'CLOSE': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
}, index=pd.MultiIndex.from_product([date, asset], names=['date', 'asset'])).reset_index()

# 向脚本输入数据
df = pl.from_pandas(df)

"""
RETURN_OO_1 = ts_delay(OPEN, -2) / ts_delay(OPEN, -1) - 1
RETURN_OO_2 = ts_delay(OPEN, -3) / ts_delay(OPEN, -1) - 1
RETURN_OO_5 = ts_delay(OPEN, -6) / ts_delay(OPEN, -1) - 1
RETURN_CC_1 = ts_delay(CLOSE, -1) / CLOSE - 1
"""
from codes.prepare_data import main

df = main(df)

# save
df.write_parquet('data.parquet', compression='zstd')
