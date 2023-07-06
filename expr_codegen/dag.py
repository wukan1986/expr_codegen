from itertools import product

import networkx as nx


def zero_indegree(G: nx.DiGraph):
    """入度为0的所有节点"""
    return [v for v, d in G.in_degree() if d == 0]


def zero_outdegree(G: nx.DiGraph):
    """出度为0的所有节点"""
    return [v for v, d in G.out_degree() if d == 0]


def skip_node(G: nx.DiGraph, node):
    """跳过中间节点，将两端的节点直接连接起来

    1. (A,B,C) 模式，直接成 (A,C)
    2. (A,B,C), (D, B) 模式，变成 (A,C),(D,C)
    """
    pred = G.pred[node]
    succ = G.succ[node]
    if len(pred) == 0 or len(succ) == 0:
        return G
    # 这里用了product生成多个关联边
    G.add_edges_from(product(pred, succ))
    G.remove_node(node)
    return G


def remove_paths(G: nx.DiGraph, *args):
    """删除路径。选择一个叶子节点，会删到不影响其它分支停止

    对于Y型，会全删除
    """
    # 准备一个当前节点列表
    this_pred = args
    # 下一步不为空就继续
    while this_pred:
        next_pred = []
        for node in this_pred:
            # 有可能多路径删除时，已经被删
            if not G.has_node(node):
                continue
            # 出度为0
            if len(G.succ[node]) == 0:
                # 找到所有上游节点
                next_pred.extend(G.pred[node])
                G.remove_node(node)
        # 更新下一次循环
        this_pred = list(set(next_pred))
    return G


def remove_paths_by_zero_outdegree(G: nx.DiGraph, exclude):
    """删除悬空路径

    注意:如果没有设置要排除，可能全图被删"""
    nodes = zero_outdegree(G)
    # 悬空
    dangling = set(nodes) - set(exclude)
    return remove_paths(G, *dangling)


def show_nodes(G):
    for i, generation in enumerate(nx.topological_generations(G)):
        print(i, '=' * 20, generation)
        for node in generation:
            print(G.nodes[node])


def show_paths(G: nx.DiGraph, *args):
    """显示路径
    """
    # 准备一个当前节点列表
    this_pred = args
    # 下一步不为空就继续
    while this_pred:
        next_pred = []
        for node in this_pred:
            print(G.nodes[node])
            next_pred.extend(G.pred[node])

        # 更新下一次循环
        this_pred = list(set(next_pred))
    return G


def node_included_path(G: nx.DiGraph, source):
    """"得到节点所在路径

    TODO: 总感觉官方提供了类似方法，就是没找到
    """
    pred = nx.ancestors(G, source)
    succ = nx.descendants(G, source)
    # set先后没有区别
    return pred | succ | {source}


# 根据原版做了修改，树结构顶部为根，向下生成。与表达式正好相反，所以这里特意将找节点的方向反过来
# https://stackoverflow.com/questions/29586520/can-one-get-hierarchical-graphs-from-networkx-with-python-3/
def hierarchy_pos(G, root, levels=None, width=1., height=1.):
    """If there is a cycle that is reachable from root, then this will see infinite recursion.
       G: the graph
       root: the root node
       levels: a dictionary
               key: level number (starting from 0)
               value: number of nodes in this level
       width: horizontal space allocated for drawing
       height: vertical space allocated for drawing"""
    TOTAL = "total"
    CURRENT = "current"

    def make_levels(levels, node=root, currentLevel=0, parent=None):
        """Compute the number of nodes for each level
        """
        if not currentLevel in levels:
            levels[currentLevel] = {TOTAL: 0, CURRENT: 0}
        levels[currentLevel][TOTAL] += 1
        neighbors = G.predecessors(node)
        for neighbor in neighbors:
            if not neighbor == parent:
                levels = make_levels(levels, neighbor, currentLevel + 1, node)
        return levels

    def make_pos(pos, node=root, currentLevel=0, parent=None, vert_loc=0):
        dx = 1 / levels[currentLevel][TOTAL]
        left = dx / 2
        pos[node] = ((left + dx * levels[currentLevel][CURRENT]) * width, vert_loc)
        levels[currentLevel][CURRENT] += 1
        neighbors = G.predecessors(node)
        for neighbor in neighbors:
            if not neighbor == parent:
                pos = make_pos(pos, neighbor, currentLevel + 1, node, vert_loc - vert_gap)
        return pos

    if levels is None:
        levels = make_levels({})
    else:
        levels = {l: {TOTAL: levels[l], CURRENT: 0} for l in levels}
    vert_gap = height / (max([l for l in levels]) + 1)
    return make_pos({})
