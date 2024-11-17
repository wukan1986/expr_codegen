"""
A、B、C=MACD()无法生成DAG，所以变通的改成

A=unpack(MACD(),0)
B=unpack(MACD(),1)
C=unpack(MACD(),2)

cse能自动提取成

_x_0 = MACD()

但 df['_x_0'] 是无法放入tuple的，所以决定用另一个类来实现兼容

"""
import pandas as pd


class GlobalVariable(object):
    def __init__(self):
        self.dict = {}
        self.df = pd.DataFrame()

    def __getitem__(self, item):
        if item in self.dict:
            return self.dict[item]
        return self.df[item]

    def __setitem__(self, key, value):
        if isinstance(value, tuple):
            # tuple存字典中
            self.dict[key] = value
            # 占位，避免drop时报错
            self.df[key] = False
        else:
            self.df[key] = value
