import base64
import inspect
from itertools import islice

import streamlit as st
import sympy
from black import format_str, Mode
from loguru import logger
from streamlit_ace import st_ace
from sympy import numbered_symbols, Symbol, FunctionClass

import expr_codegen
from expr_codegen.codes import source_to_asts
from expr_codegen.expr import replace_exprs, dict_to_exprs
from expr_codegen.tool import ExprTool


def _batched(iterable, n):
    """Batch data into lists of length *n*. The last batch may be shorter.

    >>> list(batched('ABCDEFG', 3))
    [('A', 'B', 'C'), ('D', 'E', 'F'), ('G',)]

    On Python 3.12 and above, this is an alias for :func:`itertools.batched`.
    """
    if n < 1:
        raise ValueError('n must be at least one')
    it = iter(iterable)
    while True:
        batch = tuple(islice(it, n))
        if not batch:
            break
        yield batch


# batched

def get_symbols_functions(module):
    """获取Symbol与Function"""
    symbols = [n for n, _ in inspect.getmembers(module, lambda x: isinstance(x, Symbol))]
    functions = [n for n, _ in inspect.getmembers(module, lambda x: isinstance(x, FunctionClass) or inspect.isfunction(x))]
    # 去一个特殊值
    functions = [_ for _ in functions if _ != 'Function']
    return symbols, functions


def list_to_string(items, n):
    txts = []
    for ss in _batched(items, n):
        txts.append(f'# {",".join(ss)}')
    return '\n'.join(txts)


st.set_page_config(page_title='Expr Codegen', layout="wide")

with st.sidebar:
    st.subheader("配置参数")

    date_name = st.text_input('日期字段名', 'date')
    asset_name = st.text_input('资产字段名', 'asset')

    factors_text_area = st.text_area(label='新增预定义因子', value="""# Alpha101基础因子
OPEN, HIGH, LOW, CLOSE, VOLUME, AMOUNT,
RETURNS, VWAP, CAP,
ADV5, ADV10, ADV15, ADV20, ADV30, ADV40, ADV50, ADV60, ADV81, ADV120, ADV150, ADV180,
SECTOR, INDUSTRY, SUBINDUSTRY,""")

    # 生成代码
    style = st.radio('代码风格', ('polars', 'pandas/cudf.pandas'))
    if style == 'polars':
        from expr_codegen.polars.code import codegen
    else:
        from expr_codegen.pandas.code import codegen

    st.subheader("优化")
    is_pre_opt = st.checkbox('事前`表达式`替换', True)
    is_chain_opt = st.checkbox('事后`首尾接龙`向前合并', True)
    # TODO: 好像这个还有问题等有空再改
    is_back_opt = st.checkbox('事后`整列分组`向前合并', False)

    st.subheader("关于")
    st.markdown(f"""[Github仓库](https://github.com/wukan1986/expr_codegen)

[问题反馈](http://github.com/wukan1986/expr_codegen/issues)

作者: wukan

声明：
1. 本站点不存储用户输入的表达式，安全保密可放心
2. 生成的代码可能有错，发现后请及时反馈

version: {expr_codegen.__version__}
    """)

with st.expander(label="预定义**算子**"):
    st.write('如缺算子，可以在issue中申请添加，或下载代码进行二次开发')

    # 本可以不用写这么复杂，但为了证明可以动态加载和执行，所以演示一下
    module = __import__('examples.sympy_define', fromlist=['*'])

    source = inspect.getsource(module)
    st.code(source)
    # 执行
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
        # 自定义注册到全局变量
        sympy.var(factors_text_area)

        # eval处理，转成字典
        raw, assigns = source_to_asts(exprs_src)
        assigns_dict = dict_to_exprs(assigns, globals().copy())

        if is_pre_opt:
            logger.info('事前 表达式 替换')
            assigns_dict = replace_exprs(assigns_dict)

        tool = ExprTool()

        logger.info('表达式 抽取 合并')
        exprs_dst, syms_dst = tool.merge(**assigns_dict)

        logger.info('提取公共表达式')
        tool.cse(exprs_dst, symbols_repl=numbered_symbols('_x_'), symbols_redu=assigns_dict.keys())

        logger.info('生成有向无环图')
        exprs_ldl, G = tool.dag(merge=True)

        logger.info('分组优化')
        exprs_ldl.optimize(back_opt=is_back_opt, chain_opt=is_chain_opt)

        logger.info('代码生成')
        source = codegen(exprs_ldl, assigns_dict, syms_dst,
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
