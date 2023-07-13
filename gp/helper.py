import copy

import networkx as nx
import numpy as np
from deap import gp
from sympy import preorder_traversal


def convert_inverse_prim(prim, args):
    """
    Convert inverse prims according to:
    [Dd]iv(a,b) -> Mul[a, 1/b]
    [Ss]ub(a,b) -> Add[a, -b]
    We achieve this by overwriting the corresponding format method of the sub and div prim.
    """
    prim = copy.copy(prim)

    converter = {
        'fsub': lambda *args_: "Add({}, Mul(-1,{}))".format(*args_),
        'fdiv': lambda *args_: "Mul({}, Pow({}, -1))".format(*args_),
        'fmul': lambda *args_: "Mul({},{})".format(*args_),
        'fadd': lambda *args_: "Add({},{})".format(*args_),
        'fmax': lambda *args_: "max({},{})".format(*args_),
        'fmin': lambda *args_: "min({},{})".format(*args_),

        'isub': lambda *args_: "Add({}, Mul(-1,{}))".format(*args_),
        'idiv': lambda *args_: "Mul({}, Pow({}, -1))".format(*args_),
        'imul': lambda *args_: "Mul({},{})".format(*args_),
        'iadd': lambda *args_: "Add({},{})".format(*args_),
        'imax': lambda *args_: "max({},{})".format(*args_),
        'imin': lambda *args_: "min({},{})".format(*args_),

        'pass_int': lambda *args_: "{}".format(*args_),
    }
    prim_formatter = converter.get(prim.name, prim.format)

    return prim_formatter(*args)


def stringify_for_sympy(f):
    """Return the expression in a human readable string.
    """
    string = ""
    stack = []
    for node in f:
        stack.append((node, []))
        while len(stack[-1][1]) == stack[-1][0].arity:
            prim, args = stack.pop()
            string = convert_inverse_prim(prim, args)
            if len(stack) == 0:
                break  # If stack is empty, all nodes should have been seen
            stack[-1][1].append(string)
    return string


def invalid_atom_infinite(e):
    """无效。单元素。无穷大或无穷小"""
    # 根是单元素，直接返回
    if e.is_Atom:
        return True
    # 有无限值
    for node in preorder_traversal(e):
        if node.is_infinite:
            return True
    return False


def invalid_number_type(e, pset):
    """检查参数类型"""
    # 可能导致结果为1，然后当成float去别处计算
    for node in preorder_traversal(e):
        if not node.is_Function:
            continue
        prim = pset.mapping.get(node.name, None)
        if prim is None:
            continue
        for i, arg in enumerate(prim.args):
            if issubclass(arg, np.ndarray):
                if node.args[i].is_Number:
                    return True
            elif issubclass(arg, int):
                # 应当是整数，结果却是浮点
                if node.args[i].is_Float:
                    return True
            elif issubclass(arg, float):
                pass
    return False


def draw_deap_expr(expr):
    """根据DEAP版表达式画图"""
    nodes, edges, labels = gp.graph(expr)
    edges = [(edge[1], edge[0]) for edge in edges]

    G = nx.DiGraph()
    G.add_edges_from(edges)
    nx.draw(G, labels=labels)
