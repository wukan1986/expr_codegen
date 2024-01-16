import pandas as pd
import polars as pl
import seaborn as sns
from matplotlib import pyplot as plt
from polars_ta.performance.returns import cumulative_returns
from polars_ta.wq import cs_bucket


def calc_return_by_quantile(df: pl.DataFrame, x: str, y: str, q: int = 10, date: str = 'date', asset: str = 'asset') -> pl.DataFrame:
    """收益率按因子分组

    Notes
    -----
    结果用来计算累积收益率，所以这里得传1期简单收益率

    Examples
    --------
    >>> calc_return_by_quantile(df, 'GP_0000', 'RETURN_OO_1'])
    """

    def _func_cs(df: pl.DataFrame):
        return df.select([
            date,
            asset,
            cs_bucket(pl.col(x), q).alias('factor_quantile'),
            y,
        ])

    return df.group_by(by=date).map_groups(_func_cs)


def calc_cum_return_by_quantile(df: pl.DataFrame, y: str, q: int = 10, period: int = 5,
                                *,
                                date='date', asset='asset') -> pd.DataFrame:
    df = df.to_pandas().set_index([date, asset])
    rr = df[y].unstack()  # 1日收益率
    pp = df['factor_quantile'].unstack()  # 信号仓位

    out = pd.DataFrame(index=rr.index)
    rr = rr.to_numpy()
    pp = pp.to_numpy()
    for i in range(q):
        out[f'G{i}'] = cumulative_returns(rr, pp == i, period=period, is_mean=True)
    return out


def plot_quantile_portfolio(df: pd.DataFrame, y: str, period: int = 5, *, split_x=None, ax=None) -> None:
    ax = df.plot(ax=ax, title=f'{y}, period={period}', cmap='coolwarm', lw=1, grid=True)
    ax.legend(loc='upper left')
    ax.set_xlabel('')
    if split_x is not None:
        ax.axvline(x=split_x, c="b", ls="--", lw=1)


def plot_portfolio_heatmap(df: pd.DataFrame, *, group='G9', ax=None) -> None:
    """月度热力图。可用于IC, 收益率等"""
    out = pd.DataFrame(index=df.index)
    out['year'] = out.index.year
    out['month'] = out.index.month
    out['first'] = df[group]
    out['last'] = df[group]
    out = out.groupby(by=['year', 'month']).agg({'first': 'first', 'last': 'last'})
    out['cum_ret'] = out['last'] / out['first'] - 1
    ax = sns.heatmap(out['cum_ret'].unstack(), annot=True, cmap='RdYlGn_r', cbar=False, annot_kws={"size": 7}, ax=ax)
    ax.set_title(f"{group},Monthly Return")
    ax.set_xlabel('')


def create_portfolio_sheet(df: pl.DataFrame,
                           x: str, y: str,
                           q: int = 10,
                           period=5,
                           *,
                           groups=('G0', 'G9'),
                           split_x=None,
                           date: str = 'date', asset: str = 'asset') -> None:
    df = calc_return_by_quantile(df, x, y, q, date=date, asset=asset)
    out = calc_cum_return_by_quantile(df, y, q, period, date=date, asset=asset)

    fix, axes = plt.subplots(2, 1, figsize=(12, 9))
    plot_quantile_portfolio(out, y, period, split_x=split_x, ax=axes[0])
    for i, g in enumerate(groups):
        ax = plt.subplot(223 + i)
        plot_portfolio_heatmap(out, group=g, ax=ax)
