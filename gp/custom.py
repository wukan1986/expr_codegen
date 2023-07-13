# TODO: 请在此文件中添加算子和因子
# TODO: 由于部分算子计算过慢，这里临时屏蔽了
import random

import numpy as np


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
    pset.addPrimitive(dummy, [np.ndarray, np.ndarray], np.ndarray, name='fadd')
    pset.addPrimitive(dummy, [np.ndarray, np.ndarray], np.ndarray, name='fsub')
    pset.addPrimitive(dummy, [np.ndarray, np.ndarray], np.ndarray, name='fmul')
    pset.addPrimitive(dummy, [np.ndarray, np.ndarray], np.ndarray, name='fdiv')
    pset.addPrimitive(dummy, [np.ndarray, np.ndarray], np.ndarray, name='fmax')
    pset.addPrimitive(dummy, [np.ndarray, np.ndarray], np.ndarray, name='fmin')

    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='iadd')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='isub')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='imul')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='idiv')
    # !!!max(x,1)这类表达式是合法的，但生成数量太多价值就低了，所以屏蔽
    # pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='imax')
    # pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='imin')

    # TODO: 其它算子
    pset.addPrimitive(dummy, [np.ndarray], np.ndarray, name='log')
    pset.addPrimitive(dummy, [np.ndarray], np.ndarray, name='sign')
    pset.addPrimitive(dummy, [np.ndarray], np.ndarray, name='abs')

    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_delay')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_delta')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_arg_max')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_arg_min')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_max')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_min')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_sum')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_mean')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_decay_linear')
    # pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_product')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_std_dev')
    pset.addPrimitive(dummy, [np.ndarray, int], np.ndarray, name='ts_rank')
    # pset.addPrimitive(dummy, [np.ndarray, np.ndarray, int], np.ndarray, name='ts_corr')
    # pset.addPrimitive(dummy, [np.ndarray, np.ndarray, int], np.ndarray, name='ts_covariance')

    pset.addPrimitive(dummy, [np.ndarray], np.ndarray, name='cs_rank')
    pset.addPrimitive(dummy, [np.ndarray], np.ndarray, name='cs_scale')

    return pset


def add_factors(pset):
    pset.addTerminal(1, np.ndarray, name='OPEN')
    pset.addTerminal(1, np.ndarray, name='HIGH')
    pset.addTerminal(1, np.ndarray, name='LOW')
    pset.addTerminal(1, np.ndarray, name='CLOSE')
    # pset.addTerminal(1, np.ndarray, name='VOLUME')
    # pset.addTerminal(1, np.ndarray, name='AMOUNT')

    return pset


def pass_through(x):
    # https://github.com/DEAP/deap/issues/579
    return x


def dummy(*args):
    return 1
