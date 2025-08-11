from functools import reduce
from itertools import product, permutations

import networkx as nx
from sympy import symbols

from expr_codegen.dag import zero_indegree, hierarchy_pos, remove_paths_by_zero_outdegree
from expr_codegen.expr import CL, get_symbols, get_children, get_key, is_simple_expr

_RESERVED_WORD_ = {'_NONE_', '_TRUE_', '_FALSE_'}


class ListDictList:
    """嵌套列表

    1. 最外层是 列表[]
    2. 第二层是 字典{}
    3. 第三层是 列表[]

    [
    {'ts': [1, 2], 'cs': [2], 'gp_date': [2], 'gp_key': [2], }
    {'ts': [1], 'cs': [1],}
    ]

    """

    def __init__(self):
        self._list = []

    def clear(self):
        """清空"""
        self._list = []

    def values(self):
        return self._list

    def next_row(self):
        """移动到新的一行"""
        self._list.append({})

    def append(self, key, item):
        """自动放入同key的字典中"""
        last_row = self._list[-1]
        v = last_row.get(key, None)
        if v is None:
            # 同一行的新一列
            last_row[key] = [None, item]
        else:
            last_row[key].append(item)

    def filter_empty(self):
        """过滤空值"""
        new_list = []
        for row in self._list:
            try_del1 = []
            for k, v in row.items():
                if len(v) == 0:
                    try_del1.append(k)
            for k in try_del1:
                row.pop(k)
            if len(row) > 0:
                new_list.append(row)
        self._list = new_list

    def back_merge(self):
        """向上合并，将CL类型向前合并"""
        keys = reduce(lambda x, y: x + list(y.keys()), self._list, [])
        values = reduce(lambda x, y: x + list(y.values()), self._list, [])

        new_keys = []
        new_values = []
        last_k = None
        last_v = None
        for k, v in zip(keys, values):
            # 当前是整列时可以向上合并，但前一个是gp_xxx一类时不合并，因为循环太多次了
            # if (last_v is not None) and (k[0] == CL) and (last_k[0] != GP):
            if (last_v is not None) and (k == last_k):
                # print(1, k, last_k)
                last_v.extend(v)
                v.clear()
            else:
                # print(2, k, last_k)
                new_keys.append(k)
                new_values.append(v)
                last_v = v
                last_k = k

    def optimize(self, merge: bool):
        """将多组groupby根据规则进行合并，减少运行时间"""
        # 接龙。groupby的数量没少，首尾接龙数据比较整齐
        self._list = chain_create(self._list)
        if merge:
            # 首尾一样，接上去
            self.back_merge()
        # 出现了空行，删除
        self.filter_empty()

    def drop_symbols(self):
        """组装一种数据结构，用来存储之后会用到的变量名，用于提前删除不需要的变量"""
        # 获取每一小块所用到的所有变量名
        l1 = []
        for row in self._list:
            for k, v in row.items():
                vv = []
                for v1 in v:
                    if v1 is None:
                        continue
                    vv.extend(v1[2])
                l1.append(set(vv))

        # 得到此行与之后都会出现的变量名
        l2 = [set()]
        s = set()
        for i in reversed(l1):
            s = s | i  # - {'_NONE_', '_TRUE_', '_FALSE_'}
            l2.append(s)
        l2 = list(reversed(l2))

        # 计算之后不会再出现的变量名
        l3 = [list(s - e) for s, e in zip(l2[:-1], l2[1:])]

        return l3


def score1(row) -> int:
    # 首尾相连打分加1
    lst = [None] + [key for r in row for key in dict(r).keys()]
    return sum([x == y for x, y in zip(lst[:-1], lst[1:])])


def score2(row) -> float:
    # 最后一个ts越靠前，打分越高
    lst = ['ts'] + [key[0] for r in row for key in dict(r).keys()]
    return lst[::-1].index('ts') / len(lst)


