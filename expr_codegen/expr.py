from functools import reduce

from sympy import Mul, preorder_traversal, symbols, Function, simplify, Add, Basic, Symbol, sympify, FunctionClass

# 预定义前缀，算子用前缀进行区分更方便。
# 当然也可以用是否在某容器中进行分类
CL = 'cl'  # 列算子, column
TS = 'ts'  # 时序算子, time-series
CS = 'cs'  # 横截面算子 cross section
GP = 'gp'  # 分组算子。group 分组越小，速度越慢

CL_TUP = (CL,)  # 整列元组
CL_SET = {CL_TUP}  # 整列集合


def is_symbol(x, globals_):
    s = globals_.get(x, None)
    if s is None:
        return False
    if isinstance(s, Symbol):
        # OPEN
        return True
    if type(s) is type:
        # Eq
        return issubclass(s, Basic)
    if isinstance(s, FunctionClass):
        # Not
        return True
    return False


def register_symbols(syms, globals_, is_function: bool):
    """注册sympy中需要使用的符号"""
    # Eq等已经是sympy的符号不需注册
    syms = [s for s in syms if not is_symbol(s, globals_)]
    if len(syms) == 0:
        return globals_

    if is_function:
        # 函数被注册后不能再调用，所以一定要用globals().copy()
        syms = symbols(','.join(syms), cls=Function, seq=True)
    else:
        syms = symbols(','.join(syms), cls=Symbol, seq=True)
    syms = {s.name: s for s in syms}
    globals_.update(syms)
    return globals_


def list_to_exprs(exprs_src, globals_):
    return [(k, sympify(v, globals_, evaluate=False), c) for k, v, c in exprs_src]


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
        elif arg.is_Number:
            # alpha_001 = log(1)+1
            if return_str:
                syms.append(str(arg))
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


def is_simple_expr(expr):
    if isinstance(expr, Mul):
        if expr.args[0] == -1 and len(expr.args) == 2 and expr.args[1].is_Atom:
            return True
    if isinstance(expr, Symbol):
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
                    return TS, asset
                if prefix2 == CS:
                    return CS, date
                if prefix2 == GP:
                    return GP, date, expr.args[0].name
    # 不需分组
    return CL_TUP


