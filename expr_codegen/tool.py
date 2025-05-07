import inspect
import pathlib
from functools import lru_cache
from io import TextIOBase
from typing import Sequence, Union, TypeVar, Optional, Literal

import polars as pl
from black import Mode, format_str
from loguru import logger
from sympy import simplify, cse, symbols, numbered_symbols
from sympy.core.expr import Expr
from sympy.logic import boolalg

from expr_codegen.codes import sources_to_exprs
from expr_codegen.expr import get_current_by_prefix, get_children, replace_exprs
from expr_codegen.model import dag_start, dag_end, dag_middle, _RESERVED_WORD_

try:
    from pandas import DataFrame as _pd_DataFrame
except ImportError:
    _pd_DataFrame = None

try:
    from polars import DataFrame as _pl_DataFrame
    from polars import LazyFrame as _pl_LazyFrame
except ImportError:
    _pl_DataFrame = None
    _pl_LazyFrame = None

DataFrame = TypeVar('DataFrame', _pl_LazyFrame, _pl_DataFrame, _pd_DataFrame)

# ===============================
# TypeError: expecting bool or Boolean, not `ts_delay(X, 3)`.
# ts_delay(X, 3) & ts_delay(Y, 3)
boolalg.as_Boolean = lambda x: x


# AttributeError: 'StrictGreaterThan' object has no attribute 'diff'
# ts_count(open > 1, 2) == 2
def _diff(self, *symbols, **assumptions):
    assumptions.setdefault("evaluate", False)
    from sympy.core.function import _derivative_dispatch
    return _derivative_dispatch(self, *symbols, **assumptions)


Expr.diff = _diff


# ===============================

def simplify2(expr):
    # return simplify(expr)
    try:
        expr = simplify(expr)
    except AttributeError as e:
        print(f'{expr} ,表达式无法简化, {e}')
    return expr


