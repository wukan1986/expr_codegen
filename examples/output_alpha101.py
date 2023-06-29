import re

import numpy as np
import pandas as pd

from loguru import logger

# TODO: load data
df = pd.DataFrame()


def signed_power(x, y):
    return x.sign() * (x.abs() ** y)


def func_0_ts__asset__date(df: pd.DataFrame) -> pd.DataFrame:
    # ========================================
    # x_10 = ts_sum(RETURNS, 5)
    df["x_10"] = df["RETURNS"].rolling(5).sum()
    # x_22 = ts_delta(RETURNS, 3)
    df["x_22"] = df["RETURNS"].diff(3)
    # x_32 = ts_sum(RETURNS, 250) + 1
    df["x_32"] = df["RETURNS"].rolling(250).sum() + 1
    # x_0 = ts_arg_max(signed_power(if_else(RETURNS < 0, ts_std_dev(RETURNS, 20), CLOSE), 2.0), 5)
    df["x_0"] = signed_power(df["RETURNS"].rolling(20).std(ddof=0).where(df["RETURNS"] < 0, df["CLOSE"]), 2.0).rolling(5).apply(np.argmax, engine="numba", raw=True)
    # x_12 = ts_delta(CLOSE, 1)
    df["x_12"] = df["CLOSE"].diff(1)
    # x_29 = ts_rank(CLOSE, 10)
    df["x_29"] = df["CLOSE"].rolling(10).rank(pct=True)
    # x_38 = ts_delta(CLOSE, 7)
    df["x_38"] = df["CLOSE"].diff(7)
    # x_1 = ts_delta(log(VOLUME), 2)
    df["x_1"] = np.log(df["VOLUME"]).diff(2)
    # x_19 = ts_delta(VOLUME, 3)
    df["x_19"] = df["VOLUME"].diff(3)
    # x_9 = ts_sum(OPEN, 5)
    df["x_9"] = df["OPEN"].rolling(5).sum()
    # x_34 = OPEN - ts_delay(CLOSE, 1)
    df["x_34"] = df["OPEN"] - df["CLOSE"].shift(1)
    # x_37 = ts_corr(OPEN, VOLUME, 10)
    df["x_37"] = df["OPEN"].rolling(10).corr(df["VOLUME"], ddof=0)
    # x_36 = OPEN - ts_delay(LOW, 1)
    df["x_36"] = df["OPEN"] - df["LOW"].shift(1)
    # x_8 = OPEN - ts_sum(VWAP, 10)/10
    df["x_8"] = df["OPEN"] - df["VWAP"].rolling(10).sum() / 10
    # x_35 = OPEN - ts_delay(HIGH, 1)
    df["x_35"] = df["OPEN"] - df["HIGH"].shift(1)
    # x_30 = ts_rank(VOLUME/ADV20, 5)
    df["x_30"] = (df["VOLUME"] / df["ADV20"]).rolling(5).rank(pct=True)
    return df


def func_0_cs__date(df: pd.DataFrame) -> pd.DataFrame:
    # ========================================
    # x_20 = cs_rank(CLOSE)
    df["x_20"] = df["CLOSE"].rank(pct=True)
    # x_6 = cs_rank(VOLUME)
    df["x_6"] = df["VOLUME"].rank(pct=True)
    # x_5 = cs_rank(OPEN)
    df["x_5"] = df["OPEN"].rank(pct=True)
    # x_7 = cs_rank(LOW)
    df["x_7"] = df["LOW"].rank(pct=True)
    # x_24 = cs_rank(HIGH)
    df["x_24"] = df["HIGH"].rank(pct=True)
    # ========================================
    # x_3 = CLOSE - OPEN
    df["x_3"] = df["CLOSE"] - df["OPEN"]
    # x_15 = CLOSE - VWAP
    df["x_15"] = df["CLOSE"] - df["VWAP"]
    # ========================================
    # x_23 = cs_rank(x_22)
    df["x_23"] = df["x_22"].rank(pct=True)
    # x_33 = cs_rank(x_32) + 1
    df["x_33"] = df["x_32"].rank(pct=True) + 1
    # alpha_001 = cs_rank(x_0) - 0.5
    df["alpha_001"] = df["x_0"].rank(pct=True) - 0.5
    # x_2 = cs_rank(x_1)
    df["x_2"] = df["x_1"].rank(pct=True)
    # x_4 = cs_rank(x_3/OPEN)
    df["x_4"] = (df["x_3"] / df["OPEN"]).rank(pct=True)
    # alpha_005 = -abs(cs_rank(x_15))*cs_rank(x_8)
    df["alpha_005"] = -df["x_15"].rank(pct=True).abs() * df["x_8"].rank(pct=True)
    # alpha_020 = -cs_rank(x_34)*cs_rank(x_35)*cs_rank(x_36)
    df["alpha_020"] = -df["x_34"].rank(pct=True) * df["x_35"].rank(pct=True) * df["x_36"].rank(pct=True)
    # ========================================
    # x_13 = -x_12
    df["x_13"] = -df["x_12"]
    # alpha_006 = -x_37
    df["alpha_006"] = -df["x_37"]
    # x_16 = -x_15
    df["x_16"] = -df["x_15"]
    return df


