import base64
import inspect

import streamlit as st
from black import format_str, Mode
from loguru import logger
from more_itertools import batched
from streamlit_ace import st_ace
from sympy import numbered_symbols, Symbol, FunctionClass

import expr_codegen
from expr_codegen.codes import sources_to_exprs
from expr_codegen.expr import replace_exprs
from expr_codegen.tool import ExprTool


def get_symbols_functions(module):
    """获取Symbol与Function"""
    symbols = [n for n, _ in inspect.getmembers(module, lambda x: isinstance(x, Symbol))]
    functions = [n for n, _ in inspect.getmembers(module, lambda x: isinstance(x, FunctionClass) or inspect.isfunction(x))]
    # 去一个特殊值
    functions = [_ for _ in functions if _ != 'Function']
    return symbols, functions


def list_to_string(items, n):
    txts = []
    for ss in batched(items, n):
        txts.append(f'# {",".join(ss)}')
    return '\n'.join(txts)


st.set_page_config(page_title='Expr Codegen', layout="wide")

with st.sidebar:
    st.subheader("配置参数")

    date_name = st.text_input('日期字段名', 'date')
    asset_name = st.text_input('资产字段名', 'asset')

    # 生成代码
    style = st.radio('代码风格', ('polars_over', 'polars_group', 'pandas/cudf.pandas'))
    if style == 'polars_group':
        from expr_codegen.polars_group.code import codegen
    elif style == 'polars_over':
        from expr_codegen.polars_over.code import codegen
    else:
        from expr_codegen.pandas.code import codegen

    convert_xor = st.checkbox('将`^`转换为`**`', True)

    st.subheader("优化")
    is_pre_opt = st.checkbox('事前`表达式`替换', True)
    is_chain_opt = st.checkbox('事后`首尾接龙`向前合并', True)

    st.subheader("关于")
    st.markdown(f"""[Github仓库](https://github.com/wukan1986/expr_codegen)

[问题反馈](http://github.com/wukan1986/expr_codegen/issues)

作者: wukan

声明：
1. 本站点不存储用户输入的表达式，安全保密可放心
2. 生成的代码可能有错，发现后请及时反馈

version: {expr_codegen.__version__}
    """)

# 本可以不用写这么复杂，但为了证明可以动态加载和执行，所以演示一下
module = __import__('examples.sympy_define', fromlist=['*'])
source = inspect.getsource(module)
exec(source, globals())

st.subheader('自定义表达式')
all_symbols, all_functions = get_symbols_functions(module)

exprs_src = st_ace(value=f"""# 向编辑器登记自动完成关键字，按字母排序
{list_to_string(all_symbols, 30)}

{list_to_string(all_functions, 30)}


# 请在此添加表达式，`=`右边为表达式，`=`左边为新因子名。
alpha_003=-1 * ts_corr(cs_rank(OPEN), cs_rank(VOLUME), 10)
alpha_006=-1 * ts_corr(OPEN, VOLUME, 10)
alpha_101=(CLOSE - OPEN) / ((HIGH - LOW) + 0.001)
alpha_201=alpha_101+CLOSE # 中间变量示例

LABEL_OO_1=ts_delay(OPEN, -2)/ts_delay(OPEN, -1)-1 # 第二天开盘交易
LABEL_OO_2=ts_delay(OPEN, -3)/ts_delay(OPEN, -1)-1 # 第二天开盘交易，持有二天
LABEL_CC_1=ts_delay(CLOSE, -1)/CLOSE-1 # 每天收盘交易
""",
                   language="python",
                   auto_update=True,
                   )

if st.button('生成代码'):
    with st.spinner('生成中，请等待...'):
        # eval处理，转成字典
        raw, exprs_dict = sources_to_exprs(globals().copy(), exprs_src, convert_xor=convert_xor)

        if is_pre_opt:
            logger.info('事前 表达式 替换')
            exprs_dict = replace_exprs(exprs_dict)

        tool = ExprTool()

        logger.info('表达式 抽取 合并')
        exprs_dst, syms_dst = tool.merge(**exprs_dict)

        logger.info('提取公共表达式')
        tool.cse(exprs_dst, symbols_repl=numbered_symbols('_x_'), symbols_redu=exprs_dict.keys())

        logger.info('生成有向无环图')
        exprs_ldl, G = tool.dag(merge=True)

        if is_chain_opt:
            logger.info('分组优化')
            exprs_ldl.optimize()

        logger.info('代码生成')
        source = codegen(exprs_ldl, exprs_dict, syms_dst,
                         filename='template.py.j2',
                         date=date_name, asset=asset_name,
                         extra_codes=(raw,))

        res = format_str(source, mode=Mode(line_length=600, magic_trailing_comma=True))

        b64 = base64.b64encode(res.encode('utf-8'))
        st.markdown(f'<a href="data:file/plain;base64,{b64.decode()}" download="results.py">下载代码</a>',
                    unsafe_allow_html=True)
        # 下载按钮点击后会刷新页面，不推荐
        # st.download_button(label="下载代码", data=res, file_name='output.py')

        with st.expander(label="预览代码"):
            st.code(res, language='python')
