"""
与`demo_exec_pl.py`代码基本相同，不过将生成代码换成了`pandas`

支持`cudf.pandas`，推荐使用方法如下

`python -m cudf.pandas demo_exec_pd.py`

注意：GPU计算只有在大数据量下才有意义。因为在显存与内存之间复制数据也需要耗费不少时间
"""
import os
import sys
from pathlib import Path

# 修改当前目录到上层目录，方便跨不同IDE中使用
pwd = str(Path(__file__).parents[1])
os.chdir(pwd)
sys.path.append(pwd)

# 在Linux平台下，两种方法任选一种即可
# # python -m cudf.pandas demo_exec_pd.py
#
# if os.name != 'nt':
#     try:
#         import cudf.pandas
#
#         cudf.pandas.install()
#     except:
#         pass

import pandas as pd
from matplotlib import pyplot as plt

from examples.sympy_define import *
from expr_codegen.expr import string_to_exprs
from expr_codegen.tool import ExprTool

# 防止sympy_define导入被IDE删除
_ = Eq

# ======================================
# 数据准备，请先运行`data`目录下的`prepare_data.py`
df_input = pd.read_parquet('data/data.parquet')
df_output = None


def main():
    # 表达式设置
    exprs_src = """
    MA_10=ts_mean(CLOSE, 10)
    MA_40=ts_mean(ts_mean(CLOSE, 5), 40)
    MA_60=ts_mean(MA_10, 40)
    """
    exprs_src = string_to_exprs(exprs_src, globals())

    # 生成代码
    tool = ExprTool()
    codes, G = tool.all(exprs_src, style='pandas', template_file='template.py.j2',
                        regroup=True,
                        date='date', asset='asset')

    # 打印代码
    print(codes)

    # 执行代码
    exec(codes, globals())

    # 写在def中时，exec中的df就取不到了，达到了保护数据的目的
    # UnboundLocalError: cannot access local variable 'df' where it is not associated with a value
    # print(df.columns)
    print(df_input.columns)
    print(df_output.columns)

    df = df_output
    df = df.set_index(['asset', 'date'])

    for s in ['s_100', 's_200']:
        stock = df.loc[s]
        stock[['CLOSE', 'MA_10', 'MA_40']].plot()
    plt.show()


if __name__ == "__main__":
    main()
