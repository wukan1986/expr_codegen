import inspect
from functools import lru_cache
from io import TextIOWrapper
from typing import Sequence, Dict, Optional

from black import Mode, format_str
from sympy import simplify, cse, symbols, numbered_symbols

from expr_codegen.codes import sources_to_exprs
from expr_codegen.expr import get_current_by_prefix, get_children, replace_exprs
from expr_codegen.model import dag_start, dag_end, dag_middle


class ExprTool:

    def __init__(self):
        self.get_current_func = get_current_by_prefix
        self.get_current_func_kwargs = {}
        self.exprs_dict = {}
        self.exprs_names = []
        self.globals_ = {}

    def set_current(self, func, **kwargs):
        self.get_current_func = func
        self.get_current_func_kwargs = kwargs

    def extract(self, expr):
        """抽取分割后的子公式

        Parameters
        ----------
        expr
            单表达式

        Returns
        -------
        表达式列表

        """
        # 抽取前先化简
        expr = simplify(expr)

        exprs = []
        syms = []
        get_children(self.get_current_func, self.get_current_func_kwargs,
                     expr,
                     output_exprs=exprs, output_symbols=syms)
        # print('=' * 20, expr)
        # print(exprs)
        return exprs, syms

    def merge(self, **kwargs):
        """合并多个表达式

        1. 先抽取分割子公式
        2. 合并 子公式+长公式，去重

        Parameters
        ----------
        kwargs
            表达式字典

        Returns
        -------
        表达式列表
        """
        exprs_syms = [self.extract(v) for v in kwargs.values()]
        exprs = []
        syms = []
        for e, s in exprs_syms:
            exprs.extend(e)
            syms.extend(s)

        syms = sorted(set(syms), key=syms.index)
        # 如果目标有重复表达式，这里会混乱
        exprs = sorted(set(exprs), key=exprs.index)
        exprs = exprs + list(kwargs.values())

        # print(exprs)
        syms = [str(s) for s in syms]
        return exprs, syms

    def reduce(self, repl, redu):
        """减少中间变量数量，有利用减少内存占用"""

        exprs_dict = {}

        # 不做改动，直接生成
        for variable, expr in repl:
            exprs_dict[variable] = simplify(expr)
        for variable, expr in redu:
            exprs_dict[variable] = simplify(expr)

        return exprs_dict

    def cse(self, exprs, symbols_repl=None, symbols_redu=None):
        """多个子公式+长公式，提取公共公式

        Parameters
        ----------
        exprs
            表达式列表
        symbols_repl
            中间字段名迭代器
        symbols_redu
            最终字段名列表

        Returns
        -------
        graph_dag
            依赖关系的有向无环图
        graph_key
            每个函数分组用key
        graph_exp
            表达式

        """
        self.exprs_names = list(symbols_redu)

        repl, redu = cse(exprs, symbols_repl, optimizations="basic")
        outputs_len = len(symbols_redu)

        new_redu = []
        symbols_redu = iter(symbols_redu)
        for expr in redu[-outputs_len:]:
            # 可能部分表达式只在之前出现过，后面完全用不到如，ts_rank(ts_decay_linear(x_147, 11.4157), 6.72611)
            variable = next(symbols_redu)
            variable = symbols(variable)
            new_redu.append((variable, expr))

        self.exprs_dict = self.reduce(repl, new_redu)

        # with open("exprs.pickle", "wb") as file:
        #     pickle.dump(exprs_dict, file)

        return self.exprs_dict

    def dag(self, merge: bool):
        """生成DAG"""
        G = dag_start(self.exprs_dict, self.get_current_func, self.get_current_func_kwargs)
        if merge:
            G = dag_middle(G, self.exprs_names, self.get_current_func, self.get_current_func_kwargs)
        return dag_end(G)

    def all(self, exprs_src, style: str = 'polars', template_file: str = 'template.py.j2',
            replace: bool = True, regroup: bool = False, format: bool = True,
            date='date', asset='asset',
            alias: Dict[str, str] = {},
            extra_codes: Sequence[object] = ()):
        """功能集成版，将几个功能写到一起方便使用

        Parameters
        ----------
        exprs_src: dict
            表达式字典
        style: str
            代码风格。可选值 ('polars', 'pandas')
        template_file: str
            根据需求可定制模板
        replace:bool
            表达式提换
        regroup:bool
            分组重排。注意：目前好像不稳定
        format:bool
            代码格式化
        date:str
            日期字段名
        asset:str
            资产字段名
        alias: Dict[str,str]
            符号别名。可以变通的传入正则符号名
        extra_codes: Sequence[object]
            需要复制到模板中的额外代码

        Returns
        -------
        代码字符串

        """
        assert style in ('polars', 'pandas')

        if replace:
            exprs_src = replace_exprs(exprs_src)

        # 子表达式在前，原表式在最后
        exprs_dst, syms_dst = self.merge(**exprs_src)

        # 提取公共表达式
        self.cse(exprs_dst, symbols_repl=numbered_symbols('_x_'), symbols_redu=exprs_src.keys())
        # 有向无环图流转
        exprs_ldl, G = self.dag(True)

        if regroup:
            exprs_ldl.optimize()

        if style == 'polars':
            from expr_codegen.polars.code import codegen
        else:
            from expr_codegen.pandas.code import codegen

        extra_codes = [c if isinstance(c, str) else inspect.getsource(c) for c in extra_codes]

        codes = codegen(exprs_ldl, exprs_src, syms_dst,
                        filename=template_file, date=date, asset=asset,
                        alias=alias,
                        extra_codes=extra_codes)

        if format:
            # 格式化。在遗传算法中没有必要
            codes = format_str(codes, mode=Mode(line_length=600, magic_trailing_comma=True))

        return codes, G

    def exec(self, codes: str, df_input):
        """执行代码

        Notes
        -----
        注意生成的代码已经约定输入用df_input，输出用df_output

        """
        globals_ = {'df_input': df_input}
        exec(codes, globals_)
        return globals_['df_output']

    @lru_cache(maxsize=64)
    def _get_code(self,
                  source: str, *more_sources: str,
                  extra_codes: str, output_file: str,
                  style='polars', template_file='template.py.j2',
                  date='date', asset='asset') -> str:
        """通过字符串生成代码， 加了缓存，多次调用不重复生成"""
        raw, exprs_dict = sources_to_exprs(self.globals_, source, *more_sources, safe=False)

        # 生成代码
        code, G = _TOOL_.all(exprs_dict, style=style, template_file=template_file,
                             replace=True, regroup=True, format=True,
                             date=date, asset=asset,
                             # 复制了需要使用的函数，还复制了最原始的表达式
                             extra_codes=(raw,
                                          # 传入多个列的方法
                                          extra_codes,
                                          ))
        if isinstance(output_file, TextIOWrapper):
            output_file.write(code)
        elif output_file is not None:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(code)

        return code


