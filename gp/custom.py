# TODO: 请在此文件中添加算子和因子
# TODO: 由于部分算子计算过慢，这里临时屏蔽了
import random


def add_constants(pset):
    """添加常量"""
    # 名字一定不能与其它名字重，上次与int一样，结果其它地方报错 [<class 'deap.gp.random_int'>]
    pset.addEphemeralConstant('random_int', lambda: random.choice([1, 3, 5, 10, 20, 40, 60]), int)
    return pset


def add_operators(pset):
    """添加算子"""
    # IndexError: The gp.generate function tried to add a primitive of type '<class 'int'>', but there is none available.
    # https://github.com/DEAP/deap/issues/579
    # 会导致层数过多，但暂时没办法
    pset.addPrimitive(pass_through, [int], int, name='pass_int')

    # 无法给一个算子定义多种类型，只好定义多个不同名算子
    pset.addPrimitive(dummy, [float, float], float, name='fadd')
    pset.addPrimitive(dummy, [float, float], float, name='fsub')
    pset.addPrimitive(dummy, [float, float], float, name='fmul')
    pset.addPrimitive(dummy, [float, float], float, name='fdiv')

    pset.addPrimitive(dummy, [float, int], float, name='iadd')
    pset.addPrimitive(dummy, [float, int], float, name='isub')
    pset.addPrimitive(dummy, [float, int], float, name='imul')
    pset.addPrimitive(dummy, [float, int], float, name='idiv')

    # TODO: 其它算子
    pset.addPrimitive(dummy, [float], float, name='log')
    pset.addPrimitive(dummy, [float], float, name='sign')
    pset.addPrimitive(dummy, [float], float, name='abs')

    pset.addPrimitive(dummy, [float, float], float, name='max')
    pset.addPrimitive(dummy, [float, float], float, name='min')

    pset.addPrimitive(dummy, [float, int], float, name='ts_delay')
    pset.addPrimitive(dummy, [float, int], float, name='ts_delta')
    # pset.addPrimitive(dummy, [float, int], float, name='ts_arg_max')
    # pset.addPrimitive(dummy, [float, int], float, name='ts_arg_min')
    pset.addPrimitive(dummy, [float, int], float, name='ts_max')
    pset.addPrimitive(dummy, [float, int], float, name='ts_min')
    pset.addPrimitive(dummy, [float, int], float, name='ts_sum')
    pset.addPrimitive(dummy, [float, int], float, name='ts_mean')
    # pset.addPrimitive(dummy, [float, int], float, name='ts_decay_linear')
    # pset.addPrimitive(dummy, [float, int], float, name='ts_product')
    pset.addPrimitive(dummy, [float, int], float, name='ts_std_dev')
    pset.addPrimitive(dummy, [float, int], float, name='ts_rank')
    pset.addPrimitive(dummy, [float, float, int], float, name='ts_corr')
    pset.addPrimitive(dummy, [float, float, int], float, name='ts_covariance')

    pset.addPrimitive(dummy, [float], float, name='cs_rank')
    pset.addPrimitive(dummy, [float], float, name='cs_scale')

    return pset


def add_factors(pset):
    pset.addTerminal(1, float, name='OPEN')
    pset.addTerminal(1, float, name='HIGH')
    pset.addTerminal(1, float, name='LOW')
    pset.addTerminal(1, float, name='CLOSE')
    # pset.addTerminal(1, float, name='VOLUME')
    # pset.addTerminal(1, float, name='AMOUNT')

    return pset


def pass_through(x):
    # https://github.com/DEAP/deap/issues/579
    return x


def dummy(*args):
    return 1
