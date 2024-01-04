"""
本脚本用于调试生成的代码是否可以运行
"""
import os
import sys
from pathlib import Path

# 修改当前目录到上层目录，方便跨不同IDE中使用
pwd = str(Path(__file__).parents[1])
os.chdir(pwd)
sys.path.append(pwd)
# ===============
import polars as pl

# 导入数据部分
df_input = pl.read_parquet('data/data.parquet')
df_output = None
# ===============
# 可以直接读源代码执行
with open('log/codes_0000.py', 'r', encoding='utf-8') as f:
    codes = f.read()
    # !!! globals()使用要小心防止变量被修改，特别是要执行两次的情况
    exec(codes, globals())

print(df_output.tail())

# ===============
# 如果要对代码下断点，还是得从codes_0000.py等文件直接复制过来
