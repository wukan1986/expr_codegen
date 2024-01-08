# %%
import os
import sys
from pathlib import Path

# 修改当前目录到上层目录，方便跨不同IDE中使用
pwd = str(Path(__file__).parents[1])
os.chdir(pwd)
sys.path.append(pwd)

import polars as pl
from loguru import logger  # noqa

# %%
df_input = pl.read_parquet('data/data.parquet')
# print(df.tail())

from codes.demo_exec import main

df = main(df_input)
print(df.tail())

# %%
columns = ['CLOSE', '移动平均_10', '移动平均_20', 'MAMA_20']
df1 = df.filter(pl.col('asset') == 's_100').select('date', 'asset', *columns)
df2 = df.filter(pl.col('asset') == 's_200').select('date', 'asset', *columns)
# %%
# 此绘图需要安装hvplot
# 需要在notebook环境中使用
plot1 = df1.plot(x='date', y=columns, label='s_100')
plot2 = df2.plot(x='date', y=columns, label='s_200')

# hvplot叠加特方便，但缺点是不够灵活
(plot1 + plot2).cols(1)
# %%
