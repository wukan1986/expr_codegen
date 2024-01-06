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
# ===============
if False:
    # 可以直接读源代码执行
    with open('log/codes_9999.py', 'r', encoding='utf-8') as f:
        codes = f.read()
        # !!! globals()使用要小心防止变量被修改，特别是要执行两次的情况
        exec(codes, globals())

    print(df_output.tail())

# ===============
if True:
    # 也可以下断点
    from log.codes_9999 import main

    df_output = main(df_input)
    print(df_output.tail())
# ===============
if False:
    # 也可以下断点
    m = __import__('log.codes_9999', fromlist=['*'])

    df_output = m.main(df_input)
    print(df_output.tail())