_TOOL_ = ExprTool()


def codegen_exec(df,
                 *codes,
                 extra_codes: str = r'CS_SW_L1 = pl.col(r"^sw_l1_\d+$")',
                 output_file: Optional[str] = None,
                 style: str = 'polars', template_file: str = 'template.py.j2',
                 date: str = 'date', asset: str = 'asset'
                 ):
    """快速转换源代码并执行

    Parameters
    ----------
    df: pl.DataFrame
        输入DataFrame
    codes:
        函数体。此部分中的表达式会被翻译成目标代码
    extra_codes: str
        额外代码。不做处理，会被直接复制到目标代码中
    output_file: str
        保存生成的目标代码到文件中
    style: str
        代码风格。可选值 ('polars', 'pandas')
    template_file: str
        代码模板
    date: str
        时间字段
    asset: str
        资产字段

    Returns
    -------
    pl.DataFrame

    """
    # 此代码来自于sympy.var
    frame = inspect.currentframe().f_back
    _TOOL_.globals_ = frame.f_globals.copy()
    del frame

    more_sources = [c if isinstance(c, str) else inspect.getsource(c) for c in codes]

    code = _TOOL_._get_code(
        *more_sources, extra_codes=extra_codes,
        output_file=output_file,
        style=style, template_file=template_file,
        date=date, asset=asset,
    )

    if df is None:
        return df
    else:
        return _TOOL_.exec(code, df)
