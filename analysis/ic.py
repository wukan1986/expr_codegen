from typing import Sequence

import pandas as pd
import polars as pl
import seaborn as sns
from matplotlib import pyplot as plt
from statsmodels import api as sm


def _ic(a: str, b: str) -> pl.Expr:
    """RankIC"""
    return pl.corr(a, b, method='spearman', ddof=0, propagate_nans=False)


def calc_ic(df: pl.DataFrame, x: str, yy: Sequence[str], *, date: str = 'date') -> pl.DataFrame:
    """计算一个因子与多个标签的IC

    Parameters
    ----------
    df: pl.DataFrame
    x:str
        因子
    yy:str
        标签列表
    date:str
        日期

    Examples
    --------
    # doctest: +SKIP
    >>> calc_ic(df, 'GP_0000', ['RETURN_OO_1', 'RETURN_OO_2', 'RETURN_CC_1'])

    """
    return df.group_by(by=[date]).agg(
        [_ic(y, x) for y in yy]
    ).sort(date)


def plot_ic_ts(df: pl.DataFrame, y: str, *, date: str = 'date', split_x=None, ax=None) -> None:
    """IC时序图

    Examples
    --------
    >>> plot_ic_ts(df, 'RETURN_OO_1')
    """
    df = df.select([date, y])

    df = df.select([
        date,
        pl.col(y).alias('ic'),
        pl.col(y).rolling_mean(20).alias('sma_20'),
        pl.col(y).cum_sum().alias('cum_sum'),
    ])

    df = df.to_pandas().dropna()
    s: pd.Series = df['ic']

    ic = s.mean()
    ir = s.mean() / s.std()
    rate = (s.abs() > 0.02).value_counts(normalize=True).loc[True]

    ax1 = df.plot.line(x=date, y=['ic', 'sma_20'], alpha=0.5, lw=1,
                       title=f"{y},IC={ic:0.4f},>0.02={rate:0.2f},IR={ir:0.4f}",
                       ax=ax)
    ax2 = df.plot.line(x=date, y=['cum_sum'], alpha=0.9, lw=1,
                       secondary_y='cum_sum', c='r',
                       ax=ax1)
    ax1.axhline(y=ic, c="r", ls="--", lw=1)
    ax.set_xlabel('')
    if split_x is not None:
        ax1.axvline(x=split_x, c="b", ls="--", lw=1)


def plot_ic_hist(df: pl.DataFrame, y: str, *, ax=None) -> None:
    """IC直方图

    Examples
    --------
    >>> plot_ic_hist(df, 'RETURN_OO_1')
    """
    a = df[y].to_pandas().dropna()

    mean = a.mean()
    std = a.std()
    skew = a.skew()
    kurt = a.kurt()

    ax = sns.histplot(a,
                      bins=50, kde=True,
                      stat="density", kde_kws=dict(cut=3),
                      alpha=.4, edgecolor=(1, 1, 1, .4),
                      ax=ax)

    ax.axvline(x=mean, c="r", ls="--", lw=1)
    ax.axvline(x=mean + std * 3, c="r", ls="--", lw=1)
    ax.axvline(x=mean - std * 3, c="r", ls="--", lw=1)
    ax.set_title(f"{y},mean={mean:0.4f},std={std:0.4f},skew={skew:0.4f},kurt={kurt:0.4f}")
    ax.set_xlabel('')


def plot_ic_qq(df: pl.DataFrame, y: str, *, ax=None) -> None:
    """IC QQ图

    Examples
    --------
    >>> plot_ic_qq(df, 'RETURN_OO_1')
    """
    a = df[y].to_pandas().dropna()

    sm.qqplot(a, fit=True, line='45', ax=ax)


def plot_ic_heatmap(df: pl.DataFrame, y: str, *, date: str = 'date', ax=None) -> None:
    """月度IC热力图"""
    df = df.select([date, y,
                    pl.col(date).dt.year().alias('year'),
                    pl.col(date).dt.month().alias('month')
                    ])
    df = df.group_by(by=['year', 'month']).agg(pl.mean(y))
    df = df.to_pandas().set_index(['year', 'month'])

    # https://matplotlib.org/2.0.2/examples/color/colormaps_reference.html
    ax = sns.heatmap(df[y].unstack(), annot=True, cmap='RdYlGn_r', cbar=False, annot_kws={"size": 7}, ax=ax)
    ax.set_title(f"{y},Monthly Mean IC")
    ax.set_xlabel('')


def print_ic_table(df: pl.DataFrame, x: str, yy: Sequence[str]):
    pass


def create_ic_sheet(df: pl.DataFrame, x: str, yy: Sequence[str], *, date: str = 'date', split_x='2020-01-01'):
    """生成IC图表"""
    df = calc_ic(df, x, yy, date=date)

    for y in yy:
        fig, axes = plt.subplots(2, 2, figsize=(12, 9))

        plot_ic_ts(df, y, date=date, split_x=split_x, ax=axes[0, 0])
        plot_ic_hist(df, y, ax=axes[0, 1])
        plot_ic_qq(df, y, ax=axes[1, 0])
        plot_ic_heatmap(df, y, date=date, ax=axes[1, 1])
