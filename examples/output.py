import re

import polars as pl
import polars.selectors as cs

from loguru import logger

# TODO: load data
df = pl.DataFrame()

ASSET = "asset"
DATE = "date"


def expr_rank_pct(expr):
    """rank(pct=True)"""
    return expr.rank() / (expr.len() - expr.null_count())


# step 0
def func_0_ts(df: pl.DataFrame):
    df = df.with_columns(
        # x_0 = ts_mean(OPEN, 10)
        x_0=(pl.col("OPEN").rolling_mean(10)),
        # x_1 = ts_mean(CLOSE, 10)
        x_1=(pl.col("CLOSE").rolling_mean(10)),
    )
    return df


def func_0_cs(df: pl.DataFrame):
    df = df.with_columns(
        # x_2 = cs_rank(x_0)
        x_2=(expr_rank_pct(pl.col("x_0"))),
        # x_3 = cs_rank(x_1)
        x_3=(expr_rank_pct(pl.col("x_1"))),
        # x_4 = cs_rank(OPEN)
        x_4=(expr_rank_pct(pl.col("OPEN"))),
    )
    return df


# step 1
def func_1_ts(df: pl.DataFrame):
    df = df.with_columns(
        # x_5 = ts_mean(x_4, 10)
        x_5=(pl.col("x_4").rolling_mean(10)),
        # expr_1 = -ts_corr(x_2, x_3, 10)
        expr_1=(-pl.rolling_corr(pl.col("x_2"), pl.col("x_3"), window_size=10)),
    )
    return df


# step 2
def func_2_cl(df: pl.DataFrame):
    df = df.with_columns(
        # expr_2 = -x_1 + x_2
        expr_2=(-pl.col("x_1") + pl.col("x_2")),
    )
    return df


def func_2_ts(df: pl.DataFrame):
    df = df.with_columns(
        # expr_3 = ts_mean(x_2, 10)
        expr_3=(pl.col("x_2").rolling_mean(10)),
    )
    return df


def func_2_cs(df: pl.DataFrame):
    df = df.with_columns(
        # expr_4 = cs_rank(x_5)
        expr_4=(expr_rank_pct(pl.col("x_5"))),
    )
    return df


logger.info("start...")


# step 0
df = df.sort(by=[ASSET, DATE]).groupby(by=[ASSET], maintain_order=True).apply(func_0_ts)
df = df.sort(by=[DATE]).groupby(by=[DATE], maintain_order=False).apply(func_0_cs)
# step 1
df = df.sort(by=[ASSET, DATE]).groupby(by=[ASSET], maintain_order=True).apply(func_1_ts)
# step 2
df = func_2_cl(df)
df = df.sort(by=[ASSET, DATE]).groupby(by=[ASSET], maintain_order=True).apply(func_2_ts)
df = df.sort(by=[DATE]).groupby(by=[DATE], maintain_order=False).apply(func_2_cs)


# x_0 = ts_mean(OPEN, 10)
# x_1 = ts_mean(CLOSE, 10)
# x_2 = cs_rank(x_0)
# x_3 = cs_rank(x_1)
# x_4 = cs_rank(OPEN)
# x_5 = ts_mean(x_4, 10)
# expr_1 = -ts_corr(x_2, x_3, 10)
# expr_2 = -x_1 + x_2
# expr_3 = ts_mean(x_2, 10)
# expr_4 = cs_rank(x_5)

# expr_1 = -ts_corr(cs_rank(ts_mean(OPEN, 10)), cs_rank(ts_mean(CLOSE, 10)), 10)
# expr_2 = cs_rank(ts_mean(OPEN, 10)) - ts_mean(CLOSE, 10)
# expr_3 = ts_mean(cs_rank(ts_mean(OPEN, 10)), 10)
# expr_4 = cs_rank(ts_mean(cs_rank(OPEN), 10))

# drop intermediate column
# import re
# df = df.drop(filter(lambda x: re.search(r'^x_\d+', x), df.columns))

# shrink
df = df.select(cs.all().shrink_dtype())
df = df.shrink_to_fit()

logger.info("done")

# save
# df.write_parquet('output.parquet', compression='zstd')

print(df.tail(5))
