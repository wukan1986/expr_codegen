"""尝试套通达信风格指数"""
import os
import sys
import time
from pathlib import Path

# 修改当前目录到上层目录，方便跨不同IDE中使用
pwd = str(Path(__file__).parents[1])
os.chdir(pwd)
sys.path.append(pwd)
print("pwd:", os.getcwd())
# ====================
import polars as pl
from expr_codegen.tool import codegen_exec
from loguru import logger
from polars_ta.prefix.wq import *


def _code_block_1():
    # 基础字段准备===================
    涨跌幅 = CLOSE / CLOSE[1] - 1
    振幅 = (HIGH - LOW) / CLOSE[1]

    开盘涨停 = open >= high_limit - 0.001
    最高涨停 = high >= high_limit - 0.001
    一字涨停 = low >= high_limit - 0.001
    收盘涨停 = close >= high_limit - 0.001

    开盘跌停 = open <= low_limit + 0.001
    一字跌停 = high <= low_limit + 0.001
    最低跌停 = low <= low_limit + 0.001
    收盘跌停 = close <= low_limit + 0.001

    连板天数 = ts_cum_sum_reset(收盘涨停)
    涨停T天, 涨停N板, _ = ts_up_stat(收盘涨停)


def _code_block_2():
    # 通达信风格板块===================
    _昨日强势1 = (0.07 < 涨跌幅) & (涨跌幅 < 0.1) & (上海主板 | 深圳主板)
    _昨日强势2 = (0.14 < 涨跌幅) & (涨跌幅 < 0.2) & (创业板 | 科创板)
    _昨日强势3 = (0.21 < 涨跌幅) & (涨跌幅 < 0.3) & 北交所
    昨日强势 = _昨日强势1 | _昨日强势2 | _昨日强势3
    _昨日弱势1 = (-0.1 < 涨跌幅) & (涨跌幅 < -0.07) & (上海主板 | 深圳主板)
    _昨日弱势2 = (-0.2 < 涨跌幅) & (涨跌幅 < -0.14) & (创业板 | 科创板)
    _昨日弱势3 = (-0.3 < 涨跌幅) & (涨跌幅 < -0.21) & 北交所
    昨日弱势 = _昨日弱势1 | _昨日弱势2 | _昨日弱势3
    _昨日较弱1 = (-0.07 <= 涨跌幅) & (涨跌幅 <= -0.05) & (上海主板 | 深圳主板)
    _昨日较弱2 = (-0.14 <= 涨跌幅) & (涨跌幅 <= -0.10) & (创业板 | 科创板)
    _昨日较弱3 = (-0.21 <= 涨跌幅) & (涨跌幅 <= -0.15) & 北交所
    昨日较弱 = _昨日较弱1 | _昨日较弱2 | _昨日较弱3
    _昨日较强1 = (0.05 <= 涨跌幅) & (涨跌幅 <= 0.07) & (上海主板 | 深圳主板)
    _昨日较强2 = (0.10 <= 涨跌幅) & (涨跌幅 <= 0.14) & (创业板 | 科创板)
    _昨日较强3 = (0.15 <= 涨跌幅) & (涨跌幅 <= 0.21) & 北交所
    昨日较强 = _昨日较强1 | _昨日较强2 | _昨日较强3
    _最近异动1 = (ts_sum(turnover_ratio, 3) > 25) & (ts_mean(振幅, 3) > 0.07) & ~(创业板 | 科创板)
    _最近异动2 = (ts_sum(turnover_ratio, 3) > 50) & (ts_mean(振幅, 3) > 0.14) & (创业板 | 科创板)
    最近异动 = _最近异动1 | _最近异动2
    _昨高换手1 = (turnover_ratio > 15) & ~科创板
    _昨高换手2 = (turnover_ratio > 30) & 科创板
    昨高换手 = _昨高换手1 | _昨高换手2
    近期强势 = (ts_returns(CLOSE, 20) >= 0.3) & (ts_returns(CLOSE, 3) > 0)
    近期弱势 = (ts_returns(CLOSE, 20) <= -0.2) & (ts_returns(CLOSE, 3) < 0)
    # ===================
    最近情绪 = ts_count(收盘涨停 | 收盘跌停, 5) > 0
    昨日跌停 = 收盘跌停
    昨曾跌停 = 最低跌停 & ~收盘跌停
    昨日首板 = 连板天数 == 1
    最近多板 = 涨停N板 >= 2
    昨日连板 = 连板天数 >= 2
    昨日涨停 = 收盘涨停
    昨曾涨停 = 最高涨停 & ~收盘涨停

    昨成交20 = cs_rank(-amount, False) <= 20
    大盘股 = cs_rank(-market_cap, False) <= 200
    微盘股 = cs_rank(market_cap, False) <= 400
    高市盈率 = cs_rank(-pe_ratio, False) <= 200
    低市盈率 = cs_rank(pe_ratio, False) <= 200
    高市净率 = cs_rank(-pb_ratio, False) <= 200
    低市净率 = cs_rank(pb_ratio, False) <= 200
    活跃股 = cs_rank(-ts_sum(turnover_ratio, 5)) <= 100
    不活跃股 = ts_sum(turnover_ratio, 5) < 20
    昨日振荡 = (振幅 > 0.08) & (LOW < CLOSE[1]) & (HIGH > CLOSE[1])
    近期新高 = ts_max(HIGH, 3) == ts_max(HIGH, 250)
    近期新低 = ts_min(LOW, 3) == ts_max(LOW, 250)
    百元股 = (ts_max(high, 5) > 100) & (close[1] > 90)
    低价股 = close <= 3


# 由于读写多，推荐放到内存盘，加快速度
PATH_INPUT1 = r'M:\preprocessing\data2.parquet'
# 去除停牌后的基础数据
PATH_OUTPUT = r'M:\preprocessing\out1.parquet'

if __name__ == '__main__':
    logger.info('数据准备开始')
    df = pl.read_parquet(PATH_INPUT1)

    logger.info('数据准备完成')
    # =====================================
    logger.info('计算开始')
    t1 = time.perf_counter()
    df = codegen_exec(df, _code_block_1, _code_block_2)
    t2 = time.perf_counter()
    print(t2 - t1)
    logger.info('计算结束')
    df = df.filter(
        ~pl.col('is_st'),
    )
    print(df)
