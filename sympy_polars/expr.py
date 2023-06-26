from functools import reduce

from sympy import Mul
from sympy.core.singleton import S

# 预定义前缀，算子用前缀进行区分更方便。
# 当然也可以用是否在某容器中进行分类
CL = 'cl'  # 列算子
TS = 'ts'  # 时序算子
CS = 'cs'  # 横截面算子
GP = 'gp'  # 分组算子


def get_curr_expr_tuple(expr, date, asset):
    """得到当前表达式的元组

    用于多个表达式划分到不同分组
    """
    if hasattr(expr, 'name'):
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


def get_groupby_from_tuple(tup, func_name):
    """从传入的元组中生成分组运行代码"""
    prefix2, *_ = tup

    if prefix2 == TS:
        # 组内需要按时间进行排序，需要维持顺序
        prefix2, asset, date = tup
        return f'df = df.sort(by={[asset, date]}).groupby(by={[asset]}, maintain_order=True).apply({func_name})'
    if prefix2 == CS:
        prefix2, date = tup
        return f'df = df.sort(by={[date]}).groupby(by={[date]}, maintain_order=False).apply({func_name})'
    if prefix2 == GP:
        prefix2, date, group = tup
        return f'df = df.sort(by={[date, group]}).groupby(by={[date, group]}, maintain_order=False).apply({func_name})'

    return f'df = {func_name}(df)'


def get_childen_expr_tuple(expr, output_exprs, output_symbols, date, asset):
    """当前表达式元组集合

    当前是列算子，返回子公式元组集号
    当前是其它算子，返回当前算子元组
    """
    curr = get_curr_expr_tuple(expr, date, asset)
    children = [get_childen_expr_tuple(a, output_exprs, output_symbols, date, asset) for a in expr.args]
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


def append_negative_one(node, output_exprs):
    """添加到队列，其中-x将转为x

    此举是为了防止，公共公式中出现大量-x这种情况
    """
    if isinstance(node, Mul) and node.args[0] is S.NegativeOne:
        # Mul(-1, x) 即 -x
        output_exprs.append(node.args[1])
    else:
        output_exprs.append(node)
    return output_exprs


def get_childen_expr_key(expr, date, asset):
    """从集合中加载第一个字符串

        用于将表达式放到字典的正确位置
        """
    tup = get_childen_expr_tuple(expr, [], [], date=date, asset=asset)

    if len(tup) == 0:
        return CL,
    else:
        # TODO: 取首个是否会有问题？
        return list(tup)[0]


class ListDictList:
    """嵌套列表

    1. 最外层是 列表[]
    2. 第二层是 字典{}
    3. 第三层是 列表[]

    [
    {'ts': [1, 2], 'cs': [2], 'gp_date': [2], 'gp_key': [2], }
    {'ts': [1], 'cs': [1],}
    ]

    """

    def __init__(self):
        self._list = [{}]
        self._last_key = None

    def append(self, key, item):
        """
        1. key与上次相同时，放入同一位置的list中
        2. key与上次不同时。
            1. 当前行无同名key,放入同一行
            2. 当前行有同名key,放入下一行
        """
        last_row = self._list[-1]
        if self._last_key == key:
            # 本次添加与上次同位置，直接添加
            last_row[key].append(item)
        else:
            v = last_row.get(key, None)
            if v is None:
                # 同一行的新一列
                last_row[key] = [item]
            else:
                # 同行同列已经用过，换新行
                self._list.append({key: [item]})
            # 更新当前列名
            self._last_key = key

    def clear(self):
        self._list = [{}]

    def values(self):
        return self._list.copy()
