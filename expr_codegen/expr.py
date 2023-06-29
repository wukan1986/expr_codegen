from abc import ABC
from functools import reduce
from typing import Iterable

from sympy import Mul, Function
from sympy.core.singleton import S

# 预定义前缀，算子用前缀进行区分更方便。
# 当然也可以用是否在某容器中进行分类
CL = 'cl'  # 列算子
TS = 'ts'  # 时序算子
CS = 'cs'  # 横截面算子
GP = 'gp'  # 分组算子。分组越小，速度越慢


def append_negative_one(node, output_exprs):
    """添加到队列。其中，-x将转为x

    此举是为了防止公共表达式中出现大量-x这种情况

    Parameters
    ----------
    node
        表达式当前节点
    output_exprs
        表达式列表

    Returns
    -------
    表达式列表

    """
    if isinstance(node, Mul) and node.args[0] is S.NegativeOne:
        # Mul(-1, x) 即 -x
        output_exprs.append(node.args[1])
    elif node is S.NegativeOne:
        pass
    else:
        output_exprs.append(node)
    return output_exprs


class ExprInspect(ABC):
    """表达式识别抽象类"""

    def get_current(self, expr, date, asset):
        """得到当前算子的类别

        Parameters
        ----------
        expr
            表达式
        date
            日期字段名
        asset
            资产字段名

        Returns
        -------
        当前算子的类别

        """
        # 抽象类中的抽象方法
        return CL,

    def get_children(self, expr, output_exprs, output_symbols, date, asset):
        """子表达式集合

        Parameters
        ----------
        expr
            当前表达式
        output_exprs
            存储中间表达式
        output_symbols
            存储中间符号
        date
            日期字段名。生成对应的函数名，以及分组键名
        asset
            资产字段名。生成对应的函数名，以及分组键名

        Returns
        -------
        当前是列算子，返回子公式元组集合
        当前是其它算子，返回当前算子元组

        """
        curr = self.get_current(expr, date, asset)
        children = [self.get_children(a, output_exprs, output_symbols, date, asset) for a in expr.args]
        # 删除长度为0的，CLOSE、-1 等符号为0
        children = [c for c in children if len(c) > 0]
        # 多个集合合成一个去重
        unique = reduce(lambda x, y: x | y, children, set())

        if len(unique) >= 2:
            # 大于1，表示内部不统一，内部都要处理
            for i, child in enumerate(children):
                output_exprs = append_negative_one(expr.args[i], output_exprs)
        elif curr[0] != CL:
            # 外部与内部不同，需处理
            for i, child in enumerate(children):
                # 不在子中即表示不同
                if curr in child:
                    continue
                output_exprs = append_negative_one(expr.args[i], output_exprs)

        # 按需返回，当前是基础算子就返回下一层信息，否则返回当前
        if curr[0] == CL:
            if expr.is_Symbol:
                # 汇总符号列表
                output_symbols.append(expr)
            # 返回子中出现过的集合{ts cs gp}
            return unique
        else:
            # 当前算子，非列算子，直接返回，如{ts} {cs} {gp}
            return set([curr])

    def get_key(self, expr, date, asset):
        """当前表达式，存字典时的 键

        Parameters
        ----------
        expr
            表达式
        date
            日期字段名
        asset
            资产字段名

        Returns
        -------
        用于字典的键

        """
        tup = self.get_children(expr, [], [], date=date, asset=asset)

        if len(tup) == 0:
            return CL,
        else:
            # TODO: 取首个是否会有问题？
            return list(tup)[0]

    def get_symbols(self, expr):
        syms = []
        for arg in expr.args:
            if arg.is_Symbol:
                syms.append(arg.name)
            else:
                syms += self.get_symbols(arg)
        return syms


class ExprInspectByPrefix(ExprInspect):
    """表达式识别，按名称前缀"""

    def get_current(self, expr, date, asset):
        if expr.is_Function:
            prefix1 = expr.name[2]
            if prefix1 == '_':
                prefix2 = expr.name[:2]

                if prefix2 == TS:
                    return TS, asset, date
                if prefix2 == CS:
                    return CS, date
                if prefix2 == GP:
                    return GP, date, expr.args[0].name
        # 不需分组
        return CL,


class ExprInspectByName(ExprInspect):
    def __init__(self, ts_names: Iterable[Function], cs_names: Iterable[Function], gp_names: Iterable[Function]):
        """初始化

        Parameters
        ----------
        ts_names
            时序算子集合
        cs_names
            横截面算子集合
        gp_names
            分组算子集合
        """
        self._TS_NAMES = {f.name for f in ts_names}
        self._CS_NAMES = {f.name for f in cs_names}
        self._GP_NAMES = {f.name for f in gp_names}

    def get_current(self, expr, date, asset):
        if expr.is_Function:
            if expr.name in self._TS_NAMES:
                return TS, asset, date
            if expr.name in self._CS_NAMES:
                return CS, date
            if expr.name in self._GP_NAMES:
                return GP, date, expr.args[0].name

        # 不需分组
        return CL,
