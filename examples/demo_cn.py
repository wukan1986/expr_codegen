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

from examples.sympy_define import *  # noqa
from expr_codegen.expr import string_to_exprs
from expr_codegen.tool import ExprTool

# TODO: 因子。请根据需要补充
sw_l1, = symbols('sw_l1, ', cls=Symbol)

# ==========================================
# 因子编辑区，可利用IDE的智能提示在此区域编辑因子，之后复制到下面指定区
RETURN_OPEN_001 = ts_returns(OPEN, 1)
RETURN_OPEN_003 = ts_returns(OPEN, 3)
RETURN_OPEN_005 = ts_returns(OPEN, 5)
RETURN_OPEN_010 = ts_returns(OPEN, 10)
RETURN_OPEN_020 = ts_returns(OPEN, 20)

RETURN_SHIFT_001 = ts_delay(RETURN_OPEN_001, -1-1)
RETURN_SHIFT_003 = ts_delay(RETURN_OPEN_003, -3-1)
RETURN_SHIFT_005 = ts_delay(RETURN_OPEN_005, -5-1)
RETURN_SHIFT_010 = ts_delay(RETURN_OPEN_010, -10-1)
RETURN_SHIFT_020 = ts_delay(RETURN_OPEN_020, -20-1)

LABEL_001 = cs_rank(RETURN_SHIFT_001)
LABEL_003 = cs_rank(RETURN_SHIFT_003)
LABEL_005 = cs_rank(RETURN_SHIFT_005)
LABEL_010 = cs_rank(RETURN_SHIFT_010)
LABEL_020 = cs_rank(RETURN_SHIFT_020)

隔夜收益率 = OPEN / ts_delay(CLOSE, 1)  # 支持中文

移动平均_10 = ts_mean(CLOSE, 10)
移动平均_20 = ts_mean(CLOSE, 20)
MAMA_20 = ts_mean(移动平均_10, 20)

# ==========================================
# 将前面编辑的好的代码复制到三引号字符串区即可
exprs_src = """
移动平均_10 = ts_mean(CLOSE, 10)
移动平均_20 = ts_mean(CLOSE, 20)
MAMA_20 = ts_mean(移动平均_10, 20)
"""
# 将字符串转成表达式，与streamlit中效果一样
exprs_src = string_to_exprs(exprs_src, globals())

# 生成代码
tool = ExprTool()
codes, G = tool.all(exprs_src, style='polars', template_file='template.py.j2',
                    replace=True, regroup=True, format=True,
                    date='date', asset='asset')

print(codes)

# 保存代码到指定文件
output_file = 'examples/output_polars.py'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(codes)
