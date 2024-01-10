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


pset.addPrimitive(pass_through, [int], int, name='pass_int')

def pass_through(x):
    # https://github.com/DEAP/deap/issues/579
    return x

'pass_int': lambda *args_: "{}".format(*args_),
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


from deap import gp

# 给deap打补针，解决pass_int层数过多问题，deap修复后这就可以不用了
gp.generate = generate
# ============================================
"""
如果fitness返回支持nan表示无效，就会发现名人堂会插入不少nan值，并且bisect_right也乱了
所以决定开始遇到nan时就不插入

https://github.com/DEAP/deap/issues/440#issuecomment-561046939
"""
from deap.tools.support import HallOfFame


def update(self, population):
    """Update the hall of fame with the *population* by replacing the
    worst individuals in it by the best individuals present in
    *population* (if they are better). The size of the hall of fame is
    kept constant.

    :param population: A list of individual with a fitness attribute to
                       update the hall of fame with.
    """
    for ind in population:
        # 出现nan就不插入
        if ind.fitness.values[0] != ind.fitness.values[0]:
            continue
        if len(self) == 0 and self.maxsize != 0:
            # Working on an empty hall of fame is problematic for the
            # "for else"
            # 由插入第0个，改成插入当前
            self.insert(ind)
            continue
        if ind.fitness > self[-1].fitness or len(self) < self.maxsize:
            for hofer in self:
                # Loop through the hall of fame to check for any
                # similar individual
                if self.similar(ind, hofer):
                    break
            else:
                # The individual is unique and strictly better than
                # the worst
                if len(self) >= self.maxsize:
                    self.remove(-1)
                self.insert(ind)


# 打补丁，fitness为nan时不插入
HallOfFame.update = update
# ============================================
"""
在选择精英时，比如selTournament时，3选1，如[1,2, nan]，会选出nan,所以需要进行定制

https://github.com/DEAP/deap/issues/440
"""
from deap.base import Fitness


def __gt__(self, other):
    return self.wvalues > other.wvalues


def __ge__(self, other):
    return self.wvalues >= other.wvalues


# 打补丁，方便Fitness之间进行比较
Fitness.__gt__ = __gt__
Fitness.__ge__ = __ge__

# ===============================================
import numpy as np
from deap import tools
from deap.algorithms import varOr, varAnd  # noqa
from tensorboardX import SummaryWriter


def eaMuPlusLambda(population, toolbox, mu, lambda_, cxpb, mutpb, ngen,
                   stats=None, halloffame=None, verbose=__debug__,
                   early_stopping_rounds=10):
    r"""This is the :math:`(\mu + \lambda)` evolutionary algorithm.

    :param population: A list of individuals.
    :param toolbox: A :class:`~deap.base.Toolbox` that contains the evolution
                    operators.
    :param mu: The number of individuals to select for the next generation.
    :param lambda\_: The number of children to produce at each generation.
    :param cxpb: The probability that an offspring is produced by crossover.
    :param mutpb: The probability that an offspring is produced by mutation.
    :param ngen: The number of generation.
    :param stats: A :class:`~deap.tools.Statistics` object that is updated
                  inplace, optional.
    :param halloffame: A :class:`~deap.tools.HallOfFame` object that will
                       contain the best individuals, optional.
    :param verbose: Whether or not to log the statistics.
    :returns: The final population
    :returns: A class:`~deap.tools.Logbook` with the statistics of the
              evolution.

    The algorithm takes in a population and evolves it in place using the
    :func:`varOr` function. It returns the optimized population and a
    :class:`~deap.tools.Logbook` with the statistics of the evolution. The
    logbook will contain the generation number, the number of evaluations for
    each generation and the statistics if a :class:`~deap.tools.Statistics` is
    given as argument. The *cxpb* and *mutpb* arguments are passed to the
    :func:`varOr` function. The pseudocode goes as follow ::

        evaluate(population)
        for g in range(ngen):
            offspring = varOr(population, toolbox, lambda_, cxpb, mutpb)
            evaluate(offspring)
            population = select(population + offspring, mu)

    First, the individuals having an invalid fitness are evaluated. Second,
    the evolutionary loop begins by producing *lambda_* offspring from the
    population, the offspring are generated by the :func:`varOr` function. The
    offspring are then evaluated and the next generation population is
    selected from both the offspring **and** the population. Finally, when
    *ngen* generations are done, the algorithm returns a tuple with the final
    population and a :class:`~deap.tools.Logbook` of the evolution.

    This function expects :meth:`toolbox.mate`, :meth:`toolbox.mutate`,
    :meth:`toolbox.select` and :meth:`toolbox.evaluate` aliases to be
    registered in the toolbox. This algorithm uses the :func:`varOr`
    variation.
    """
    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    if halloffame is not None:
        halloffame.update(population)

    record = stats.compile(population) if stats is not None else {}

    # 新添
    writer = SummaryWriter()
    for k, v in record.items():
        for i, n in enumerate(('train', 'vaild')):
            writer.add_scalar(f'{k}/{n}', v[i], ngen)

    logbook.record(gen=0, nevals=len(invalid_ind), **record)
    if verbose:
        print(logbook.stream)

    # Begin the generational process
    for gen in range(1, ngen + 1):
        # Vary the population
        offspring = varOr(population, toolbox, lambda_, cxpb, mutpb)

        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        # Update the hall of fame with the generated individuals
        if halloffame is not None:
            halloffame.update(offspring)

        # Select the next generation population
        population[:] = toolbox.select(population + offspring, mu)

        # Update the statistics with the new population
        record = stats.compile(population) if stats is not None else {}
        for k, v in record.items():
            for i, n in enumerate(('train', 'vaild')):
                writer.add_scalar(f'{k}/{n}', v[i], gen)

        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        if verbose:
            print(logbook.stream)

        # TODO 不知写的早停算法是否合适，用户可自行修改
        avg = logbook.select('avg')
        if len(avg) > early_stopping_rounds:
            std = np.std(avg[-early_stopping_rounds:])
            if std < 0.00001:
                print(f'early_stopping_rounds={early_stopping_rounds}', '\t', std)
                break
    # 关闭
    writer.close()

    return population, logbook
