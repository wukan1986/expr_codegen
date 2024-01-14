from typing import Sequence

import matplotlib.pyplot as plt
import polars as pl
import seaborn as sns
from polars_ta.wq import cs_bucket


def calc_returns_by_quantile(df: pl.DataFrame, x: str, yy: Sequence[str], q: int = 10, date: str = 'date') -> pl.DataFrame:
    """收益率按因子分组

    Examples
    --------
    >>> calc_returns_by_quantile(df, 'GP_0000', ['RETURN_OO_1', 'RETURN_OO_2', 'RETURN_CC_1'])
    """

    def _func_cs(df: pl.DataFrame):
        return df.select([
            date,
            cs_bucket(pl.col(x), q),
            *yy,
        ])

    return df.group_by(by=date).map_groups(_func_cs)


def plot_quantile_returns_bar(df: pl.DataFrame, x: str, yy: Sequence[str], ax=None):
    """分组收益柱状图

    Examples
    --------
    >>> plot_quantile_returns_bar(df, 'GP_0000', ['RETURN_OO_1', 'RETURN_OO_2', 'RETURN_CC_1'])
    """
    df = df.group_by(by=x).agg([pl.mean(y) for y in yy]).sort(x)
    df = df.to_pandas().set_index(x)
    ax = df.plot.bar(ax=ax)
    ax.set_title(f'{x},Mean Return By Factor Quantile')
    ax.set_xlabel('')


def plot_quantile_returns_violin(df: pl.DataFrame, x: str, yy: Sequence[str], ax=None):
    """分组收益小提琴图

    Examples
    --------
    >>> plot_quantile_returns_violin(df, 'GP_0000', ['RETURN_OO_1', 'RETURN_OO_2', 'RETURN_CC_1'])

    Notes
    -----
    速度有点慢
    """
    df = df.to_pandas().set_index(x)[yy]
    # TODO 超大数据有必要截断吗
    if len(df) > 5000 * 250:
        df = df.sample(5000 * 120)
    df = df.stack().reset_index()
    df.columns = ['x', 'hue', 'y']
    df = df.sort_values(by=['x', 'hue'])
    ax = sns.violinplot(data=df, x='x', y='y', hue='hue', ax=ax)
    ax.set_title(f'{x}, Return By Factor Quantile')
    ax.set_xlabel('')


def create_returns_sheet(df: pl.DataFrame, x: str, yy: Sequence[str], q: int = 10, date: str = 'date'):
    df = calc_returns_by_quantile(df, x, yy, q=q, date=date)

    fig, axes = plt.subplots(2, 1, figsize=(12, 9))

    plot_quantile_returns_bar(df, x, yy, ax=axes[0])
    plot_quantile_returns_violin(df, x, yy, ax=axes[1])