class ExprTool:

    def __init__(self):
        self.get_current_func = get_current_by_prefix
        self.get_current_func_kwargs = {}
        self.exprs_list = {}
        self.exprs_names = []
        self.globals_ = {}

    def set_current(self, func, **kwargs):
        self.get_current_func = func
        self.get_current_func_kwargs = kwargs

    def extract(self, expr, date, asset):
        """抽取分割后的子公式

        Parameters
        ----------
        expr
            单表达式

        Returns
        -------
        表达式列表

        """
        exprs = []
        syms = []
        get_children(self.get_current_func, self.get_current_func_kwargs,
                     expr,
                     output_exprs=exprs, output_symbols=syms,
                     date=date, asset=asset)
        # print('=' * 20, expr)
        # print(exprs)
        return exprs, syms

    def merge(self, date, asset, args):
        """合并多个表达式

        1. 先抽取分割子公式
        2. 合并 子公式+长公式，去重

        Parameters
        ----------
        args
            表达式列表

        Returns
        -------
        表达式列表
        """
        # 抽取前先化简
        args = [(k, simplify2(v), c) for k, v, c in args]

        # 保留了注释信息
        exprs_syms = [(self.extract(v, date, asset), c) for k, v, c in args]
        exprs = []
        syms = []
        for (e, s), c in exprs_syms:
            syms.extend(s)
            for _ in e:
                # 抽取的表达式添加注释
                exprs.append((_, c))

        syms = sorted(set(syms), key=syms.index)
        # 如果目标有重复表达式，这里会混乱
        exprs = sorted(set(exprs), key=exprs.index)
        # 这里不能合并简化与未简化的表达式，会导致cse时失败，需要简化表达式合并
        exprs = exprs + [(v, c) for k, v, c in args]

        # print(exprs)
        syms = [str(s) for s in syms]
        return exprs, syms

    def reduce(self, repl, redu):
        """减少中间变量数量，有利用减少内存占用"""

        exprs_list = []

        # cse前简化一次，cse后不再简化
        # (~开盘涨停 & 昨收涨停) | (~收盘涨停 & 最高涨停)
        for k, v in repl:
            exprs_list.append((k, v, "#"))
        for k, v, c in redu:
            exprs_list.append((k, v, c))

        return exprs_list

    def cse(self, exprs, symbols_repl=None, exprs_src=None):
        """多个子公式+长公式，提取公共公式

        Parameters
        ----------
        exprs
            表达式列表
        symbols_repl
            中间字段名迭代器
        exprs_src
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
        self.exprs_names = [k for k, v, c in exprs_src]
        # 包含了注释信息
        _exprs = [k for k, v in exprs]

        # 注意：对于表达式右边相同，左边不同的情况，会当成一个处理
        repl, redu = cse(_exprs, symbols_repl, optimizations="basic")
        outputs_len = len(exprs_src)

        new_redu = []
        symbols_redu = iter(exprs_src)
        for expr in redu[-outputs_len:]:
            # 可能部分表达式只在之前出现过，后面完全用不到如，ts_rank(ts_decay_linear(x_147, 11.4157), 6.72611)
            variable = next(symbols_redu)
            a = symbols(variable[0])
            new_redu.append((a, expr, variable[2]))

        self.exprs_list = self.reduce(repl, new_redu)

        # with open("exprs.pickle", "wb") as file:
        #     pickle.dump(exprs_dict, file)

        return self.exprs_list

    def dag(self, merge: bool, date, asset):
        """生成DAG"""
        G = dag_start(self.exprs_list, self.get_current_func, self.get_current_func_kwargs, date, asset)
        if merge:
            G = dag_middle(G, self.exprs_names, self.get_current_func, self.get_current_func_kwargs, date, asset)
        return dag_end(G)

    def all(self, exprs_src, style: Literal['pandas', 'polars', 'sql'] = 'polars',
            template_file: Optional[str] = None,
            replace: bool = True, regroup: bool = False, format: bool = True,
            date='date', asset='asset',
            extra_codes: Sequence[object] = (),
            table_name: str = 'self',
            **kwargs):
        """功能集成版，将几个功能写到一起方便使用

        Parameters
        ----------
        exprs_src: list
            表达式列表
        style: str
            代码风格。可选值 ('polars', 'pandas', 'sql')
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
        extra_codes: Sequence[object]
            需要复制到模板中的额外代码

        Returns
        -------
        代码字符串

        """
        assert style in ('pandas', 'polars', 'sql')

        if replace:
            exprs_src = replace_exprs(exprs_src)

        # 子表达式在前，原表式在最后
        exprs_dst, syms_dst = self.merge(date, asset, exprs_src)
        syms_dst = list(set(syms_dst) - _RESERVED_WORD_)

        # 提取公共表达式
        self.cse(exprs_dst, symbols_repl=numbered_symbols('_x_'), exprs_src=exprs_src)
        # 有向无环图流转
        exprs_ldl, G = self.dag(True, date, asset)

        if regroup:
            exprs_ldl.optimize(merge=style != 'sql')

        if style == 'polars':
            from expr_codegen.polars.code import codegen
        elif style == 'pandas':
            from expr_codegen.pandas.code import codegen
        elif style == 'sql':
            from expr_codegen.sql.code import codegen
            format = False
        else:
            raise ValueError(f'unknown style {style}')

        extra_codes = [c if isinstance(c, str) else inspect.getsource(c) for c in extra_codes]

        codes = codegen(exprs_ldl, exprs_src, syms_dst,
                        filename=template_file, date=date, asset=asset,
                        extra_codes=extra_codes,
                        table_name=table_name,
                        **kwargs)

        logger.info(f'{style} code is generated')

        if format:
            # 格式化。在遗传算法中没有必要
            codes = format_str(codes, mode=Mode(line_length=600, magic_trailing_comma=True))

        return codes, G

    @lru_cache(maxsize=64)
    def _get_code(self,
                  source: str, *more_sources: str,
                  extra_codes: str,
                  output_file: str,
                  convert_xor: bool,
                  style: Literal['pandas', 'polars', 'sql'] = 'polars',
                  template_file: Optional[str] = None,
                  date: str = 'date', asset: str = 'asset',
                  table_name: str = 'self',
                  **kwargs) -> str:
        """通过字符串生成代码， 加了缓存，多次调用不重复生成"""
        raw, exprs_list = sources_to_exprs(self.globals_, source, *more_sources, convert_xor=convert_xor)

        # 生成代码
        code, G = _TOOL_.all(exprs_list, style=style, template_file=template_file,
                             replace=True, regroup=True, format=True,
                             date=date, asset=asset,
                             # 复制了需要使用的函数，还复制了最原始的表达式
                             extra_codes=(raw,
                                          # 传入多个列的方法
                                          extra_codes,
                                          ),
                             table_name=table_name,
                             **kwargs)

        # 移回到cache，防止多次调用多次保存
        if isinstance(output_file, TextIOBase):
            # 输出到控制台
            output_file.write(code)
        elif output_file is not None:
            output_file = pathlib.Path(output_file)
            logger.info(f'save to {output_file.absolute()}')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(code)

        return code


@lru_cache(maxsize=64, typed=True)
def _get_func_from_code_py(code: str):
    logger.info(f'get func from code py')
    globals_ = {}
    exec(code, globals_)
    return globals_['main']


@lru_cache(maxsize=64, typed=True)
def _get_func_from_module(module: str):
    """"可下断点调试"""
    m = __import__(module, fromlist=['*'])
    logger.info(f'get func from module {m}')
    return m.main


