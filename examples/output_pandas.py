import re

import numpy as np
import pandas as pd

from loguru import logger

# TODO: load data
df = pd.DataFrame()


def func_0_ts__asset__date(df: pd.DataFrame) -> pd.DataFrame:
    # x_0 = ts_mean(OPEN, 10)
    df["x_0"] = df["OPEN"].rolling(10).mean()
    # x_1 = ts_mean(CLOSE, 10)
    df["x_1"] = df["CLOSE"].rolling(10).mean()
    return df


def func_0_cs__date(df: pd.DataFrame) -> pd.DataFrame:
    # x_2 = cs_rank(x_0)
    df["x_2"] = (df["x_0"]).rank(pct=True)
    # x_3 = cs_rank(x_1)
    df["x_3"] = (df["x_1"]).rank(pct=True)
    return df


def func_0_cl(df: pd.DataFrame) -> pd.DataFrame:
    # x_4 = abs(log(x_1))
    df["x_4"] = np.log(df["x_1"]).abs()
    return df


def func_0_gp__date__sw_l1(df: pd.DataFrame) -> pd.DataFrame:
    # x_5 = gp_rank(sw_l1, CLOSE)
    df["x_5"] = (df["sw_l1"]).rank(pct=True)
    return df


def func_1_cs__date(df: pd.DataFrame) -> pd.DataFrame:
    # x_6 = cs_rank(OPEN)
    df["x_6"] = (df["OPEN"]).rank(pct=True)
    return df


def func_1_ts__asset__date(df: pd.DataFrame) -> pd.DataFrame:
    # x_7 = ts_mean(x_6, 10)
    df["x_7"] = df["x_6"].rolling(10).mean()
    # expr_1 = -ts_corr(x_2, x_3, 10)
    df["expr_1"] = -(df["x_2"]).rolling(10).corr(df["x_3"])
    return df


def func_1_cl(df: pd.DataFrame) -> pd.DataFrame:
    # expr_2 = x_2 - x_4 + x_5
    df["expr_2"] = df["x_2"] - df["x_4"] + df["x_5"]
    return df


def func_2_ts__asset__date(df: pd.DataFrame) -> pd.DataFrame:
    # expr_3 = ts_mean(x_2, 10)
    df["expr_3"] = df["x_2"].rolling(10).mean()
    return df


def func_2_cs__date(df: pd.DataFrame) -> pd.DataFrame:
    # expr_4 = cs_rank(x_7)
    df["expr_4"] = (df["x_7"]).rank(pct=True)
    return df


def func_3_ts__asset__date(df: pd.DataFrame) -> pd.DataFrame:
    # expr_5 = -ts_corr(OPEN, CLOSE, 10)
    df["expr_5"] = -(df["OPEN"]).rolling(10).corr(df["CLOSE"])
    # expr_6 = ts_delta(OPEN, 10)
    df["expr_6"] = df["OPEN"].diff(10)
    return df


logger.info("start...")


df = df.sort_values(by=["asset", "date"]).groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date)
df = df.groupby(by=["date"], group_keys=False).apply(func_0_cs__date)
df = func_0_cl(df)
df = df.groupby(by=["date", "sw_l1"], group_keys=False).apply(func_0_gp__date__sw_l1)
df = df.groupby(by=["date"], group_keys=False).apply(func_1_cs__date)
df = df.sort_values(by=["asset", "date"]).groupby(by=["asset"], group_keys=False).apply(func_1_ts__asset__date)
df = func_1_cl(df)
df = df.sort_values(by=["asset", "date"]).groupby(by=["asset"], group_keys=False).apply(func_2_ts__asset__date)
df = df.groupby(by=["date"], group_keys=False).apply(func_2_cs__date)
df = df.sort_values(by=["asset", "date"]).groupby(by=["asset"], group_keys=False).apply(func_3_ts__asset__date)


# x_0 = ts_mean(OPEN, 10)
# x_1 = ts_mean(CLOSE, 10)
# x_2 = cs_rank(x_0)
# x_3 = cs_rank(x_1)
# x_4 = abs(log(x_1))
# x_5 = gp_rank(sw_l1, CLOSE)
# x_6 = cs_rank(OPEN)
# x_7 = ts_mean(x_6, 10)
# expr_1 = -ts_corr(x_2, x_3, 10)
# expr_2 = x_2 - x_4 + x_5
# expr_3 = ts_mean(x_2, 10)
# expr_4 = cs_rank(x_7)
# expr_5 = -ts_corr(OPEN, CLOSE, 10)
# expr_6 = ts_delta(OPEN, 10)

# expr_1 = -ts_corr(cs_rank(ts_mean(OPEN, 10)), cs_rank(ts_mean(CLOSE, 10)), 10)
# expr_2 = -abs(log(ts_mean(CLOSE, 10))) + cs_rank(ts_mean(OPEN, 10)) + gp_rank(sw_l1, CLOSE)
# expr_3 = ts_mean(cs_rank(ts_mean(OPEN, 10)), 10)
# expr_4 = cs_rank(ts_mean(cs_rank(OPEN), 10))
# expr_5 = -ts_corr(OPEN, CLOSE, 10)
# expr_6 = ts_delta(OPEN, 10)

# drop intermediate columns
df = df.drop(columns=filter(lambda x: re.search(r"^x_\d+", x), df.columns))


logger.info("done")

# save
# df.to_parquet('output.parquet', compression='zstd')

print(df.tail(5))
