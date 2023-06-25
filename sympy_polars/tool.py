import os
from functools import reduce

import jinja2
from jinja2 import FileSystemLoader
from sympy import simplify, cse
from sympy.core import Mul
from sympy.core.singleton import S

from sympy_polars.printer import PolarsStrPrinter


class List2D:
    """嵌套列表，主要实现 多行*三列 ，"""

    def __init__(self, max_col=3):
        self._list = []
        self._row = 0
        self._last_col = -1
        self._max_col = max_col

    def append(self, col, item):
        assert 0 <= col < self._max_col
        if col < self._last_col:
            self._row += 1
        while len(self._list) <= self._row:
            # 这里不能用[[[],]*3],因为最内的[]是同一个对象，此处需要多个对象
            self._list += [[[] for _ in range(self._max_col)]]

        tmp = self._list[self._row][col]
        tmp.append(item)
        self._last_col = col

    def clear(self):
        self._list = []

    def values(self):
        return self._list.copy()


def flatten(nested_list):
    """嵌套列表转成一维列表"""
    flat_list = []
    for item in nested_list:
        if isinstance(item, list):
            flat_list.extend(flatten(item))
        else:
            flat_list.append(item)
    return flat_list


def get_curr_expr_type(expr):
    """根据函数名得到当前的函数类型

    也可以维护不同的容器，查找是否在容器中，这样函数名就没有限制了
    """
    if hasattr(expr, 'name'):
        if expr.name.startswith('ts_'):
            # time series
            return 0b0001
        if expr.name.startswith('cs_'):
            # cross-sectional
            return 0b0010
        if expr.name.startswith('gp_'):
            # group
            return 0b0100
    # element-wise
    return 0b0000


class ExprTool:
    def __init__(self):
        self._exprs = []

    def get_depth_expr_type(self, expr):
        """得到多层表达式类型"""
        curr = get_curr_expr_type(expr)
        depths = [self.get_depth_expr_type(a) for a in expr.args]
        depths = [d for d in depths if d > 0]
        inner = reduce(lambda x, y: x | y, depths, 0)

        # 内部不统一，内部非0的都处理
        if inner in (0b0011, 0b0101, 0b0110, 0b0111):
            for i, d in enumerate(depths):
                node = expr.args[i]
                if isinstance(node, Mul) and node.args[0] is S.NegativeOne:
                    # -x TO x
                    self._exprs.append(node.args[1])
                else:
                    self._exprs.append(node)
        elif curr > 0:
            # 内外不统一，不一样的需处理
            for i, d in enumerate(depths):
                if curr ^ d > 0:
                    node = expr.args[i]
                    if isinstance(node, Mul) and node.args[0] is S.NegativeOne:
                        self._exprs.append(node.args[1])
                    else:
                        self._exprs.append(node)
        if curr == 0:
            return inner
        else:
            return curr

    def extract(self, expr):
        """"""
        # 抽取前先化简
        expr = simplify(expr)

        self._exprs = []
        self.get_depth_expr_type(expr)
        return self._exprs.copy()

    def merge(self, **kwargs):
        args = [self.extract(v) for v in kwargs.values()] + [list(kwargs.values())]
        exprs = reduce(lambda x, y: x + y, args, [])
        exprs = sorted(set(exprs), key=exprs.index)
        return exprs

    def cse(self, exprs, symbols_repl=None, symbols_redu=None):
        symbols_redu = iter(symbols_redu)

        p = PolarsStrPrinter()
        expr_2d = List2D()
        code_2d = List2D()

        repl, redu = cse(exprs, symbols_repl, optimizations="basic")
        for variable, expr in repl:
            expr = simplify(expr)
            col = self.get_depth_expr_type(expr)
            code = f"# {variable} = {expr}\n{variable}=({p.doprint(expr)}),"
            expr_2d.append(col, (variable, expr))
            code_2d.append(col, code)

        for i, expr in enumerate(redu):
            # 单元素没有必要打印
            if len(expr.args) == 0:
                continue
            variable = next(symbols_redu)
            expr = simplify(expr)
            col = self.get_depth_expr_type(expr)
            code = f"# {variable} = {expr}\n{variable}=({p.doprint(expr)}),"
            expr_2d.append(col, (variable, expr))
            code_2d.append(col, code)

        return expr_2d, code_2d

    def codegen(self, code_2d: List2D, expr_2d: List2D, origin=""):
        rows = code_2d.values()
        temp = flatten(expr_2d.values())
        env = jinja2.Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
        template = env.get_template('polars.py.j2')
        return template.render(rows=rows, origin=origin, exprs=temp)
