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
# TODO 样本外数据
df_input = df_input.filter(pl.col('date') >= datetime(2021, 1, 1))

# 重新计算并回填
fitnesses = map_exprs(evaluate_expr, pop, gen=count(9999), date_input=df_input)
for ind, fit in zip(pop, fitnesses):
    ind.fitness.values = fit

# 打印新的fitness结果
print_population(pop)
