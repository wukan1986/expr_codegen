import polars as pl
import seaborn as sns


def plot_heatmap(df: pl.DataFrame, y: str, x: str = 'date', ax=None) -> None:
    """月度热力图。可用于IC, 收益率等"""
    df = df.select([x, y,
                    pl.col(x).dt.year().alias('year'),
                    pl.col(x).dt.month().alias('month')
                    ])
    df = df.group_by(by=['year', 'month']).agg(pl.mean(y))
    df = df.to_pandas().set_index(['year', 'month'])
    # plt.figure()
    # https://matplotlib.org/2.0.2/examples/color/colormaps_reference.html
    ax = sns.heatmap(df[y].unstack(), annot=True, cmap='RdYlGn_r', cbar=False, annot_kws={"size": 7}, ax=ax)
    # ax.set_title(f"{y},Monthly Mean")
