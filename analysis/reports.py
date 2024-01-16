import os
from typing import Sequence

import polars as pl
from matplotlib import pyplot as plt

from analysis.ic import calc_ic, plot_ic_ts, plot_ic_hist, plot_ic_heatmap
from analysis.portfolio import calc_return_by_quantile, plot_quantile_portfolio, calc_cum_return_by_quantile
from analysis.turnover import calc_auto_correlation, calc_quantile_turnover, plot_factor_auto_correlation, plot_turnover_quantile


def ipynb_to_html(template: str, output: str = None,
                  no_input: bool = False, no_prompt: bool = False, execute: bool = True,
                  timeout: int = 120,
                  open_browser: bool = True,
                  **kwargs) -> int:
    """将`ipynb`导出成`HTML`格式

    Parameters
    ----------
    template
    output
    no_input: bool
        无输入
    no_prompt: bool
        无提示
    execute: bool
        是否执行
    timeout: int
        执行超时
    open_browser: bool
        是否打开浏览器
    kwargs: dict
        环境变量。最终转成大写，所以与前面的参数不会冲突

    """
    template = str(template)
    if not template.endswith('.ipynb'):
        raise ValueError('template must be a ipynb file')

    if output is None:
        output = template.replace('.ipynb', '.html')

    no_input = '--no-input' if no_input else ''
    no_prompt = '--no-prompt' if no_prompt else ''
    execute = '--execute' if execute else ''
    command = f"jupyter nbconvert {template} --to=html --output={output} {no_input} {no_prompt} {execute} --allow-errors --ExecutePreprocessor.timeout={timeout}"

    # 环境变量名必须大写，值只能是字符串
    kwargs = {k.upper(): str(v) for k, v in kwargs.items()}
    # 担心环境变量副作用，同时跑多个影响其它进程，所以不用 os.environ
    # os.environ.update(kwargs)

    if os.name == 'nt':
        cmds = [f'set {k}={v}' for k, v in kwargs.items()] + [command]
        # commands = ' & '.join(cmds)
    else:
        cmds = [f'export {k}={v}' for k, v in kwargs.items()] + [command]
        # commands = ' ; '.join(cmds)

    commands = ' && '.join(cmds)

    print('environ:', kwargs)
    print('command:', command)
    print('system:', commands)

    ret = os.system(commands)
    if ret == 0 and open_browser:
        os.system(output)
    return ret


def create_2x2_sheet(df: pl.DataFrame,
                     x: str,
                     y: str, y1: str,
                     q: int = 10,
                     *,
                     period: int = 5,
                     split_x: str = '2020-01-01',
                     date: str = 'date', asset: str = 'asset') -> None:
    """画2*2的图表。含IC时序、IC直方图、IC热力图、累积收益图

    Parameters
    ----------
    df
    x
    y: str
        用于记算IC的N期收益
    y1:str
        用于记算收益的1期收益
    q:str
        分层数，默认10层
    period:int
        累计收益时持仓天数与资金份数
    split_x
    date
    asset

    Returns
    -------

    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    # 画IC信息
    df1 = calc_ic(df, x, [y], date=date)
    plot_ic_ts(df1, y, date=date, split_x=split_x, ax=axes[0, 0])
    plot_ic_hist(df1, y, ax=axes[0, 1])
    plot_ic_heatmap(df1, y, date=date, ax=axes[1, 0])

    # 画净值曲线
    df2 = calc_return_by_quantile(df, x, y1, q, date=date, asset=asset)
    df3 = calc_cum_return_by_quantile(df2, y1, q, period, date=date, asset=asset)
    plot_quantile_portfolio(df3, y1, period, split_x=split_x, ax=axes[1, 1])


def create_2x3_sheet(df: pl.DataFrame,
                     x: str,
                     y: str, y1: str,
                     q: int = 10,
                     *,
                     period: int = 5,
                     quantile=9,
                     periods: Sequence[int] = (1, 5, 10, 20),
                     split_x: str = '2020-01-01',
                     date: str = 'date', asset: str = 'asset') -> None:
    """画2*3图

    Parameters
    ----------
    df
    x
    y: str
        用于记算IC的N期收益
    y1:str
        用于记算收益的1期收益
    q:str
        分层数，默认10层
    period: int
        累计收益时持仓天数与资金份数
    quantile:int
        换手率关注第几层
    periods:
        换手率，多期比较
    split_x
    date
    asset

    Returns
    -------

    """
    fig, axes = plt.subplots(2, 3, figsize=(18, 9))

    # 画IC信息
    df1 = calc_ic(df, x, [y], date=date)
    plot_ic_ts(df1, y, date=date, split_x=split_x, ax=axes[0, 0])
    plot_ic_hist(df1, y, ax=axes[0, 1])
    plot_ic_heatmap(df1, y, date=date, ax=axes[0, 2])

    # 画净值曲线
    df2 = calc_return_by_quantile(df, x, y1, q, date=date, asset=asset)
    df3 = calc_cum_return_by_quantile(df2, y1, q, period, date=date, asset=asset)
    plot_quantile_portfolio(df3, y1, period, split_x=split_x, ax=axes[1, 0])

    # 画换手率
    df4 = calc_auto_correlation(df, x, periods=periods, date=date)
    df5 = calc_quantile_turnover(df, x, q=q, periods=periods)
    plot_factor_auto_correlation(df4, split_x=split_x, date=date, ax=axes[1, 1])
    plot_turnover_quantile(df5, quantile=quantile, periods=periods, split_x=split_x, date=date, ax=axes[1, 2])
