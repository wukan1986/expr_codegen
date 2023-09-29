import timeit

import numpy as np
import pandas as pd
import polars as pl

_N = 250 * 10
_K = 5000

asset = [f'x_{i}' for i in range(_K)]
date = pd.date_range('2000-01-1', periods=_N)

df_sort_by_date = pd.DataFrame({
    'OPEN': np.random.rand(_K * _N),
    'HIGH': np.random.rand(_K * _N),
    'LOW': np.random.rand(_K * _N),
    'CLOSE': np.random.rand(_K * _N),
}, index=pd.MultiIndex.from_product([date, asset], names=['date', 'asset'])).reset_index()

df_sort_by_asset = pd.DataFrame({
    'OPEN': np.random.rand(_K * _N),
    'HIGH': np.random.rand(_K * _N),
    'LOW': np.random.rand(_K * _N),
    'CLOSE': np.random.rand(_K * _N),
}, index=pd.MultiIndex.from_product([asset, date], names=['asset', 'date'])).reset_index()

df_sort_by_date.info()
# 乱序
df = df_sort_by_date.sample(_K * _N * 2, replace=True, ignore_index=True)

df_sort_by_date = pl.from_pandas(df_sort_by_date)
df_sort_by_asset = pl.from_pandas(df_sort_by_asset)
df = pl.from_pandas(df)

print(df.tail(10))


def func_0_ts__asset__date_1(df: pl.DataFrame) -> pl.DataFrame:
    # ========================================
    df = df.with_columns(
        # x_0 = ts_mean(OPEN, 10)
        x_0=(pl.col("OPEN").rolling_mean(10)),
        # expr_6 = ts_delta(OPEN, 10)
        expr_6=(pl.col("OPEN").diff(10)),
        # x_1 = ts_mean(CLOSE, 10)
        x_1=(pl.col("CLOSE").rolling_mean(10)),
    )
    # print(df['date'])
    return df


def func_0_ts__asset__date_2(df: pl.DataFrame) -> pl.DataFrame:
    df = df.sort(by=["date"])
    df = df.with_columns(
        # x_0 = ts_mean(OPEN, 10)
        x_0=(pl.col("OPEN").rolling_mean(10)),
        # expr_6 = ts_delta(OPEN, 10)
        expr_6=(pl.col("OPEN").diff(10)),
        # x_1 = ts_mean(CLOSE, 10)
        x_1=(pl.col("CLOSE").rolling_mean(10)),
    )
    # print(df['date'])
    return df


print('=' * 60)
# 10年，已经按日期，资产排序的情况下，3种情况速度并没有多大差异
# 6.80373189994134
# 9.654270599945448
# 8.68796220002696

print(timeit.timeit('df_sort_by_date.sort(by=["date"]).groupby(by=["asset"], maintain_order=True).apply(func_0_ts__asset__date_1)', number=5, globals=locals()))
print(timeit.timeit('df_sort_by_date.sort(by=["asset", "date"]).groupby(by=["asset"], maintain_order=True).apply(func_0_ts__asset__date_1)', number=5, globals=locals()))
print(timeit.timeit('df_sort_by_date.groupby(by=["asset"], maintain_order=False).apply(func_0_ts__asset__date_2)', number=5, globals=locals()))

print('=' * 60)
# 10年，已经按资产,日期排序的情况下，3种情况速度并没有多大差异
# 8.119568099966273
# 7.845328400027938
# 7.50117709999904
print(timeit.timeit('df_sort_by_asset.sort(by=["date"]).groupby(by=["asset"], maintain_order=True).apply(func_0_ts__asset__date_1)', number=5, globals=locals()))
print(timeit.timeit('df_sort_by_asset.sort(by=["asset", "date"]).groupby(by=["asset"], maintain_order=True).apply(func_0_ts__asset__date_1)', number=5, globals=locals()))
print(timeit.timeit('df_sort_by_asset.groupby(by=["asset"], maintain_order=False).apply(func_0_ts__asset__date_2)', number=5, globals=locals()))

print('=' * 60)
# 2年，乱序后，结果差异很大
# 16.66170910000801
# 23.977682299911976
# 16.773866499890573
print(timeit.timeit('df.sort(by=["date"]).groupby(by=["asset"], maintain_order=True).apply(func_0_ts__asset__date_1)', number=5, globals=locals()))
print(timeit.timeit('df.sort(by=["asset", "date"]).groupby(by=["asset"], maintain_order=True).apply(func_0_ts__asset__date_1)', number=5, globals=locals()))
print(timeit.timeit('df.groupby(by=["asset"], maintain_order=False).apply(func_0_ts__asset__date_2)', number=5, globals=locals()))
