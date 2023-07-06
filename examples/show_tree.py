from matplotlib import pyplot as plt
from sympy import numbered_symbols

from examples.sympy_define import *
from expr_codegen.dag import zero_outdegree
from expr_codegen.model import create_dag_exprs, init_dag_exprs, draw_expr_tree, merge_nodes_1, merge_nodes_2
from expr_codegen.tool import ExprTool

exprs_src = {
    "alpha_001": (cs_rank(ts_arg_max(signed_power(if_else((RETURNS < 0), ts_std_dev(RETURNS, 20), CLOSE), 2.), 5)) - 0.5),
    "alpha_002": (-1 * ts_corr(cs_rank(ts_delta(log(VOLUME), 2)), cs_rank(((CLOSE - OPEN) / OPEN)), 6)),
    "alpha_003": (-1 * ts_corr(cs_rank(OPEN), cs_rank(VOLUME), 10)),
    "alpha_004": (-1 * ts_rank(cs_rank(LOW), 9)),
    "alpha_005": (cs_rank((OPEN - (ts_sum(VWAP, 10) / 10))) * (-1 * abs(cs_rank((CLOSE - VWAP))))),
    "alpha_006": -1 * ts_corr(OPEN, VOLUME, 10),
}

# TODO: 一定要正确设定时间列名和资产列名，以及表达式识别类
tool = ExprTool(date='date', asset='asset')

# 子表达式在前，原表式在最后
exprs_dst, syms_dst = tool.merge(**exprs_src)

# 提取公共表达式
exprs_dict = tool.cse(exprs_dst, symbols_repl=numbered_symbols('x_'), symbols_redu=exprs_src.keys())

# 创建DAG
G = create_dag_exprs(exprs_dict)
G = init_dag_exprs(G, tool.get_current_func, tool.get_current_func_kwargs, tool.date, tool.asset)

# 以下可以看到节点的合并过程
zero = zero_outdegree(G)
for z in zero:
    print(z)
    # 在同一画布上画上下两图
    fig, axs = plt.subplots(2, 1)
    draw_expr_tree(G, z, ax=axs[0])
    merge_nodes_1(G, z)
    merge_nodes_2(G, z)
    draw_expr_tree(G, z, ax=axs[1])
    plt.show()
