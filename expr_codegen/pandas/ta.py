"""
原本代码都写在printer.py中，但存在一些不足
1. 每新添函数都要修改printer.py，工作量大，不够灵活
2. 生成的代码过于直接，不便研究分析
3. 纯字符串拼接，没有IDE语法检查，非常容易出错
4. 部分写法对模板侵入性高，import混乱

所以有必要使用类似于polars_ta的公共库，但因目前未找到合适库，所以以下是临时版，以后要独立出去
"""
from typing import Tuple

import numpy as np
import pandas as pd

try:
    import talib
except:
    pass


def abs_(x: pd.Series) -> pd.Series:
    return np.abs(x)


def cs_demean(x: pd.Series) -> pd.Series:
    return x - x.mean()


def cs_rank(x: pd.Series, pct: bool = True) -> pd.Series:
    return x.rank(pct=pct)


def cs_scale(x: pd.Series, scale: float = 1) -> pd.Series:
    return x / x.abs().sum() * scale


def if_else(input1: pd.Series, input2: pd.Series, input3: pd.Series = None):
    return np.where(input1, input2, input3)


def log(x: pd.Series) -> pd.Series:
    return np.log(x)


def max_(a: pd.Series, b: pd.Series) -> pd.Series:
    return np.maximum(a, b)


def min_(a: pd.Series, b: pd.Series) -> pd.Series:
    return np.minimum(a, b)


def sign(x: pd.Series) -> pd.Series:
    return np.sign(x)


def signed_power(x: pd.Series, y: float) -> pd.Series:
    return x.sign() * (x.abs() ** y)


def ts_corr(x: pd.Series, y: pd.Series, d: int = 5, ddof: int = 1) -> pd.Series:
    return x.rolling(d).corr(y, ddof=ddof)


def ts_covariance(x: pd.Series, y: pd.Series, d: int = 5, ddof: int = 1) -> pd.Series:
    return x.rolling(d).cov(y, ddof=ddof)


def ts_delay(x: pd.Series, d: int = 1) -> pd.Series:
    return x.shift(d)


def ts_delta(x: pd.Series, d: int = 1) -> pd.Series:
    return x.diff(d)


def ts_max(x: pd.Series, d: int = 5) -> pd.Series:
    return x.rolling(d).max()


def ts_mean(x: pd.Series, d: int = 5) -> pd.Series:
    return x.rolling(d).mean()


def ts_min(x: pd.Series, d: int = 5) -> pd.Series:
    return x.rolling(d).min()


def ts_product(x: pd.Series, d: int = 5) -> pd.Series:
    return x.rolling(d).apply(np.prod, raw=True)


def ts_rank(x: pd.Series, d: int = 5, pct: bool = True) -> pd.Series:
    return x.rolling(d).rank(pct=pct)


def ts_std_dev(x: pd.Series, d: int = 5, ddof: int = 0) -> pd.Series:
    return x.rolling(d).std(ddof=ddof)


def ts_sum(x: pd.Series, d: int = 5) -> pd.Series:
    return x.rolling(d).sum()


def ts_MACD(close: pd.Series, fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    return talib.MACD(close, fastperiod, slowperiod, signalperiod)
