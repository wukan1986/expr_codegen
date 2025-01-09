"""
分钟线处理示例

在分钟线预处理时常常需要按天分别处理。例如ts_delay如果是对多天分钟数据处理，只有第一天第一条为null,
如果是对每天分钟数据处理，每天第一条为null,

在日线时，默认date参数的freq是1d，asset参数是股票代码
在按日划分的分钟时，默认date参数的freq是1min，asset参数是股票代码+日，这样才能每天独立处理

如果分钟数据已经按日期分好了文件，也可以直接多进程并行处理，就没这么麻烦

"""
from datetime import datetime

import numpy as np
import pandas as pd
import polars as pl
from loguru import logger

from expr_codegen import codegen_exec  # noqa

np.random.seed(42)

ASSET_COUNT = 500
DATE_COUNT = 250 * 24 * 10 * 1
DATE = pd.date_range(datetime(2020, 1, 1), periods=DATE_COUNT, freq='1min').repeat(ASSET_COUNT)
ASSET = [f'A{i:04d}' for i in range(ASSET_COUNT)] * DATE_COUNT

df = pl.DataFrame(
    {
        'datetime': DATE,
        'asset': ASSET,
        "OPEN": np.random.rand(DATE_COUNT * ASSET_COUNT),
        "HIGH": np.random.rand(DATE_COUNT * ASSET_COUNT),
        "LOW": np.random.rand(DATE_COUNT * ASSET_COUNT),
        "CLOSE": np.random.rand(DATE_COUNT * ASSET_COUNT),
        "VOLUME": np.random.rand(DATE_COUNT * ASSET_COUNT),
        "OPEN_INTEREST": np.random.rand(DATE_COUNT * ASSET_COUNT),
        "FILTER": np.tri(DATE_COUNT, ASSET_COUNT, k=-2).reshape(-1),
    }
).lazy()

df = df.filter(pl.col('FILTER') == 1)

logger.info('时间戳调整开始')
# 交易日，期货夜盘属于下一个交易日，后移4小时夜盘日期就一样了
df = df.with_columns(trading_day=pl.col('datetime').dt.offset_by("4h"))
# 周五晚已经变成了周六，双休要移动到周一
df = df.with_columns(trading_day=pl.when(pl.col('trading_day').dt.weekday() > 5)
                     .then(pl.col("trading_day").dt.offset_by("2d"))
                     .otherwise(pl.col("trading_day")))
df = df.with_columns(
    # 交易日
    trading_day=pl.col("trading_day").dt.date(),
    # 工作日
    action_day=pl.col('datetime').dt.date(),
)
df = df.collect()
logger.info('时间戳调整完成')
# ---
# !!! 重要代码，生成复合字段，用来ts_排序
# _asset_date以下划线开头，会自动删除，如要保留，可去了下划线
# 股票用action_day，期货用trading_day
df = df.with_columns(_asset_date=pl.struct("asset", "trading_day"))
df = codegen_exec(df, """OPEN_RANK = cs_rank(OPEN[1]) # 仅演示""",
                  # !!!使用时一定要分清分组是用哪个字段
                  date='datetime', asset='_asset_date')
# ---
logger.info('1分钟转15分钟线开始')
df1 = df.sort('asset', 'datetime').group_by_dynamic('datetime', every="15m", closed='left', label="left", group_by=['asset', 'trading_day']).agg(
    open_dt=pl.first("datetime"),
    close_dt=pl.last("datetime"),
    OPEN=pl.first("OPEN"),
    HIGH=pl.max("HIGH"),
    LOW=pl.min("LOW"),
    CLOSE=pl.last("CLOSE"),
    VOLUME=pl.sum("VOLUME"),
    OPEN_INTEREST=pl.last("OPEN_INTEREST"),
)
logger.info('1分钟转15分钟线结束')
print(df1)
# ---
logger.info('1分钟转日线开始')
# 也可以使用group_by_dynamic，只是日线隐含了label="left"
df1 = df.sort('asset', 'datetime').group_by('asset', 'trading_day', maintain_order=True).agg(
    open_dt=pl.first("datetime"),
    close_dt=pl.last("datetime"),
    OPEN=pl.first("OPEN"),
    HIGH=pl.max("HIGH"),
    LOW=pl.min("LOW"),
    CLOSE=pl.last("CLOSE"),
    VOLUME=pl.sum("VOLUME"),
    OPEN_INTEREST=pl.last("OPEN_INTEREST"),
)
logger.info('1分钟转日线结束')
print(df1)
