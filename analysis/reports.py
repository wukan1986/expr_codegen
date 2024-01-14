import polars as pl
from matplotlib import pyplot as plt

from analysis.information_coefficient import calc_ic, plot_ic_ts, plot_ic_hist, plot_ic_heatmap
from analysis.portfolio import calc_return_by_quantile, plot_quantile_portfolio, calc_cum_return_by_quantile


def create_simple_sheet(df: pl.DataFrame,
                        x: str,
                        y: str, y1: str,
                        q: int = 10, period: int = 5,
                        date: str = 'date', asset: str = 'asset'):
    """

    Parameters
    ----------
    df
    x
    y
    y1
    q
    period
    date
    asset

    Returns
    -------

    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    # 画IC信息
    df1 = calc_ic(df, x, [y], date)
    plot_ic_ts(df1, y, ax=axes[0, 0])
    plot_ic_hist(df1, y, ax=axes[0, 1])
    plot_ic_heatmap(df1, y, date, ax=axes[1, 0])

    # 画净值曲线
    df2 = calc_return_by_quantile(df, x, y1, q, date, asset)
    df3 = calc_cum_return_by_quantile(df2, x, y1, q, period, date, asset)
    plot_quantile_portfolio(df3, y1, period, ax=axes[1, 1])
