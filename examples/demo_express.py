from expr_codegen.tool import codegen_exec


def _code_block_():
    # 因子编辑区，可利用IDE的智能提示在此区域编辑因子

    # 会在生成的代码中自动导入
    from polars_ta.wq import cs_mad_zscore_resid

    # 1. 下划线开头的变量只是中间变量，最终输出时会被剔除
    _a = ts_returns(CLOSE, 1)
    _b = ts_sum(min_(_a, 0) ** 2, 20)
    _c = ts_sum(max_(_a, 0) ** 2, 20)
    _d = ts_sum(_a ** 2, 20)
    _e = (_b - _c) / _d
    # 2. 下划线开头的变量可以重复使用。 多个复杂因子多行书写时有重复中间变时不再冲突
    # 3. 下划线开头的变量循环赋值。 在调试时可快速用注释进行切换了
    _e = cs_mad_zscore_resid(_e, LOG_MC_ZS, ONE)
    RSJ = _e


df = None  # 替换成真实的polars数据
df = codegen_exec(_code_block_, df, output_file="output.py")
