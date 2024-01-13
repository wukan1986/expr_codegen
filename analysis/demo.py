# %%
import os
import sys
from pathlib import Path

# 修改当前目录到上层目录，方便跨不同IDE中使用
pwd = str(Path(__file__).parents[1])
os.chdir(pwd)
sys.path.append(pwd)
# ===============
# %%
# 从main中导入，可以大大减少代码
import matplotlib.pyplot as plt

from gp.main import *
from analysis.information_coefficient import create_ic_sheet
from analysis.portfolio import create_portfolio_sheet
from analysis.returns import create_returns_sheet

# TODO 可替换成任意一代的种群文件
with open(LOG_DIR / f'hall_of_fame.pkl', 'rb') as f:
    pop = pickle.load(f)

df_input = pl.read_parquet('data/data.parquet')

# %%
from log.codes_9999 import main

df_output = main(df_input)
# %%
x = 'GP_0000'
yy = ['RETURN_OO_1', 'RETURN_OO_2', 'RETURN_CC_1']
# %%
create_ic_sheet(df_output, x, yy, by='date')
# %%
create_returns_sheet(df_output, x, yy, by='date')

y = 'RETURN_OO_1'
create_portfolio_sheet(df_output, x, y, period=10, by='date', asset='asset')

plt.show()

# %%