def func_1_ts__asset__date(df: pd.DataFrame) -> pd.DataFrame:
    # ========================================
    # x_28 = ts_delta(x_12, 1)
    df["x_28"] = df["x_12"].diff(1)
    # alpha_012 = -x_12*sign(ts_delta(VOLUME, 1))
    df["alpha_012"] = -df["x_12"] * df["VOLUME"].diff(1).sign()
    # alpha_007 = if_else(ADV20 < VOLUME, -sign(x_38)*ts_rank(abs(x_38), 60), -1)
    df["alpha_007"] = (-df["x_38"].sign() * df["x_38"].abs().rolling(60).rank(pct=True)).where(df["ADV20"] < df["VOLUME"], -1)
    # x_21 = ts_covariance(x_20, x_6, 5)
    df["x_21"] = df["x_20"].rolling(5).cov(df["x_6"], ddof=0)
    # x_31 = x_3 + ts_corr(CLOSE, OPEN, 10) + ts_std_dev(abs(x_3), 5)
    df["x_31"] = df["x_3"] + df["CLOSE"].rolling(10).corr(df["OPEN"], ddof=0) + df["x_3"].abs().rolling(5).std(ddof=0)
    # alpha_003 = -ts_corr(x_5, x_6, 10)
    df["alpha_003"] = -df["x_5"].rolling(10).corr(df["x_6"], ddof=0)
    # x_11 = x_10*x_9 - ts_delay(x_10*x_9, 10)
    df["x_11"] = df["x_10"] * df["x_9"] - (df["x_10"] * df["x_9"]).shift(10)
    # alpha_004 = -ts_rank(x_7, 9)
    df["alpha_004"] = -df["x_7"].rolling(9).rank(pct=True)
    # x_25 = ts_corr(x_24, x_6, 3)
    df["x_25"] = df["x_24"].rolling(3).corr(df["x_6"], ddof=0)
    # x_27 = ts_covariance(x_24, x_6, 5)
    df["x_27"] = df["x_24"].rolling(5).cov(df["x_6"], ddof=0)
    # ========================================
    # alpha_014 = -x_23*x_37
    df["alpha_014"] = -df["x_23"] * df["x_37"]
    # ========================================
    # alpha_019 = -x_33*sign(CLOSE + x_38 - ts_delay(CLOSE, 7))
    df["alpha_019"] = -df["x_33"] * (df["CLOSE"] + df["x_38"] - df["CLOSE"].shift(7)).sign()
    # x_14 = if_else(ts_min(x_12, 4) > 0, x_12, if_else(ts_max(x_12, 4) < 0, x_12, x_13))
    df["x_14"] = df["x_12"].where(df["x_12"].rolling(4).min() > 0, df["x_12"].where(df["x_12"].rolling(4).max() < 0, df["x_13"]))
    # alpha_009 = if_else(ts_min(x_12, 5) > 0, x_12, if_else(ts_max(x_12, 5) < 0, x_12, x_13))
    df["alpha_009"] = df["x_12"].where(df["x_12"].rolling(5).min() > 0, df["x_12"].where(df["x_12"].rolling(5).max() < 0, df["x_13"]))
    # alpha_002 = -ts_corr(x_2, x_4, 6)
    df["alpha_002"] = -df["x_2"].rolling(6).corr(df["x_4"], ddof=0)
    # x_17 = ts_max(x_16, 3)
    df["x_17"] = df["x_16"].rolling(3).max()
    # x_18 = ts_min(x_16, 3)
    df["x_18"] = df["x_16"].rolling(3).min()
    return df


def func_2_cs__date(df: pd.DataFrame) -> pd.DataFrame:
    # ========================================
    # alpha_017 = -cs_rank(x_28)*cs_rank(x_29)*cs_rank(x_30)
    df["alpha_017"] = -df["x_28"].rank(pct=True) * df["x_29"].rank(pct=True) * df["x_30"].rank(pct=True)
    # alpha_013 = -cs_rank(x_21)
    df["alpha_013"] = -df["x_21"].rank(pct=True)
    # alpha_018 = -cs_rank(x_31)
    df["alpha_018"] = -df["x_31"].rank(pct=True)
    # alpha_008 = -cs_rank(x_11)
    df["alpha_008"] = -df["x_11"].rank(pct=True)
    # x_26 = cs_rank(x_25)
    df["x_26"] = df["x_25"].rank(pct=True)
    # alpha_016 = -cs_rank(x_27)
    df["alpha_016"] = -df["x_27"].rank(pct=True)
    # ========================================
    # alpha_010 = cs_rank(x_14)
    df["alpha_010"] = df["x_14"].rank(pct=True)
    # alpha_011 = (cs_rank(x_17) + cs_rank(x_18))*cs_rank(x_19)
    df["alpha_011"] = (df["x_17"].rank(pct=True) + df["x_18"].rank(pct=True)) * df["x_19"].rank(pct=True)
    return df