def chain_create(nested_list):
    """接龙。多个列表，头尾相连

    测试用表达式
    ma_10 = ts_mean(CLOSE, 10)
    MAMA_20 = ts_mean(ma_10, 20)
    alpha_031 = ((cs_rank(cs_rank(cs_rank(ts_decay_linear((-1 * cs_rank(cs_rank(ts_delta(CLOSE, 10)))), 10))))))

    """
    perms = []
    for d in nested_list:
        # 每一层生成排列
        perms.append(permutations(d.items()))

    last_score = float('-inf')
    last_row = None
    # 生成笛卡尔积
    for row in product(*perms):
        result = score1(row) + score2(row)
        # print(result, row)
        if result > last_score:
            last_score = result
            last_row = row

    return [dict(ro) for ro in last_row]


# ==========================

def create_dag_exprs(exprs):
    """根据表达式字典生成DAG"""
    # 创建有向无环图
    G = nx.DiGraph()

    for symbol, expr, comment in exprs:
        # if symbol.name == 'GP_0':
        #     test = 1
        if expr.is_Symbol:
            G.add_node(symbol.name, symbol=symbol, expr=expr, comment=comment)
            G.add_edge(expr.name, symbol.name)
        else:
            # 添加中间节点
            G.add_node(symbol.name, symbol=symbol, expr=expr, comment=comment)
            syms = get_symbols(expr, return_str=True)
            for sym in syms:
                # 由于边的原因，这里会主动生成一些源节点
                G.add_edge(sym, symbol.name)
            if len(syms) == 0:
                # GP_0033=log(1/2400)
                if hasattr(expr, 'name'):
                    G.add_edge(expr.name, symbol.name)
                else:
                    G.add_edge(str(expr), symbol.name)

    # 源始因子，添加属性
    for node in zero_indegree(G):
        s = symbols(node)
        G.nodes[node]['symbol'] = s
        G.nodes[node]['expr'] = s
        G.nodes[node]['comment'] = "#"
    #
    # for node in zero_outdegree(G):
    #     print(11, G.nodes[node]['comment'])
    return G


def init_dag_exprs(G, func, func_kwargs, date, asset):
    """使用表达式信息初始化DAG"""
    for i, generation in enumerate(nx.topological_generations(G)):
        # print(i, generation)
        for node in generation:
            expr = G.nodes[node]['expr']
            syms = []
            children = get_children(func, func_kwargs, expr, [], syms, date, asset)
            G.nodes[node]['children'] = children
            G.nodes[node]['key'] = get_key(children)
            G.nodes[node]['symbols'] = [str(s) for s in syms]
            G.nodes[node]['gen'] = i
            # print(G.nodes[node])
    return G


def merge_nodes_1(G: nx.DiGraph, keep_nodes, *args):
    """合并节点，从当前节点开始，查看是否可能替换前后两端的节点"""
    # 准备一个当前节点列表
    this_pred = args
    # 下一步不为空就继续
    while this_pred:
        next_pred = []
        for node in this_pred:
            if not G.has_node(node):
                continue
            pred = G.pred[node]
            if len(pred) == 0:
                # 到了最上层的因子，需停止
                continue
            dic = G.nodes[node]
            key = dic['key']
            expr = dic['expr']
            symbols = dic['symbols']
            if key[0] == CL:
                if is_simple_expr(expr):
                    # 检查表达式是否很简单, 是就替换，可能会替换多个
                    skip_expr_node(G, node, keep_nodes)
                else:
                    succ = G.succ[node]
                    # 下游只有一个，直接替换。
                    if len(succ) == 1:
                        for s in succ:
                            # if_else(_A>_B,_A,_B)会出现量次，不能删
                            if G.nodes[s]['symbols'].count(node) > 1:
                                continue
                            skip_expr_node(G, node, keep_nodes)
            else:
                # 复制一次，防止修改后报错
                for p in pred.copy():
                    # 在下游同一表达式中使用了多次，不替换
                    if symbols.count(p) > 1:
                        continue
                    d = G.nodes[p]
                    k = d['key']
                    e = d['expr']
                    if key == k:
                        # 同类型
                        succ = G.succ[p]
                        # 下游只有一个，直接替换。
                        if len(succ) == 1:
                            for s in succ:
                                if G.nodes[s]['symbols'].count(p) > 1:
                                    continue
                                skip_expr_node(G, p, keep_nodes)
            next_pred.extend(pred)
        # 更新下一次循环
        this_pred = list(set(next_pred))
    return G


