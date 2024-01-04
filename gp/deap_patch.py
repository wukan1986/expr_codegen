"""
IndexError: The gp.generate function tried to add a primitive of type '<class 'int'>', but there is none available.
https://github.com/DEAP/deap/issues/579
https://github.com/DEAP/deap/pull/737

它产生的原因是前后两个节点决定。例如:

pset.addPrimitive(func1, [pd.DataFrame, pd.DataFrame], pd.DataFrame)
pset.addPrimitive(func2, [pd.DataFrame,int], pd.DataFrame)

当前一个节点是func2(pd.DataFrame, int)时，那么第二个参数就需要返回值为int的节点，

会发现没有primitive可用，只能去找Terminal,

pset.addPrimitive(func3, [...], int)  # 需要int返回值的primitive

但genFull genGrow中的condition都没有检查有对应类型primitive可用

所以我修正为多加 `or len(pset.primitives[type_]) == 0`


其实，当选出一个算子时，表达式树的一个分支长度就已经确定了，再通过pass_int来增加长度无意义

"""
import random
import sys
from inspect import isclass


def generate(pset, min_, max_, condition, type_=None):
    """Generate a tree as a list of primitives and terminals in a depth-first
    order. The tree is built from the root to the leaves, and it stops growing
    the current branch when the *condition* is fulfilled: in which case, it
    back-tracks, then tries to grow another branch until the *condition* is
    fulfilled again, and so on. The returned list can then be passed to the
    constructor of the class *PrimitiveTree* to build an actual tree object.

    :param pset: Primitive set from which primitives are selected.
    :param min_: Minimum height of the produced trees.
    :param max_: Maximum Height of the produced trees.
    :param condition: The condition is a function that takes two arguments,
                      the height of the tree to build and the current
                      depth in the tree.
    :param type_: The type that should return the tree when called, when
                  :obj:`None` (default) the type of :pset: (pset.ret)
                  is assumed.
    :returns: A grown tree with leaves at possibly different depths
              depending on the condition function.
    """
    if type_ is None:
        type_ = pset.ret
    expr = []
    height = random.randint(min_, max_)
    stack = [(0, type_)]
    while len(stack) != 0:
        depth, type_ = stack.pop()
        if condition(height, depth) or len(pset.primitives[type_]) == 0:
            try:
                term = random.choice(pset.terminals[type_])
            except IndexError:
                _, _, traceback = sys.exc_info()
                raise IndexError("The gp.generate function tried to add "
                                 "a terminal of type '%s', but there is "
                                 "none available." % (type_,)).with_traceback(traceback)
            if isclass(term):
                term = term()
            expr.append(term)
        else:
            try:
                prim = random.choice(pset.primitives[type_])
            except IndexError:
                _, _, traceback = sys.exc_info()
                raise IndexError("The gp.generate function tried to add "
                                 "a primitive of type '%s', but there is "
                                 "none available." % (type_,)).with_traceback(traceback)
            expr.append(prim)
            for arg in reversed(prim.args):
                stack.append((depth + 1, arg))
    return expr
