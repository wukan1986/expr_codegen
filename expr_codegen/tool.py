from functools import reduce

from sympy import simplify, cse

from expr_codegen.expr import ListDictList, ExprInspect


class ExprTool:

    def __init__(self, date: str, asset: str, inspect: ExprInspect):
        """指定分组时用到的时间和资产的字段名

        Parameters
        ----------
        date: str
            日期时间字段名
        asset: str
            资产字段名
        inspect:
            表达式识别工具类
        """
        self._date = date
        self._asset = asset
        self._inspect = inspect

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
        self._inspect.get_children(expr,
                                   output_exprs=exprs, output_symbols=[],
                                   date=self._date, asset=self._asset)
        return exprs

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
        args = [self.extract(v) for v in kwargs.values()] + [list(kwargs.values())]
        exprs = reduce(lambda x, y: x + y, args, [])
        exprs = sorted(set(exprs), key=exprs.index)
        return exprs

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
        根据条件分割后的表达式容器

        """
        symbols_redu = iter(symbols_redu)
        exprs_ldl = ListDictList()

        repl, redu = cse(exprs, symbols_repl, optimizations="basic")
        for variable, expr in repl:
            expr = simplify(expr)
            key = self._inspect.get_key(expr, date=self._date, asset=self._asset)
            exprs_ldl.append(key, (variable, expr))

        for i, expr in enumerate(redu):
            # 单元素没有必要打印
            if len(expr.args) == 0:
                continue
            variable = next(symbols_redu)
            expr = simplify(expr)
            # 表达式集合得到的元组
            key = self._inspect.get_key(expr, date=self._date, asset=self._asset)
            exprs_ldl.append(key, (variable, expr))

        return exprs_ldl