def func_3_ts__asset__date(df: pd.DataFrame) -> pd.DataFrame:
    # ========================================
    # alpha_015 = -ts_sum(x_26, 3)
    df["alpha_015"] = -df["x_26"].rolling(3).sum()
    return df


logger.info("start...")


df = df.sort_values(by=["asset", "date"]).groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date)
df = df.groupby(by=["date"], group_keys=False).apply(func_0_cs__date)
df = df.sort_values(by=["asset", "date"]).groupby(by=["asset"], group_keys=False).apply(func_1_ts__asset__date)
df = df.groupby(by=["date"], group_keys=False).apply(func_2_cs__date)
df = df.sort_values(by=["asset", "date"]).groupby(by=["asset"], group_keys=False).apply(func_3_ts__asset__date)


# #========================================func_0_ts__asset__date
# x_10 = ts_sum(RETURNS, 5)
# x_22 = ts_delta(RETURNS, 3)
# x_32 = ts_sum(RETURNS, 250) + 1
# x_0 = ts_arg_max(signed_power(if_else(RETURNS < 0, ts_std_dev(RETURNS, 20), CLOSE), 2.0), 5)
# x_12 = ts_delta(CLOSE, 1)
# x_29 = ts_rank(CLOSE, 10)
# x_38 = ts_delta(CLOSE, 7)
# x_1 = ts_delta(log(VOLUME), 2)
# x_19 = ts_delta(VOLUME, 3)
# x_9 = ts_sum(OPEN, 5)
# x_34 = OPEN - ts_delay(CLOSE, 1)
# x_37 = ts_corr(OPEN, VOLUME, 10)
# x_36 = OPEN - ts_delay(LOW, 1)
# x_8 = OPEN - ts_sum(VWAP, 10)/10
# x_35 = OPEN - ts_delay(HIGH, 1)
# x_30 = ts_rank(VOLUME/ADV20, 5)
# #========================================func_0_cs__date
# x_20 = cs_rank(CLOSE)
# x_6 = cs_rank(VOLUME)
# x_5 = cs_rank(OPEN)
# x_7 = cs_rank(LOW)
# x_24 = cs_rank(HIGH)
# #========================================func_0_cs__date
# x_3 = CLOSE - OPEN
# x_15 = CLOSE - VWAP
# #========================================func_0_cs__date
# x_23 = cs_rank(x_22)
# x_33 = cs_rank(x_32) + 1
# alpha_001 = cs_rank(x_0) - 0.5
# x_2 = cs_rank(x_1)
# x_4 = cs_rank(x_3/OPEN)
# alpha_005 = -abs(cs_rank(x_15))*cs_rank(x_8)
# alpha_020 = -cs_rank(x_34)*cs_rank(x_35)*cs_rank(x_36)
# #========================================func_0_cs__date
# x_13 = -x_12
# alpha_006 = -x_37
# x_16 = -x_15
# #========================================func_1_ts__asset__date
# x_28 = ts_delta(x_12, 1)
# alpha_012 = -x_12*sign(ts_delta(VOLUME, 1))
# alpha_007 = if_else(ADV20 < VOLUME, -sign(x_38)*ts_rank(abs(x_38), 60), -1)
# x_21 = ts_covariance(x_20, x_6, 5)
# x_31 = x_3 + ts_corr(CLOSE, OPEN, 10) + ts_std_dev(abs(x_3), 5)
# alpha_003 = -ts_corr(x_5, x_6, 10)
# x_11 = x_10*x_9 - ts_delay(x_10*x_9, 10)
# alpha_004 = -ts_rank(x_7, 9)
# x_25 = ts_corr(x_24, x_6, 3)
# x_27 = ts_covariance(x_24, x_6, 5)
# #========================================func_1_ts__asset__date
# alpha_014 = -x_23*x_37
# #========================================func_1_ts__asset__date
# alpha_019 = -x_33*sign(CLOSE + x_38 - ts_delay(CLOSE, 7))
# x_14 = if_else(ts_min(x_12, 4) > 0, x_12, if_else(ts_max(x_12, 4) < 0, x_12, x_13))
# alpha_009 = if_else(ts_min(x_12, 5) > 0, x_12, if_else(ts_max(x_12, 5) < 0, x_12, x_13))
# alpha_002 = -ts_corr(x_2, x_4, 6)
# x_17 = ts_max(x_16, 3)
# x_18 = ts_min(x_16, 3)
# #========================================func_2_cs__date
# alpha_017 = -cs_rank(x_28)*cs_rank(x_29)*cs_rank(x_30)
# alpha_013 = -cs_rank(x_21)
# alpha_018 = -cs_rank(x_31)
# alpha_008 = -cs_rank(x_11)
# x_26 = cs_rank(x_25)
# alpha_016 = -cs_rank(x_27)
# #========================================func_2_cs__date
# alpha_010 = cs_rank(x_14)
# alpha_011 = (cs_rank(x_17) + cs_rank(x_18))*cs_rank(x_19)
# #========================================func_3_ts__asset__date
# alpha_015 = -ts_sum(x_26, 3)

