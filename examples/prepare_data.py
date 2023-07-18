"""
准备测试数据，可用于遗传算法

"""
import numpy as np
import pandas as pd
import polars as pl

_N = 250 * 10
_K = 500

asset = [f's_{i}' for i in range(_K)]
date = pd.date_range('2000-01-1', periods=_N)

df = pd.DataFrame({
    'OPEN': np.cumprod(1 + (np.random.rand(_K * _N) - 0.5).reshape(_N, -1) / 100, axis=0).reshape(-1),
    'HIGH': np.cumprod(1 + (np.random.rand(_K * _N) - 0.5).reshape(_N, -1) / 100, axis=0).reshape(-1),
    'LOW': np.cumprod(1 + (np.random.rand(_K * _N) - 0.5).reshape(_N, -1) / 100, axis=0).reshape(-1),
    'CLOSE': np.cumprod(1 + (np.random.rand(_K * _N) - 0.5).reshape(_N, -1) / 100, axis=0).reshape(-1),
}, index=pd.MultiIndex.from_product([date, asset], names=['date', 'asset'])).reset_index()

# 向脚本输入数据
df = pl.from_pandas(df)

"""
LABEL_OO_1=ts_delay(OPEN, -2)/ts_delay(OPEN, -1)-1 # 第二天开盘交易
LABEL_OO_2=ts_delay(OPEN, -3)/ts_delay(OPEN, -1)-1 # 第二天开盘交易，持有二天
LABEL_CC_1=ts_delay(CLOSE, -1)/CLOSE-1 # 每天收盘交易
"""


def func_0_ts__asset__date(df: pl.DataFrame) -> pl.DataFrame:
    df = df.sort(by=["date"])
    # ========================================
    df = df.with_columns(
        # _x_0 = 1/ts_delay(OPEN, -1)
        _x_0=(1 / pl.col("OPEN").shift(-1)),
        # LABEL_CC_1 = (-CLOSE + ts_delay(CLOSE, -1))/CLOSE
        LABEL_CC_1=((-pl.col("CLOSE") + pl.col("CLOSE").shift(-1)) / pl.col("CLOSE")),
    )
    # ========================================
    df = df.with_columns(
        # LABEL_OO_1 = _x_0*ts_delay(OPEN, -2) - 1
        LABEL_OO_1=(pl.col("_x_0") * pl.col("OPEN").shift(-2) - 1),
        # LABEL_OO_2 = _x_0*ts_delay(OPEN, -3) - 1
        LABEL_OO_2=(pl.col("_x_0") * pl.col("OPEN").shift(-3) - 1),
    )
    return df


df = df.sort(by=["date", "asset"])
df = df.groupby(by=["asset"], maintain_order=True).apply(func_0_ts__asset__date)

# save
df.write_parquet('data.parquet', compression='zstd')
