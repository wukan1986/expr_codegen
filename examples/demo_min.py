"""
分钟线处理示例

在分钟线预处理时常常需要按天分别处理。例如ts_delay如果是对多天分钟数据处理，只有第一天第一条为null,
如果是对每天分钟数据处理，每天第一条为null,

在日线时，默认date参数的freq是1d，asset参数是股票代码
在按日划分的分钟时，默认date参数的freq是1min，asset参数是股票代码+日，这样才能每天独立处理

如果分钟数据已经按日期分好了文件，也可以直接多进程并行处理，就没这么麻烦

"""
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import polars as pl

from expr_codegen.tool import codegen_exec

np.random.seed(42)

ASSET_COUNT = 500
DATE_COUNT = 250 * 20
DATE = pd.date_range(datetime(2020, 1, 1), periods=DATE_COUNT, freq='2h').repeat(ASSET_COUNT)
ASSET = [f'A{i:04d}' for i in range(ASSET_COUNT)] * DATE_COUNT

df = pl.DataFrame(
    {
        'datetime': DATE,
        'asset': ASSET,
        "OPEN": np.random.rand(DATE_COUNT * ASSET_COUNT),
        "FILTER": np.tri(DATE_COUNT, ASSET_COUNT, k=-2).reshape(-1),
    }
)
df = df.filter(pl.col('FILTER') == 1)

# 交易日，期货夜盘属于下一个交易日，后移4小时夜盘日期就一样了
df = df.with_columns(trading_day=pl.col('datetime').dt.offset_by("4h"))
# 周五晚已经变成了周六，双修要移动到周一
df = df.with_columns(trading_day=pl.when(pl.col('trading_day').dt.weekday() > 5)
                     .then(pl.col("trading_day").dt.offset_by("2d"))
                     .otherwise(pl.col("trading_day")))
df = df.with_columns(
    # 交易日
    trading_day=pl.col("trading_day").dt.truncate("1d"),
    # 工作日
    action_day=pl.col('datetime').dt.truncate('1d'),
)


def _code_block_1():
    OPEN_1 = ts_delay(OPEN, 1)
    OPEN_RANK = cs_rank(OPEN_1)


# !!! 重要代码，生成复合字段，用来ts_排序
# _asset_date以下划线开头，会自动删除，如要保留，可去了下划线
# 股票用action_day，期货用trading_day
df = df.with_columns(_asset_date=pl.struct("asset", "trading_day"))
print(df.tail(5))
df = codegen_exec(df, _code_block_1, output_file=sys.stdout,  # 打印代码
                  # !!!使用时一定要分清分组是用哪个字段
                  date='datetime', asset='_asset_date')
# 演示中间某天的数据
df = df.filter(pl.col('asset') == 'A0000', pl.col('trading_day') == pl.datetime(2020, 1, 6))

print(df)
# df.write_csv('output.csv')
