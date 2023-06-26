from functools import reduce

from sympy import simplify, cse

from sympy_polars.expr import get_childen_expr_tuple, ListDictList, get_childen_expr_key


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
