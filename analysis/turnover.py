# 换手率
from typing import Sequence

import pandas as pd
import polars as pl
from matplotlib import pyplot as plt
from polars_ta.wq import cs_bucket


def _auto_corr(a: str, period: int) -> pl.Expr:
    return pl.corr(pl.col(a), pl.col(a).shift(period), method='spearman', ddof=0, propagate_nans=False).alias(f'AC{period:02d}')


def calc_auto_correlation(df: pl.DataFrame, x: str, *, periods: Sequence[int] = (1, 5, 10, 20), date: str = 'date'):
    """计算排序自相关"""
    return df.group_by(by=[date]).agg([_auto_corr(x, p) for p in periods]).sort(date)


def _list_to_set(x):
    return set() if x is None else set(x)


def _set_diff(curr: pd.Series, period: int):
    history = curr.shift(period).apply(_list_to_set)
    new_ = (curr - history)
    # 当前持仓中有多少是新股票
    return new_.apply(len) / curr.apply(len)


def calc_quantile_turnover(df: pl.DataFrame,
                           x: str, q: int = 10,
                           *,
                           periods: Sequence[int] = (1, 5, 10, 20),
                           date: str = 'date', asset: str = 'asset'):
    def _func_cs(df: pl.DataFrame):
        return df.select([
            date,
            asset,
            cs_bucket(pl.col(x), q).alias('factor_quantile'),
        ])

    def _func_ts(df: pd.DataFrame, periods=periods):
        for p in periods:
            df[f'P{p:02d}'] = _set_diff(df[asset], p)
        return df

    df1 = df.group_by(by=date).map_groups(_func_cs)
    df2: pd.DataFrame = df1.group_by(by=[date, 'factor_quantile']).agg(asset).sort(date).to_pandas()
    df2[asset] = df2[asset].apply(_list_to_set)
    df3 = df2.groupby(by='factor_quantile').apply(_func_ts)
    return df3


def plot_factor_auto_correlation(df: pl.DataFrame, *, split_x='2020-01-01', date: str = 'date', ax=None):
    df = df.to_pandas().set_index(date)
    ax = df.plot(title='Factor Auto Correlation', cmap='coolwarm', alpha=0.7, lw=1, grid=True, ax=ax)
    if split_x is not None:
        ax.axvline(x=split_x, c="b", ls="--", lw=1)


def plot_turnover_quantile(df, quantile: int = 0, *, periods: Sequence[int] = (1, 5, 10, 20), split_x='2020-01-01', date: str = 'date', ax=None):
    df = df[df['factor_quantile'] == quantile]
    df = df.set_index(date)
    df = df[[f'P{p:02d}' for p in periods]]
    ax = df.plot(title=f'Quantile {quantile} Mean Turnover', alpha=0.7, lw=1, grid=True, ax=ax)
    if split_x is not None:
        ax.axvline(x=split_x, c="b", ls="--", lw=1)


def create_turnover_sheet(df, x, q: int = 10, *, quantiles=(0, 9), periods: Sequence[int] = (1, 5, 10, 20), date: str = 'date', split_x='2020-01-01'):
    df1 = calc_auto_correlation(df, x, periods=periods, date=date)
    df2 = calc_quantile_turnover(df, x, q=q, periods=periods)

    fix, axes = plt.subplots(2, 1, figsize=(12, 9))
    plot_factor_auto_correlation(df1, split_x=split_x, date=date, ax=axes[0])
    for i, q in enumerate(quantiles):
        ax = plt.subplot(223 + i)
        plot_turnover_quantile(df2, quantile=q, periods=periods, split_x=split_x, date=date, ax=ax)
