import numpy as np
import pandas as pd
import polars as pl

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

df = pl.from_pandas(df_sort_by_asset)


def rank_pct(expr: pl.Expr) -> pl.Expr:
    """rank(pct=True)"""
    return expr.rank() / (expr.len() - expr.null_count())


def func_0_ts__asset__date(df: pl.DataFrame) -> pl.DataFrame:
    assert df['date'].to_pandas().is_monotonic_increasing
    # ========================================
    df = df.with_columns(
        # x_0 = ts_mean(OPEN, 10)
        x_0=(pl.col("OPEN").rolling_mean(10)),
        # expr_6 = ts_delta(OPEN, 10)
        expr_6=(pl.col("OPEN").diff(10)),
        # x_1 = ts_mean(CLOSE, 10)
        x_1=(pl.col("CLOSE").rolling_mean(10)),
    )
    return df


def func_0_cs__date(df: pl.DataFrame) -> pl.DataFrame:
    # ========================================
    df = df.with_columns(
        # x_6 = cs_rank(OPEN)
        x_6=(rank_pct(pl.col("OPEN"))),
    )
    # ========================================
    df = df.with_columns(
        # x_2 = cs_rank(x_0)
        x_2=(rank_pct(pl.col("x_0"))),
        # x_3 = cs_rank(x_1)
        x_3=(rank_pct(pl.col("x_1"))),
    )
    return df


def run1(df):
    df = df.groupby(by=["asset"], maintain_order=True).apply(func_0_ts__asset__date)
    # 输出也是按同股票在一起，所以整体无法通过
    # assert df['date'].to_pandas().is_monotonic_increasing
    df = df.groupby(by=["date"], maintain_order=False).apply(func_0_cs__date)
    # 输了更乱了
    #assert df['date'].to_pandas().is_monotonic_increasing
    df = df.groupby(by=["asset"], maintain_order=True).apply(func_0_ts__asset__date)
    # assert df['date'].to_pandas().is_monotonic_increasing

# 测sort的时机，输出结果很快就变了
run1(df)
