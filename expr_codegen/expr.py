import re
from functools import reduce

from sympy import Mul, preorder_traversal

# 预定义前缀，算子用前缀进行区分更方便。
# 当然也可以用是否在某容器中进行分类
CL = 'cl'  # 列算子
TS = 'ts'  # 时序算子
CS = 'cs'  # 横截面算子
GP = 'gp'  # 分组算子。分组越小，速度越慢


def append_node(node, output_exprs):
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
    if isinstance(node, Mul):
        if node.args[0] == -1 or node.args[0] == 1:
            # 可能是-1也可能是1.0
            for arg in node.args[1:]:
                if arg.is_Atom:
                    continue
                output_exprs.append(arg)
                # print(1, arg)
        else:
            output_exprs.append(node)
            # print(2, node)
    else:
        output_exprs.append(node)
        # print(3, node)

    return output_exprs


def get_symbols(expr, syms=None, return_str=True):
    """得到"""
    if syms is None:
        syms = []

    for arg in expr.args:
        if arg.is_Symbol:
            if return_str:
                syms.append(arg.name)
            else:
                syms.append(arg)
        else:
            get_symbols(arg, syms, return_str)
    return syms


def is_NegativeX(expr):
    """-x, 但-ts_sum格式不返回False"""
    if isinstance(expr, Mul):
        if expr.args[0] == -1 and len(expr.args) == 2 and expr.args[1].is_Atom:
            return True
    return False


def get_current_by_prefix(expr, date, asset, *args, **kwargs):
    if expr.is_Function:
        if hasattr(expr, 'name'):  # Or 没有名字
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


def get_current_by_name(expr, date, asset, ts_names, cs_names, gp_names, *args, **kwargs):
    if expr.is_Function:
        if hasattr(expr, 'name'):  # Or 没有名字
            if expr.name in ts_names:
                return TS, asset, date
            if expr.name in cs_names:
                return CS, date
            if expr.name in gp_names:
                return GP, date, expr.args[0].name

    # 不需分组
    return CL,


# __level__ = 0


def get_children(func, config, expr, output_exprs, output_symbols, date, asset):
    # global __level__
    # __level__ += 1

    try:
        curr = func(expr, date, asset, **config)
        children = [get_children(func, config, a, output_exprs, output_symbols, date, asset) for a in expr.args]

        # if __level__ == 1:
        #     print(expr, curr, children)

        # 多个集合合成一个去重
        unique = reduce(lambda x, y: x | y, children, set())

        if len(unique) >= 2:
            # 大于1，表示内部不统一，内部都要处理
            for i, child in enumerate(children):
                # alpha_047无法正确输出
                if expr.args[i].is_Atom:
                    # print(expr.args[i], 'is_Atom 1')
                    continue
                output_exprs = append_node(expr.args[i], output_exprs)
        elif curr[0] != CL:
            # 外部与内部不同，需处理
            for i, child in enumerate(children):
                # 不在子中即表示不同
                if curr in child:
                    continue
                if expr.args[i].is_Atom:
                    # print(expr.args[i], 'is_Atom 2')
                    continue
                output_exprs = append_node(expr.args[i], output_exprs)

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
    finally:
        # __level__ -= 1
        pass


def get_key(func, config, expr, date, asset):
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
    tup = get_children(func, config, expr, [], [], date=date, asset=asset)

    if len(tup) == 0:
        return CL,
    else:
        # TODO: 取首个是否会有问题？
        return list(tup)[0]


def ts_sum__to__ts_mean(e, ts_mean):
    """将ts_sum(x, y)/y 转成 ts_mean(x, y)"""
    replacements = []
    for node in preorder_traversal(e):
        if node.is_Mul and node.args[0].is_Rational and node.args[1].is_Function:
            if node.args[1].name == 'ts_sum':
                if node.args[1].args[1] == node.args[0].q and node.args[0].p == 1:
                    replacements.append((node, ts_mean(node.args[1].args[0], node.args[1].args[1])))
    for node, replacement in replacements:
        print(node, '  ->  ', replacement)
        e = e.xreplace({node: replacement})
    return e


def cs_rank__drop_duplicates(e):
    """cs_rank(cs_rank(x)) 转成 cs_rank(x)"""
    replacements = []
    for node in preorder_traversal(e):
        # print(node)
        if hasattr(node, 'name') and node.name == 'cs_rank':
            if hasattr(node.args[0], 'name') and node.args[0].name == 'cs_rank':
                replacements.append((node, node.args[0]))
    for node, replacement in replacements:
        print(node, '  ->  ', replacement)
        e = e.xreplace({node: replacement})
    return e


def mul_one(e):
    """1.0*VWAP转成VWAP"""
    replacements = []
    for node in preorder_traversal(e):
        # print(node)
        if isinstance(node, Mul) and node.args[0] == 1:
            if len(node.args) > 2:
                replacements.append((node, Mul._from_args(node.args[1:])))
            else:
                replacements.append((node, node.args[1]))
    for node, replacement in replacements:
        print(node, '  ->  ', replacement)
        e = e.xreplace({node: replacement})
    return e


def safe_eval(string, dict):
    code = compile(string, '<user input>', 'eval')
    reason = None
    banned = ('eval', 'compile', 'exec', 'getattr', 'hasattr', 'setattr', 'delattr',
              'classmethod', 'globals', 'help', 'input', 'isinstance', 'issubclass', 'locals',
              'open', 'print', 'property', 'staticmethod', 'vars')
    for name in code.co_names:
        if re.search(r'^__\S*__$', name):
            reason = 'attributes not allowed'
        elif name in banned:
            reason = 'code execution not allowed'
        if reason:
            raise NameError(f'{name} not allowed : {reason}')
    return eval(code, dict)
