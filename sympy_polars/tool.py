import os
from functools import reduce

import jinja2
from jinja2 import FileSystemLoader
from sympy import simplify, cse

from sympy_polars.expr import get_childen_expr_tuple, ListDictList, get_childen_expr_key, get_groupby_from_tuple
from sympy_polars.printer import PolarsStrPrinter


class ExprTool:

    def __init__(self, date, asset):
        """指定分组时用到的时间和资产的字段名"""
        self._date = date
        self._asset = asset

    def extract(self, expr):
        """抽取按条件分割后的子公式"""
        # 抽取前先化简
        expr = simplify(expr)

        exprs = []
        get_childen_expr_tuple(expr,
                               output_exprs=exprs, output_symbols=[],
                               date=self._date, asset=self._asset)
        return exprs

    def merge(self, **kwargs):
        """合并多个长公式

        1. 先抽取分割子公式
        2. 合并子公式+长公式，去重
        """
        args = [self.extract(v) for v in kwargs.values()] + [list(kwargs.values())]
        exprs = reduce(lambda x, y: x + y, args, [])
        exprs = sorted(set(exprs), key=exprs.index)
        return exprs

    def cse(self, exprs, symbols_repl=None, symbols_redu=None):
        """多个子公式+长公式，提取公共公式"""
        symbols_redu = iter(symbols_redu)
        exprs_ldl = ListDictList()

        repl, redu = cse(exprs, symbols_repl, optimizations="basic")
        for variable, expr in repl:
            expr = simplify(expr)
            key = get_childen_expr_key(expr, date=self._date, asset=self._asset)
            exprs_ldl.append(key, (variable, expr))

        for i, expr in enumerate(redu):
            # 单元素没有必要打印
            if len(expr.args) == 0:
                continue
            variable = next(symbols_redu)
            expr = simplify(expr)
            # 表达式集合得到的元组
            key = get_childen_expr_key(expr, date=self._date, asset=self._asset)
            exprs_ldl.append(key, (variable, expr))

        return exprs_ldl

    def codegen(self, exprs_ldl: ListDictList, exprs_src, filename='polars.py.j2'):
        """基于模板的代码生成"""
        # 打印Polars风格代码
        p = PolarsStrPrinter()

        # polars风格代码
        funcs = {}
        # 分组应用代码
        groupbys = {}
        # 处理过后的表达式
        exprs_dst = {}

        for i, row in enumerate(exprs_ldl.values()):
            for k, vv in row.items():
                # 函数名
                func_name = f'func_{i}_{"__".join(k)}'
                func_code = []
                for va, ex in vv:
                    exprs_dst[va] = ex
                    func_code.append(f"# {va} = {ex}\n{va}=({p.doprint(ex)}),")
                # polars风格代码列表
                funcs[func_name] = func_code
                # 分组应用代码
                groupbys[func_name] = get_groupby_from_tuple(k, func_name)

        env = jinja2.Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
        template = env.get_template(filename)
        return template.render(funcs=funcs, groupbys=groupbys,
                               exprs_src=exprs_src, exprs_dst=exprs_dst)
