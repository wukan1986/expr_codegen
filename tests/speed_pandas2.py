import numpy as np
import pandas as pd


def getCols(k) -> str:
    return [f'x_{i}' for i in range(k)]


pd.testing.getCols = getCols
pd.testing._N = 250 * 10
pd.testing._K = 5000

# 生成5000支股票实在太慢，所以改用其它方案
# CLOSE = pd._testing.makeTimeDataFrame()

_N = 250 * 10
_K = 5000

asset = [f'x_{i}' for i in range(_K)]
date = pd.date_range('2000-01-1', periods=_N)

df_sort_by_asset = pd.DataFrame({
    'OPEN': np.random.rand(_K * _N),
    'HIGH': np.random.rand(_K * _N),
    'LOW': np.random.rand(_K * _N),
    'CLOSE': np.random.rand(_K * _N),
}, index=pd.MultiIndex.from_product([asset, date], names=['asset', 'date'])).reset_index()


def func_0_ts__asset__date(df: pd.DataFrame) -> pd.DataFrame:
    # ========================================
    # x_0 = ts_mean(OPEN, 10)
    df["x_0"] = df["OPEN"].rolling(10).mean()
    # expr_6 = ts_delta(OPEN, 10)
    df["expr_6"] = df["OPEN"].diff(10)
    # expr_7 = ts_delta(OPEN + 1, 10)
    df["expr_7"] = (df["OPEN"] + 1).diff(10)
    # x_1 = ts_mean(CLOSE, 10)
    df["x_1"] = df["CLOSE"].rolling(10).mean()
    assert df['date'].is_monotonic_increasing
    return df


def func_0_cs__date(df: pd.DataFrame) -> pd.DataFrame:
    # ========================================
    # x_2 = cs_rank(x_0)
    df["x_2"] = df["x_0"].rank(pct=True)
    # x_3 = cs_rank(x_1)
    df["x_3"] = df["x_1"].rank(pct=True)
    return df


def run1(df):
    df = df.groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date)
    assert df['date'].is_monotonic_increasing
    df = df.groupby(by=["date"], group_keys=False).apply(func_0_cs__date)
    assert df['date'].is_monotonic_increasing
    df = df.groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date)
    assert df['date'].is_monotonic_increasing

# 测sort的时机，内部折腾，外部顺序不变
df = df_sort_by_asset.sort_values(by=["date", "asset"]).reset_index(drop=True)
run1(df)
