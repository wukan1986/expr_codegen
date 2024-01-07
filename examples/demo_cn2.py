"""
如果你不习惯在streamlit生成的编辑器中编写公式，也可以在IDE中使用，带智能提示

编辑完后再将公式复制到 https://exprcodegen.streamlit.app/ 或 以下的指定区域生成即可
"""
import os
import sys
from pathlib import Path

# 修改当前目录到上层目录，方便跨不同IDE中使用
pwd = str(Path(__file__).parents[1])
os.chdir(pwd)
sys.path.append(pwd)
# ===============
import inspect

from examples.sympy_define import *  # noqa
from expr_codegen.expr import string_to_exprs
from expr_codegen.tool import ExprTool

_ = 0  # 只要之前出现了语句，之后的import位置不参与调整
from polars_ta.prefix.talib import *  # noqa
from polars_ta.prefix.tdx import *  # noqa
from polars_ta.prefix.ta import *  # noqa
from polars_ta.prefix.wq import *  # noqa
from polars_ta.prefix.cdl import *  # noqa

# TODO: 因子。请根据需要补充
sw_l1, = symbols('sw_l1, ', cls=Symbol)


def cs_label(cond, x):
    """表达式太长，可自己封装一下。生成源代码后，需要将此部分复制过去

    注意：名字需要考虑是否设置前缀`ts_`、`cs_`
    内部代码必须与前缀统一，否则生成的代码混乱。
    如cs_label与内部的cs_bucket、cs_winsorize_quantile是统一的
    """
    return if_else(cond, None, cs_bucket(cs_winsorize_quantile(x, 0.01, 0.99), 20))


def _expr_code():
    # 因子编辑区，可利用IDE的智能提示在此区域编辑因子
    _NEXT_DAY = ts_delay(four_price_doji(OPEN, HIGH, LOW, CLOSE), -1)
    LABEL_005 = cs_label(_NEXT_DAY, ts_delay(CLOSE, -5) / ts_delay(OPEN, -1))
    LABEL_010 = cs_label(_NEXT_DAY, ts_delay(CLOSE, -10) / ts_delay(OPEN, -1))


# 读取源代码，转成字符串
source = inspect.getsource(_expr_code)
print(source)

# 将字符串转成表达式，与streamlit中效果一样
exprs_src = string_to_exprs(source, globals().copy())

# 生成代码
tool = ExprTool()
codes, G = tool.all(exprs_src, style='polars', template_file='template.py.j2',
                    replace=True, regroup=True, format=True,
                    date='date', asset='asset')

print(codes)
#
# 保存代码到指定文件
output_file = 'examples/output_polars.py'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(codes)
