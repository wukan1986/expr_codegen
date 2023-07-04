import re
from functools import reduce

from sympy import Mul, preorder_traversal, symbols, Function

# 预定义前缀，算子用前缀进行区分更方便。
# 当然也可以用是否在某容器中进行分类
CL = 'cl'  # 列算子, column
TS = 'ts'  # 时序算子, time-series
CS = 'cs'  # 横截面算子 cross section
GP = 'gp'  # 分组算子。group 分组越小，速度越慢

CL_TUP = (CL,)  # 整列元组
CL_SET = set([CL_TUP])  # 整列集合


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


def get_current_by_prefix(expr, date, asset, **kwargs):
    """表达式根节点信息。按名称前缀。例如

    OPEN取的是OPEN，得cl
    ts_mean取的ts_mean,得ts
    -ts_mean取的是-,得cl
    """
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
    return CL_TUP


def get_current_by_name(expr, date, asset, ts_names, cs_names, gp_names, **kwargs):
    """表达式根节点信息。按名称。

    Parameters
    ----------
    ts_names
        时序算子名称字符串集合
    cs_names
        横截面算子名称字符串集合
    gp_names
        分组算子名称字符串集合
    kwargs

    """
    if expr.is_Function:
        if hasattr(expr, 'name'):  # Or 没有名字
            if expr.name in ts_names:
                return TS, asset, date
            if expr.name in cs_names:
                return CS, date
            if expr.name in gp_names:
                return GP, date, expr.args[0].name

    # 不需分组
    return CL_TUP


# 调试用，勿删
# __level__ = 0


def get_children(func, func_kwargs, expr, output_exprs, output_symbols, date, asset):
    """表达式整体信息。例如

    -ts_corr返回{ts}而不是 {cl}
    -ts_corr+cs_rank返回{ts,cs}
    -OPEN-CLOSE返回{cl}

    Parameters
    ----------
    func
        表达式根分类函数
    func_kwargs
        func对应的参数字典
    expr
        表达式
    output_exprs
        输出分割后的了表达式
    output_symbols
        输出每个子表达式中的符号
    date
        分组用的日期字段名
    asset
        分组用的资产字段名

    Returns
    -------

    """
    # global __level__
    # __level__ += 1

    try:
        curr = func(expr, date, asset, **func_kwargs)
        children = [get_children(func, func_kwargs, a, output_exprs, output_symbols, date, asset) for a in expr.args]

        # print(expr, curr, children)
        # if __level__ == 1:
        #     print(expr, curr, children)

        # 多个集合合成一个去重
        unique = reduce(lambda x, y: x | y, children, set()) - CL_SET

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


def get_key(children):
    """!!!此函数只能在先抽取出子表达式后再cse，然后才能调用。否则报错。

    为了保证expr能正确分组，只有一种分法

    Parameters
    ----------


    Returns
    -------
    用于字典的键

    """
    if len(children) == 0:
        # OPEN等因子会走这一步
        return CL_TUP
    elif len(children) == 1:
        # 只有一种分法，最合适的方法
        return list(children)[0]
    else:
        assert False, f'{children} 无法正确分类，之前没有分清'


def ts_sum__to__ts_mean(e):
    """将ts_sum(x, y)/y 转成 ts_mean(x, y)"""
    # TODO: 这里重新定义的ts_mean与外部已经定义好的是否同一个？
    ts_mean = symbols('ts_mean', cls=Function)

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
