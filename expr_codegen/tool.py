from graphlib import TopologicalSorter

from sympy import simplify, cse, symbols

from expr_codegen.expr import is_NegativeX, get_current_by_prefix, get_children, get_key, CL
from expr_codegen.model import ListDictList, DictList


def dag_ready(graph_dag, graph_key, graph_exp):
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


class ExprTool:

    def __init__(self, date: str, asset: str):
        """指定分组时用到的时间和资产的字段名

        Parameters
        ----------
        date: str
            日期时间字段名
        asset: str
            资产字段名
        """
        self._date = date
        self._asset = asset
        self.get_current_func = get_current_by_prefix
        self.get_current_func_kwargs = {}

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
                     output_exprs=exprs, output_symbols=syms,
                     date=self._date, asset=self._asset)
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

        exprs = exprs + list(kwargs.values())
        exprs = sorted(set(exprs), key=exprs.index)
        syms = sorted(set(syms), key=syms.index)

        # print(exprs)

        return exprs, syms

    def reduce(self, repl, redu):
        """减少中间变量数量，有利用减少内存占用"""

        exprs_dict = {}

        # 不做改动，直接生成
        for variable, expr in repl:
            exprs_dict[variable] = expr
        for variable, expr in redu:
            exprs_dict[variable] = expr

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
        # 有向无环图，用于分层计算
        graph_dag = {}
        # 同一层中 分组所用
        graph_key = {}
        # 每个变量对应的表达式
        graph_exp = {}

        repl, redu = cse(exprs, symbols_repl, optimizations="basic")
        outputs_len = len(symbols_redu)

        new_redu = []
        symbols_redu = iter(symbols_redu)
        for expr in redu[-outputs_len:]:
            # 可能部分表达式只在之前出现过，后面完全用不到如，ts_rank(ts_decay_linear(x_147, 11.4157), 6.72611)
            variable = next(symbols_redu)
            variable = symbols(variable)
            new_redu.append((variable, expr))

        exprs_dict = self.reduce(repl, new_redu)

        # 生成DAG
        for variable, expr in exprs_dict.items():
            syms = []
            children = get_children(self.get_current_func, self.get_current_func_kwargs, expr, [], syms, date=self._date, asset=self._asset)
            key = get_key(children)

            graph_dag[variable.name] = [str(s) for s in syms]
            graph_key[variable.name] = key
            graph_exp[variable.name] = expr

        return graph_dag, graph_key, graph_exp