def get_current_by_name(expr, ts_names, cs_names, gp_names, date, asset, **kwargs):
    """表达式根节点信息。按名称。

    Parameters
    ----------
    expr
    ts_names
        时序算子名称字符串集合
    cs_names
        横截面算子名称字符串集合
    gp_names
        分组算子名称字符串集合
    date
        日期字符串
    asset
        资产字符串
    kwargs

    """
    if expr.is_Function:
        if hasattr(expr, 'name'):  # Or 没有名字
            if expr.name in ts_names:
                return TS, asset
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
    asset

    Returns
    -------

    """
    # global __level__
    # __level__ += 1

    try:
        curr = func(expr, date, asset, **func_kwargs)
        children = [get_children(func, func_kwargs, a, output_exprs, output_symbols, date, asset) for a in expr.args]

        # print(expr, curr, children, __level__)
        # if __level__ == 6:
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
        else:
            # ts_sum(OPEN, 5)*ts_sum(RETURNS, 5) ('cl',) [{('ts', 'asset', 'date')}, {('ts', 'asset', 'date')}] 6 alpha_008
            pass
            # if isinstance(expr, Mul):
            #     output_exprs = append_node(expr, output_exprs)

        # 按需返回，当前是基础算子就返回下一层信息，否则返回当前
        if curr[0] == CL:
            if expr.is_Symbol:
                # 汇总符号列表
                output_symbols.append(expr)
            # 返回子中出现过的集合{ts cs gp}
            return unique
        else:
            # 当前算子，非列算子，直接返回，如{ts} {cs} {gp}
            return {curr}
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


def replace_exprs(exprs):
    """使用替换的方式简化表达式"""
    # Alpha101中大量ts_sum(x, 10)/10, 转成ts_mean(x, 10)
    exprs = [(k, _replace__ts_sum__to__ts_mean(v), c) for k, v, c in exprs]
    # alpha_031中大量cs_rank(cs_rank(x)) 转成cs_rank(x)
    exprs = [(k, _replace__repeat(v), c) for k, v, c in exprs]
    # 1.0*VWAP转VWAP
    exprs = [(k, _replace__one_mul(v), c) for k, v, c in exprs]
    # 将部分参数为1的ts函数进行简化
    exprs = [(k, _replace__ts_xxx_1(v), c) for k, v, c in exprs]
    # ts_delay转成ts_delta
    exprs = [(k, _replace__ts_delay__to__ts_delta(v), c) for k, v, c in exprs]

    return exprs


def get_node_name(node):
    """得到节点名"""
    if hasattr(node, 'name'):
        # 如 ts_arg_max
        node_name = node.name
    else:
        # 如 log
        node_name = str(node.func)
    return node_name


def _replace__ts_sum__to__ts_mean(e):
    """将ts_sum(x, y)/y 转成 ts_mean(x, y)"""
    if not isinstance(e, Basic):
        return e

    # TODO: 这里重新定义的ts_mean与外部已经定义好的是否同一个？
    ts_mean = symbols('ts_mean', cls=Function)

    replacements = []
    for node in preorder_traversal(e):
        if node.is_Mul and node.args[0].is_Rational and node.args[1].is_Function:
            node_name = get_node_name(node.args[1])
            if node_name == 'ts_sum':
                if node.args[1].args[1] == node.args[0].q and node.args[0].p == 1:
                    replacements.append((node, ts_mean(node.args[1].args[0], node.args[1].args[1])))
    for node, replacement in replacements:
        print(node, '  ->  ', replacement)
        e = e.xreplace({node: replacement})
    return e


def _replace__repeat(e):
    """cs_rank(cs_rank(x)) 转成 cs_rank(x)
    sign(sign(x)) 转成 sign(x)
    Abs(Abs(x)) 转成 Abs(x)
    """
    if not isinstance(e, Basic):
        return e

    replacements = []
    for node in preorder_traversal(e):
        # print(node)
        if len(node.args) == 0:
            continue
        node_name = get_node_name(node)
        node_args0_name = get_node_name(node.args[0])
        if node_name == node_args0_name:
            if node_name in ('cs_rank', 'sign', 'Abs', 'abs_'):
                replacements.append((node, node.args[0]))
    for node, replacement in replacements:
        print(node, '  ->  ', replacement)
        e = e.xreplace({node: replacement})
    return e


def _replace__one_mul(e):
    """1.0*VWAP转成VWAP"""
    if not isinstance(e, Basic):
        return e

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


def _replace__ts_xxx_1(e):
    """ts_xxx部分函数如果参数为1，可直接丢弃"""
    if not isinstance(e, Basic):
        return e

    replacements = []
    for node in preorder_traversal(e):
        node_name = get_node_name(node)
        if node_name in ('ts_mean', 'ts_sum', 'ts_decay_linear',
                         'ts_max', 'ts_min', 'ts_arg_max', 'ts_arg_min',
                         'ts_product', 'ts_std_dev', 'ts_rank'):
            try:
                if node.args[1] <= 1:
                    replacements.append((node, node.args[0]))
            except:
                print(node_name)
                print(e)
                raise
    for node, replacement in replacements:
        print(node, '  ->  ', replacement)
        e = e.xreplace({node: replacement})
    return e


def _replace__ts_delay__to__ts_delta(e):
    """ 将-ts_delay(x, y)转成ts_delta(x, y)-x

    本质上为x-ts_delay(x, y) 转成 ts_delta(x, y)

    例如 OPEN - ts_delay(OPEN, 5) + (CLOSE - ts_delay(CLOSE, 5))
    结果 ts_delta(CLOSE, 5) + ts_delta(OPEN, 5)
    """
    if not isinstance(e, Basic):
        return e

    ts_delta = symbols('ts_delta', cls=Function)

    replacements = []
    for node in preorder_traversal(e):
        if node.is_Add:
            new_args = []
            for arg in node.args:
                if arg.is_Mul:
                    if arg.args[0] == -1 and arg.args[1].is_Function and get_node_name(arg.args[1]) == 'ts_delay':
                        # 添加ts_delta(x, y)
                        new_args.append(ts_delta(arg.args[1].args[0], arg.args[1].args[1]))
                        # 添加-x
                        new_args.append(-arg.args[1].args[0])
                    else:
                        new_args.append(arg)
                else:
                    new_args.append(arg)
            if len(new_args) > len(node.args):
                # 长度变长，表示成功实现了调整
                tmp_args = simplify(Add._from_args(new_args))
                # 优化后长度变短，表示有变量对冲掉了，成功
                if len(tmp_args.args) < len(new_args):
                    replacements.append((node, tmp_args))
    for node, replacement in replacements:
        print(node, '  ->  ', replacement)
        e = e.xreplace({node: replacement})
    return e

# def is_meaningless(e):
#     if _meaningless__ts_xxx_1(e):
#         return True
#     if _meaningless__xx_xx(e):
#         return True
#     return False
#
#
# def _meaningless__ts_xxx_1(e):
#     """ts_xxx部分函数如果参数为1，可直接丢弃"""
#     for node in preorder_traversal(e):
#         if len(node.args) >= 2:
#             node_name = get_node_name(node)
#             if node_name in ('ts_delay', 'ts_delta'):
#                 if not node.args[1].is_Integer:
#                     return True
#             if node_name.startswith('ts_'):
#                 if not node.args[-1].is_Number:
#                     return True
#                 if node.args[-1] <= 1:
#                     return True
#     return False
#
#
# def _meaningless__xx_xx(e):
#     """部分函数如果两参数完全一样，可直接丢弃"""
#     for node in preorder_traversal(e):
#         if len(node.args) >= 2:
#             if node.args[0] == node.args[1]:
#                 return True
#     return False
