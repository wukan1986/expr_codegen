import numpy as np
import pandas as pd
import polars as pl
from polars_ta.prefix.wq import *

from expr_codegen import codegen_exec

_N = 250 * 1
_K = 500  # TODO 如要单资产，改此处为1即可

asset = [f's_{i:04d}' for i in range(_K)]
date = pd.date_range('2015-1-1', periods=_N)

df = pd.DataFrame({
    # 原始价格
    'CLOSE': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    'OPEN': np.cumprod(1 + np.random.uniform(-0.1, 0.1, size=(_N, _K)), axis=0).reshape(-1),
    # TODO 这只是为了制造长度不同的数据而设计
    "FILTER": np.tri(_N, _K, k=100).reshape(-1),
}, index=pd.MultiIndex.from_product([date, asset], names=['date', 'asset'])).reset_index()

# 向脚本输入数据
df = pl.from_pandas(df)


def _code_block_1():
    # 因子编辑区，可利用IDE的智能提示在此区域编辑因子
    A1 = floor(log1p(ceiling(abs_(CLOSE * 100) * 2)))


df = codegen_exec(df, _code_block_1, over_null='partition_by', output_file='1_out.sql', style='sql',
                  table_name='df')  # 打印代码

print(df.collect())

code = codegen_exec(None, _code_block_1, over_null='partition_by', output_file='1_out.sql', style='sql',
                    date='date1', asset='asset2',
                    table_name='df')  # 打印代码

print(code)
