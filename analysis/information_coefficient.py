from typing import Sequence, Optional

import polars as pl
import seaborn as sns
from matplotlib import pyplot as plt
from statsmodels import api as sm


def _ic(a: str, b: str) -> pl.Expr:
    """RankIC"""
    return pl.corr(a, b, method='spearman', ddof=0, propagate_nans=False)


def calc_ic(df: pl.DataFrame, x: str, yy: Sequence[str], date: str = 'date') -> pl.DataFrame:
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


def plot_ic_ts(df: pl.DataFrame, y: str, x: Optional[str] = 'date', ax=None) -> None:
    """IC时序图

    Examples
    --------
    >>> plot_ic_ts(df, 'RETURN_OO_1')
    """
    if x is None:
        df = df.select(y)
    else:
        df = df.select([x, y])

    df = df.select([
        x,
        pl.col(y).alias('ic'),
        pl.col(y).rolling_mean(20).alias('sma_20'),
        pl.col(y).cum_sum().alias('cum_sum'),
    ])

    df = df.to_pandas().dropna()

    ic = df['ic'].mean()
    ir = df['ic'].mean() / df['ic'].std(ddof=0)

    ax1 = df.plot.line(x=x, y=['ic', 'sma_20'], alpha=0.5, lw=1,
                       title=f"{y},IC={ic:0.4f},IR={ir:0.4f}",
                       ax=ax)
    ax2 = df.plot.line(x=x, y=['cum_sum'], alpha=0.9, lw=1,
                       secondary_y='cum_sum', c='r',
                       ax=ax1)
    ax1.axhline(y=ic, c="r", ls="--", lw=1)
    ax.set_xlabel('')


def plot_ic_hist(df: pl.DataFrame, y: str, ax=None) -> None:
    """IC直方图

    Examples
    --------
    >>> plot_ic_hist(df, 'RETURN_OO_1')
    """
    a = df[y].to_pandas().dropna()

    mean = a.mean()
    std = a.std(ddof=0)
    skew = a.skew()
    kurt = a.kurt()

    # plt.figure()
    ax = sns.histplot(a, bins=50, kde=True,
                      stat="density", kde_kws=dict(cut=3),
                      alpha=.4, edgecolor=(1, 1, 1, .4),
                      ax=ax)

    ax.axvline(x=mean, c="r", ls="--", lw=1)
    ax.axvline(x=mean + std * 3, c="r", ls="--", lw=1)
    ax.axvline(x=mean - std * 3, c="r", ls="--", lw=1)
    ax.set_title(f"{y},mean={mean:0.4f},std={std:0.4f},skew={skew:0.4f},kurt={kurt:0.4f}")
    ax.set_xlabel('')


def plot_ic_qq(df: pl.DataFrame, y: str, ax=None) -> None:
    """IC QQ图

    Examples
    --------
    >>> plot_ic_qq(df, 'RETURN_OO_1')
    """
    a = df[y].to_pandas().dropna()
    sm.qqplot(a, fit=True, line='45', ax=ax)


def plot_ic_heatmap(df: pl.DataFrame, y: str, date: str = 'date', ax=None) -> None:
    """月度热力图。可用于IC, 收益率等"""
    df = df.select([date, y,
                    pl.col(date).dt.year().alias('year'),
                    pl.col(date).dt.month().alias('month')
                    ])
    df = df.group_by(by=['year', 'month']).agg(pl.mean(y))
    df = df.to_pandas().set_index(['year', 'month'])
    # plt.figure()
    # https://matplotlib.org/2.0.2/examples/color/colormaps_reference.html
    ax = sns.heatmap(df[y].unstack(), annot=True, cmap='RdYlGn_r', cbar=False, annot_kws={"size": 7}, ax=ax)
    ax.set_title(f"{y},Monthly Mean IC")
    ax.set_xlabel('')


def print_ic_table(df: pl.DataFrame, x: str, yy: Sequence[str]):
    pass


def create_ic_sheet(df: pl.DataFrame, x: str, yy: Sequence[str], date: str = 'date'):
    """生成CI图表"""
    df = calc_ic(df, x, yy, date)

    for y in yy:
        fig, axes = plt.subplots(2, 2, figsize=(12, 9))

        plot_ic_ts(df, y, ax=axes[0, 0])
        plot_ic_hist(df, y, ax=axes[0, 1])
        plot_ic_qq(df, y, ax=axes[1, 0])
        plot_ic_heatmap(df, y, date, ax=axes[1, 1])
