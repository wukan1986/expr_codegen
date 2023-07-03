from graphlib import TopologicalSorter

from sympy import simplify, cse, symbols

from expr_codegen.expr import get_symbols, is_NegativeX, get_current_by_prefix, get_children, get_key
from expr_codegen.model import ListDictList, DictList


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
        self.get_current_config = {}

    def set_current(self, func, config):
        self.get_current_func = func
        self.get_current_config = config

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
        get_children(self.get_current_func, self.get_current_config,
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
        outputs_len = len(symbols_redu)

        # 记录新的表达式，为了减少字段减少内存
        exprs_dict = {}
        # 维护因子在哪些表达式中出现过
        repl_dl = DictList()
        # 记录-x需替换的表达式，分两段是因为处理的方式不一样
        exprs_negative1 = []
        exprs_negative2 = []

        # 对前部进行查找-x
        # x_19=-x_18，去找哪些表达式中出现了x_19，替换成-x_18
        for variable, expr in repl:
            expr = simplify(expr)
            exprs_dict[variable] = expr

            # 记录在哪出现过
            syms = get_symbols(expr, return_str=False)
            for s in syms:
                repl_dl.append(s, variable)

            # 记录需替换因子
            if is_NegativeX(expr):
                # x_19=-x_18
                exprs_negative1.append((variable, expr))

        # 为后段数据查找-x
        # alpha_006=-x_29，找x_29=?, 将alpha_006=-?
        # 如果x_29被引用了两次就不替换
        symbols_redu = iter(symbols_redu)
        for expr in redu[-outputs_len:]:
            variable = next(symbols_redu)
            variable = symbols(variable)
            expr = simplify(expr)
            exprs_dict[variable] = expr
            syms = get_symbols(expr, return_str=False)
            for s in syms:
                repl_dl.append(s, variable)

            if is_NegativeX(expr):
                # alpha_006=-x_29，找x_29记录下来
                x = expr.args[1]
                exprs_negative2.append((x, exprs_dict.get(x)))

        # 由于表达式为x_19=-x_18，-x_18很简单，所以把出现x_19替换即可
        for va, ex in exprs_negative1:
            vv = repl_dl.get(va)
            for v in vv:
                ee = exprs_dict.get(v)
                exprs_dict[v] = ee.xreplace({va: ex})
            exprs_dict.pop(va)

        # alpha_006=-x_29
        # 由于表达式为x_29=ts_corr，ts_corr很复杂，所以x_29只出现一次的情况下才替换
        for va, ex in exprs_negative2:
            vv = repl_dl.get(va)
            # 被多处引用就不替换
            if len(vv) > 1:
                continue
            for v in vv:
                ee = exprs_dict.get(v)
                exprs_dict[v] = ee.xreplace({va: ex})
            exprs_dict.pop(va)

        # 生成DAG
        for variable, expr in exprs_dict.items():
            graph_dag[variable.name] = get_symbols(expr)
            graph_key[variable.name] = get_key(self.get_current_func, self.get_current_config,
                                               expr, date=self._date, asset=self._asset)
            graph_exp[variable.name] = expr

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