def merge_nodes_2(G: nx.DiGraph, keep_nodes, *args):
    """合并节点，从当前节点开始，查看是否需要被替换，只做用于根节点"""
    # 准备一个当前节点列表
    this_pred = args
    # 下一步不为空就继续
    while this_pred:
        next_pred = []
        for node in this_pred:
            dic = G.nodes[node]
            expr = dic['expr']
            if not is_simple_expr(expr):
                continue
            pred = G.pred[node]
            for p in pred.copy():
                succ = G.succ[p]
                if len(succ) > 1:
                    # 上游节点只有一个下游，当前就是自己了
                    continue
                for s in succ:
                    if G.nodes[s]['symbols'].count(p) > 1:
                        continue
                    skip_expr_node(G, p, keep_nodes)
            # 只做根节点，所以没有下一次了
            # next_pred.extend(pred)
        # 更新下一次循环
        this_pred = list(set(next_pred))
    return G


def get_expr_labels(G, nodes=None):
    """得到表达式标签"""
    labels = {}
    if nodes is None:
        for n, d in G.nodes(data=True):
            labels[n] = '{symbol}={expr}'.format(**d)
    else:
        for n, d in G.nodes(data=True):
            if n not in nodes:
                continue
            labels[n] = '{symbol}={expr}'.format(**d)
    return labels


def draw_expr_tree(G: nx.DiGraph, root: str, ax=None):
    """画表达式树"""
    # 查找上游节点
    nodes = nx.ancestors(G, root) | {root}
    labels = get_expr_labels(G, nodes)
    # 子图
    view = nx.subgraph(G, nodes)
    # 位置
    pos = hierarchy_pos(G, root)
    nx.draw(view, ax=ax, pos=pos, labels=labels)


def skip_expr_node(G: nx.DiGraph, node, keep_nodes):
    """跳过中间节点，将两端的节点直接连接起来，同时更新表达式

    1. (A,B,C) 模式，直接成 (A,C)
    2. (A,B,C), (D, B) 模式，变成 (A,C),(D,C)
    """
    if node in keep_nodes:
        return G

    pred = G.pred[node]
    succ = G.succ[node]
    if len(pred) == 0 or len(succ) == 0:
        return G

    # 取当前节点表达式
    d = G.nodes[node]
    expr = d['expr']
    symbol = d['symbol']

    for s in succ:
        e = G.nodes[s]['expr']
        e = e.xreplace({symbol: expr})
        G.nodes[s]['expr'] = e

    # 这里用了product生成多个关联边
    G.add_edges_from(product(pred, succ))
    G.remove_node(node)
    return G


def dag_start(exprs_list, func, func_kwargs, date, asset):
    """初始生成DAG"""
    G = create_dag_exprs(exprs_list)
    G = init_dag_exprs(G, func, func_kwargs, date, asset)

    # 分层输出
    return G


def dag_middle(G, exprs_names, skip_columns, func, func_kwargs, date, asset):
    """删除几个没有必要的节点"""
    # 以下划线开头的节点，不保留
    keep_nodes = [k for k in exprs_names if not k.startswith('_')]

    G = merge_nodes_1(G, keep_nodes, *keep_nodes)
    G = merge_nodes_2(G, keep_nodes, *keep_nodes)

    # 移除0出度的节点，但保留部分
    G = remove_paths_by_zero_outdegree(G, set(keep_nodes) - set(skip_columns))

    # 由于表达式修改，需再次更新表达式
    G = init_dag_exprs(G, func, func_kwargs, date, asset)

    # 分层输出
    return G


def dag_end(G):
    """有向无环图流转"""
    exprs_ldl = ListDictList()

    for i, generation in enumerate(nx.topological_generations(G)):
        exprs_ldl.next_row()
        for node in generation:
            key = G.nodes[node]['key']
            expr = G.nodes[node]['expr']
            comment = G.nodes[node]['comment']
            symbols = G.nodes[node]['symbols']
            # 这几个特殊的不算成字段名
            symbols = list(set(symbols) - _RESERVED_WORD_)

            exprs_ldl.append(key, (node, expr, symbols, comment))

    # 第0层是CLOSE等基础因子，剔除
    exprs_ldl._list = exprs_ldl.values()[1:]

    return exprs_ldl, G
