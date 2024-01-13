import pandas as pd
import polars as pl
from matplotlib import pyplot as plt
from polars_ta.performance.returns import cumulative_returns
from polars_ta.wq import cs_bucket


def calc_return_by_quantile(df: pl.DataFrame, x: str, y: str, q: int = 10, by: str = 'date', asset: str = 'asset') -> pl.DataFrame:
    """收益率按因子分组，只能选择一期收益率

    Examples
    --------
    >>> calc_return_by_quantile(df, 'GP_0000', 'RETURN_OO_1'])
    """

    def _func_cs(df: pl.DataFrame):
        return df.select([
            by,
            asset,
            cs_bucket(pl.col(x), q),
            y,
        ])

    return df.group_by(by=by).map_groups(_func_cs)


def plot_quantile_portfolio(df: pl.DataFrame, x: str, y: str, q: int = 10, period: int = 5) -> pd.DataFrame:
    df = df.to_pandas().set_index(['date', 'asset'])
    rr = df[y].unstack()  # 1日收益率
    pp = df[x].unstack()  # 信号仓位

    out = pd.DataFrame(index=rr.index)
    rr = rr.to_numpy()
    pp = pp.to_numpy()
    for i in range(q):
        out[f'G{i}'] = cumulative_returns(rr, pp == i, period=period, is_mean=True)
    return out


def create_portfolio_sheet(df: pl.DataFrame, x: str, y, q: int = 10, period=5, by: str = 'date', asset: str = 'asset'):
    df = calc_return_by_quantile(df, x, y, q, by, asset)

    out = plot_quantile_portfolio(df, x, y, q, period)
    fig, axes = plt.subplots(1, 1, figsize=(12, 9))
    out.plot(ax=axes, cmap='coolwarm')
