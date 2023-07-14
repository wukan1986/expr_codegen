import numpy as np
import pandas as pd
import polars as pl
from matplotlib import pyplot as plt

from examples.sympy_define import *
from expr_codegen.expr import string_to_exprs
from expr_codegen.tool import ExprTool

# 防止sympy_define导入被IDE删除
_ = gp_neutralize

# ======================================
# 数据准备
_N = 250 * 10
_K = 500

asset = [f's_{i}' for i in range(_K)]
date = pd.date_range('2000-01-1', periods=_N)

df = pd.DataFrame({
    'OPEN': np.cumprod(1 + (np.random.rand(_K * _N) - 0.5).reshape(_N, -1) / 100, axis=0).reshape(-1),
    'HIGH': np.cumprod(1 + (np.random.rand(_K * _N) - 0.5).reshape(_N, -1) / 100, axis=0).reshape(-1),
    'LOW': np.cumprod(1 + (np.random.rand(_K * _N) - 0.5).reshape(_N, -1) / 100, axis=0).reshape(-1),
    'CLOSE': np.cumprod(1 + (np.random.rand(_K * _N) - 0.5).reshape(_N, -1) / 100, axis=0).reshape(-1),
}, index=pd.MultiIndex.from_product([date, asset], names=['date', 'asset'])).reset_index()

df = pl.from_pandas(df)

# 表达式设置，可用字符串，也可以用字典
exprs_src = """
MA_10=ts_mean(CLOSE, 10)
MA_40=ts_mean(ts_mean(CLOSE, 5), 40)
"""
exprs_src = string_to_exprs(exprs_src, globals())

# 生成代码
tool = ExprTool(date='date', asset='asset')
codes, G = tool.all(exprs_src, style='polars', template_file='template.py.j2', fast=True)

# 打印代码
print(codes)

# 执行代码
exec(codes)

df = df.to_pandas()
df = df.set_index(['asset', 'date'])

for s in ['s_100', 's_200']:
    stock = df.loc[s]
    stock[['CLOSE', 'MA_10', 'MA_40']].plot()
plt.show()
