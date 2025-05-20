import numpy as np
import pandas as pd
import polars as pl
from loguru import logger

from expr_codegen import codegen_exec

_N = 250 * 10
_K = 500

asset = [f's_{i:04d}' for i in range(_K)]
date = pd.date_range('2015-1-1', periods=_N)

df = pd.DataFrame({
    'RETURNS': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'VWAP': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'LOW': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'CLOSE': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
}, index=pd.MultiIndex.from_product([date, asset], names=['date', 'asset'])).reset_index()

# 向脚本输入数据
# df = pl.from_pandas(df)


def _code_block_1():
    # 要求能将ts_提前
    B = cs_rank(CLOSE, False)
    C = cs_rank(CLOSE, True)
    A = ts_returns(CLOSE, 5)
    D = ts_returns(CLOSE, 10)
    E = A + B


def _code_block_2():
    # 要求能将ts_提前
    ma_10 = ts_mean(CLOSE, 10)
    MAMA_20 = ts_mean(ma_10, 20)
    alpha_031 = ((cs_rank(cs_rank(cs_rank(ts_decay_linear((-1 * cs_rank(cs_rank(ts_delta(CLOSE, 10)))), 10))))))


def _code_block_1():
    # 要求能将ts_提前
    A = ts_returns(CLOSE, 5)
    D = ts_returns(A, 10) + cs_rank(CLOSE)
    E = A + D


def _code_block_1():
    # 要求能将ts_提前
    B = cs_rank(CLOSE, False)
    C = cs_rank(CLOSE, True)
    E = B + C


logger.info("1")
df = codegen_exec(df, _code_block_1, over_null='partition_by', output_file="1_out.py", style='pandas', filter_last=True)
print(df)
logger.info("2")
