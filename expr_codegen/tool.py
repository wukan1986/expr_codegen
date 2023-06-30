from functools import reduce
from graphlib import TopologicalSorter

from sympy import simplify, cse

from expr_codegen.expr import ExprInspect
from expr_codegen.model import ListDictList


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
        syms = []
        self._inspect.get_children(expr,
                                   output_exprs=exprs, output_symbols=syms,
                                   date=self._date, asset=self._asset)
        # print('=' * 20, expr)
        # print(exprs)
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
        # args = [list(kwargs.values())] + [self.extract(v) for v in kwargs.values()]
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
        graph_dag
            依赖关系的有向无环图
        graph_key
            每个函数分组用key
        graph_exp
            表达式

        """
        graph_dag = {}
        graph_key = {}
        graph_exp = {}

        repl, redu = cse(exprs, symbols_repl, optimizations="basic")
        # 最终表达式开始位置
        exprs_start = len(redu) - len(symbols_redu)

        for variable, expr in repl:
            expr = simplify(expr)

            graph_dag[variable.name] = set(self._inspect.get_symbols(expr))
            graph_key[variable.name] = self._inspect.get_key(expr, date=self._date, asset=self._asset)
            graph_exp[variable.name] = expr

        symbols_redu = iter(symbols_redu)
        for i, expr in enumerate(redu):
            # 前面是需要输出的表达式
            # if i >= src_len:
            #     continue
            if i < exprs_start:
                continue
            # print(expr)
            variable = next(symbols_redu)
            expr = simplify(expr)

            graph_dag[variable] = set(self._inspect.get_symbols(expr))
            graph_key[variable] = self._inspect.get_key(expr, date=self._date, asset=self._asset)
            graph_exp[variable] = expr

        return graph_dag, graph_key, graph_exp

    def dag_ready(self, graph_dag, graph_key, graph_exp):
        """有向无环图流转"""
        exprs_ldl = ListDictList()

        ts = TopologicalSorter(graph_dag)
        ts.prepare()

        nodes = ts.get_ready()  # 基础符号
        ts.done(*nodes)  # 移动到第二行
        nodes = ts.get_ready()  # 取第二行结果
        while len(nodes) > 0:
            exprs_ldl.next_row()
            for node in nodes:
                exprs_ldl.append(graph_key[node], (node, graph_exp[node]))
            ts.done(*nodes)
            nodes = ts.get_ready()

        # with open("test.pickle", "wb") as file:
        #     pickle.dump(exprs_ldl, file)
        return exprs_ldl