# alpha_001 = -0.5 + cs_rank(ts_arg_max(signed_power(if_else(RETURNS < 0, ts_std_dev(RETURNS, 20), CLOSE), 2.0), 5))
# alpha_002 = -ts_corr(cs_rank(ts_delta(log(VOLUME), 2)), cs_rank((CLOSE - OPEN)/OPEN), 6)
# alpha_003 = -ts_corr(cs_rank(OPEN), cs_rank(VOLUME), 10)
# alpha_004 = -ts_rank(cs_rank(LOW), 9)
# alpha_005 = -abs(cs_rank(CLOSE - VWAP))*cs_rank(OPEN - ts_sum(VWAP, 10)/10)
# alpha_006 = -ts_corr(OPEN, VOLUME, 10)
# alpha_007 = if_else(ADV20 < VOLUME, -sign(ts_delta(CLOSE, 7))*ts_rank(abs(ts_delta(CLOSE, 7)), 60), -1)
# alpha_008 = -cs_rank(-ts_delay(ts_sum(OPEN, 5)*ts_sum(RETURNS, 5), 10) + ts_sum(OPEN, 5)*ts_sum(RETURNS, 5))
# alpha_009 = if_else(ts_min(ts_delta(CLOSE, 1), 5) > 0, ts_delta(CLOSE, 1), if_else(ts_max(ts_delta(CLOSE, 1), 5) < 0, ts_delta(CLOSE, 1), -ts_delta(CLOSE, 1)))
# alpha_010 = cs_rank(if_else(ts_min(ts_delta(CLOSE, 1), 4) > 0, ts_delta(CLOSE, 1), if_else(ts_max(ts_delta(CLOSE, 1), 4) < 0, ts_delta(CLOSE, 1), -ts_delta(CLOSE, 1))))
# alpha_011 = (cs_rank(ts_max(-CLOSE + VWAP, 3)) + cs_rank(ts_min(-CLOSE + VWAP, 3)))*cs_rank(ts_delta(VOLUME, 3))
# alpha_012 = -sign(ts_delta(VOLUME, 1))*ts_delta(CLOSE, 1)
# alpha_013 = -cs_rank(ts_covariance(cs_rank(CLOSE), cs_rank(VOLUME), 5))
# alpha_014 = -cs_rank(ts_delta(RETURNS, 3))*ts_corr(OPEN, VOLUME, 10)
# alpha_015 = -ts_sum(cs_rank(ts_corr(cs_rank(HIGH), cs_rank(VOLUME), 3)), 3)
# alpha_016 = -cs_rank(ts_covariance(cs_rank(HIGH), cs_rank(VOLUME), 5))
# alpha_017 = -cs_rank(ts_delta(ts_delta(CLOSE, 1), 1))*cs_rank(ts_rank(CLOSE, 10))*cs_rank(ts_rank(VOLUME/ADV20, 5))
# alpha_018 = -cs_rank(CLOSE - OPEN + ts_corr(CLOSE, OPEN, 10) + ts_std_dev(abs(CLOSE - OPEN), 5))
# alpha_019 = -(cs_rank(ts_sum(RETURNS, 250) + 1) + 1)*sign(CLOSE - ts_delay(CLOSE, 7) + ts_delta(CLOSE, 7))
# alpha_020 = -cs_rank(OPEN - ts_delay(CLOSE, 1))*cs_rank(OPEN - ts_delay(HIGH, 1))*cs_rank(OPEN - ts_delay(LOW, 1))

# drop intermediate columns
df = df.drop(columns=filter(lambda x: re.search(r"^x_\d+", x), df.columns))


logger.info("done")

# save
# df.to_parquet('output.parquet', compression='zstd')

print(df.tail(5))