@lru_cache(maxsize=64, typed=True)
def _get_func_from_file_py(file: str):
    file = pathlib.Path(file)
    logger.info(f'get func from file "{file.absolute()}"')
    with open(file, 'r', encoding='utf-8') as f:
        globals_ = {}
        exec(f.read(), globals_)
        return globals_['main']


@lru_cache(maxsize=64, typed=True)
def _get_code_from_file(file: str):
    file = pathlib.Path(file)
    logger.info(f'get code from file "{file.absolute()}"')
    with open(file, 'r', encoding='utf-8') as f:
        return f.read()


_TOOL_ = ExprTool()


def codegen_exec(df: Optional[DataFrame],
                 *codes,
                 over_null: Literal['partition_by', 'order_by', None],
                 extra_codes: str = r'CS_SW_L1 = r"^sw_l1_\d+$"',
                 output_file: Union[str, TextIOBase, None] = None,
                 run_file: Union[bool, str] = False,
                 convert_xor: bool = False,
                 style: Literal['pandas', 'polars', 'sql'] = 'polars',
                 template_file: Optional[str] = None,
                 date: str = 'date', asset: str = 'asset',
                 table_name: str = 'self',
                 **kwargs) -> Union[DataFrame, str, None]:
    """快速转换源代码并执行

    Parameters
    ----------
    df: pl.DataFrame, pd.DataFrame, pl.LazyFrame,None
        输入DataFrame，输出DataFrame
        输入None，输出代码
    codes:
        函数体。此部分中的表达式会被翻译成目标代码
    extra_codes: str
        额外代码。不做处理，会被直接复制到目标代码中
    output_file: str| TextIOBase
        保存生成的目标代码到文件中
    run_file: bool or str
        是否不生成脚本，直接运行代码。注意：带缓存功能，多次调用不重复生成
        - 如果是True，会自动从output_file中读取代码
        - 如果是字符串，会自动从run_file中读取代码
        - 如果是模块名，会自动从模块中读取代码(可调试)
            - 注意：可能调用到其他目录下的同名模块，所以保存的文件名要有辨识度
    convert_xor: bool
        ^ 转成异或还是乘方
    style: str
        代码风格。可选值 'pandas', 'polars', 'sql'
        - pandas: 不支持struct
        - sql: 只生成sql语句，不执行
    template_file: str
        代码模板
    date: str
        时间字段
    asset: str
        资产字段
    over_null: str
        时序中遇到null时的处理方式
        - partition_by: 空值划分到不同分区
        - order_by: 空值排同一分区的前排
        - None: 不做处理
    table_name:str
        表名。style=sql时有效

    Returns
    -------
    DataFrame
        输出DataFrame
    str
        输出代码

    Notes
    -----
    处处都有缓存，所以在公式研发阶段要留意日志输出。以免一直调试的旧公式

    1. 确保重新生成了代码  `code is generated`
    2. 通过代码得到了函数 `get func from code`

    """
    if df is not None:
        input_file = None
        # 以下代码都带缓存功能
        if run_file is True:
            assert output_file is not None, 'output_file is required'
            input_file = str(output_file)
        elif run_file is not False:
            input_file = str(run_file)

        if input_file is not None:
            if input_file.endswith('.py'):
                return _get_func_from_file_py(input_file)(df)
            elif input_file.endswith('.sql'):
                with pl.SQLContext(frames={table_name: df}) as ctx:
                    return ctx.execute(_get_code_from_file(input_file), eager=isinstance(df, _pl_DataFrame))
            else:
                return _get_func_from_module(input_file)(df)  # 可断点调试
    else:
        pass

    # 此代码来自于sympy.var
    frame = inspect.currentframe().f_back
    _TOOL_.globals_ = frame.f_globals.copy()
    del frame

    more_sources = [c if isinstance(c, str) else inspect.getsource(c) for c in codes]

    code = _TOOL_._get_code(
        *more_sources,
        extra_codes=extra_codes,
        output_file=output_file,
        convert_xor=convert_xor,
        style=style, template_file=template_file,
        date=date, asset=asset,
        over_null=over_null,
        table_name=table_name,
        **kwargs
    )

    if df is None:
        # 如果df为空，直接返回代码
        return code
    elif style == 'sql':
        with pl.SQLContext(frames={table_name: df}) as ctx:
            return ctx.execute(code, eager=isinstance(df, _pl_DataFrame))
    else:
        # 代码一样时就从缓存中取出函数
        return _get_func_from_code_py(code)(df)
