import timeit

import numpy as np
import pandas as pd


def getCols(k) -> str:
    return [f'x_{i}' for i in range(k)]


pd._testing.getCols = getCols
pd._testing._N = 250 * 10
pd._testing._K = 5000

# 生成5000支股票实在太慢，所以改用其它方案
# CLOSE = pd._testing.makeTimeDataFrame()

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
print(df.tail(10))


def func_0_ts__asset__date_1(df: pd.DataFrame) -> pd.DataFrame:
    # ========================================
    # x_0 = ts_mean(OPEN, 10)
    df["x_0"] = df["OPEN"].rolling(10).mean()
    # expr_6 = ts_delta(OPEN, 10)
    df["expr_6"] = df["OPEN"].diff(10)
    # expr_7 = ts_delta(OPEN + 1, 10)
    df["expr_7"] = (df["OPEN"] + 1).diff(10)
    # x_1 = ts_mean(CLOSE, 10)
    df["x_1"] = df["CLOSE"].rolling(10).mean()
    return df


def func_0_ts__asset__date_2(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(by=["date"])
    # ========================================
    # x_0 = ts_mean(OPEN, 10)
    df["x_0"] = df["OPEN"].rolling(10).mean()
    # expr_6 = ts_delta(OPEN, 10)
    df["expr_6"] = df["OPEN"].diff(10)
    # expr_7 = ts_delta(OPEN + 1, 10)
    df["expr_7"] = (df["OPEN"] + 1).diff(10)
    # x_1 = ts_mean(CLOSE, 10)
    df["x_1"] = df["CLOSE"].rolling(10).mean()
    return df


def func_0_cs__date(df: pd.DataFrame) -> pd.DataFrame:
    # ========================================
    # x_2 = cs_rank(x_0)
    df["x_2"] = df["x_0"].rank(pct=True)
    # x_3 = cs_rank(x_1)
    df["x_3"] = df["x_1"].rank(pct=True)
    return df


print('=' * 60)
# 10年，已经按日期，资产排序的情况下，3种情况速度并没有多大差异
# 21.95759929995984
# 23.93896960001439
# 23.232979799970053

print(timeit.timeit('df_sort_by_date.sort_values(by=["date"]).groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date_1)', number=3, globals=locals()))
print(timeit.timeit('df_sort_by_date.sort_values(by=["asset", "date"]).groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date_1)', number=3, globals=locals()))
print(timeit.timeit('df_sort_by_date.groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date_2)', number=3, globals=locals()))

print('=' * 60)
# 10年，已经按资产,日期排序的情况下，3种情况速度并没有多大差异
# 25.781703099957667
# 20.82362669997383
# 20.364632499986328
print(timeit.timeit('df_sort_by_asset.sort_values(by=["date"]).groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date_1)', number=3, globals=locals()))
print(timeit.timeit('df_sort_by_asset.sort_values(by=["asset", "date"]).groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date_1)', number=3, globals=locals()))
print(timeit.timeit('df_sort_by_asset.groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date_2)', number=3, globals=locals()))

print('=' * 60)
# 2年，乱序后，结果差异很大
# 56.11242270004004
# 45.11343280004803
# 34.87692619999871
print(timeit.timeit('df.sort_values(by=["date"]).groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date_1)', number=3, globals=locals()))
print(timeit.timeit('df.sort_values(by=["asset", "date"]).groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date_1)', number=3, globals=locals()))
print(timeit.timeit('df.groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date_2)', number=3, globals=locals()))
