import os
import sys

from pathlib import Path

# 修改当前目录到上层目录，方便跨不同IDE中使用
pwd = str(Path(__file__).parents[1])
os.chdir(pwd)
sys.path.append(pwd)
# ===============
# 从main中导入，可以大大减少代码
from main import *

# TODO 可替换成任意一代的种群文件
with open(LOG_DIR / f'hall_of_fame.pkl', 'rb') as f:
    pop = pickle.load(f)

# 打印原始名人堂中表达式
print_population(pop)

df_input = pl.read_parquet('data/data.parquet')
df_train = df_input.filter(pl.col('date') < datetime(2021, 1, 1))
df_vaild = df_input.filter(pl.col('date') >= datetime(2021, 1, 1))
del df_input  # 释放内存
# 重新计算并回填
fitnesses = map_exprs(print, pop, gen=count(9999), label=LABEL_y, input_train=None, input_vaild=df_vaild)
for ind, fit in zip(pop, fitnesses):
    ind.fitness.values = fit

# 打印新的fitness结果
print_population(pop)
