import base64
from io import StringIO

import streamlit as st
from streamlit_ace import st_ace

from expr_codegen import codegen_exec, __version__

st.set_page_config(page_title='Expr Codegen', layout="wide")

with st.sidebar:
    st.subheader("配置参数")

    date_name = st.text_input('日期字段名', 'date')
    asset_name = st.text_input('资产字段名', 'asset')

    # 生成代码
    style = st.radio('代码风格', ('polars_over', 'polars_group', 'pandas/cudf.pandas'))
    over_null = st.radio('over_null模式', ('partition_by', 'order_by', None))

    convert_xor = st.checkbox('将`^`转换为`**`', True)

    st.subheader("关于")
    st.markdown(f"""[Github仓库](https://github.com/wukan1986/expr_codegen)

[问题反馈](http://github.com/wukan1986/expr_codegen/issues)

作者: wukan

声明：
1. 本站点不存储用户输入的表达式，安全保密可放心
2. 生成的代码可能有错，发现后请及时反馈

version: {__version__}
    """)

st.subheader('自定义表达式')

exprs_src = st_ace(value=f"""# 请在此添加表达式，`=`右边为表达式，`=`左边为新因子名
alpha_003=-1 * ts_corr(cs_rank(OPEN), cs_rank(VOLUME), 10)
alpha_006=-1 * ts_corr(OPEN, VOLUME, 10)
alpha_101=(CLOSE - OPEN) / ((HIGH - LOW) + 0.001)
alpha_201=alpha_101+CLOSE # 中间变量示例

LABEL_OO_1=OPEN[-2]/OPEN[-1]-1 # 第二天开盘交易
LABEL_OO_2=OPEN[-3]/OPEN[-1]-1 # 第二天开盘交易，持有二天
LABEL_CC_1=CLOSE[-1]/CLOSE-1 # 每天收盘交易
""",
                   language="python",
                   auto_update=True,
                   )

if st.button('生成代码'):
    with st.spinner('生成中，请等待...'):
        code = StringIO()
        codegen_exec(None, exprs_src, output_file=code, convert_xor=convert_xor, style=style, over_null=over_null)
        code.seek(0)
        res = code.read()
        b64 = base64.b64encode(res.encode('utf-8'))
        st.markdown(f'<a href="data:file/plain;base64,{b64.decode()}" download="results.py">下载代码</a>',
                    unsafe_allow_html=True)
        # 下载按钮点击后会刷新页面，不推荐
        # st.download_button(label="下载代码", data=res, file_name='output.py')

        with st.expander(label="预览代码"):
            st.code(res, language='python')
