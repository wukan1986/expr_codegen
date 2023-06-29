from itertools import product


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

    def clear(self):
        self._list = []

    def values(self):
        return self._list

    def optimize(self):
        """相临两层的同类其实可以合并，可以减少groupby次数"""
        chains, head, tail = chains_create(self._list)
        self._list, new_head, new_tail = chains_sort(self._list, chains, head, tail)
        chians_move(new_head, new_tail)


def chains_create(nested_list):
    """接龙。多个列表，头尾相连"""
    # 两两取交集，交集为{}时，添加一个{None}，防止product时出错
    neighbor_inter = [set(x) & set(y) or {None} for x, y in zip(nested_list[:-1], nested_list[1:])]

    # 查找最小数字，表示两两不重复
    last_min = float('inf')
    last_row = None
    for row in product(*neighbor_inter):
        # 判断两两是否重复
        result = sum([x == y for x, y in zip(row[:-1], row[1:])])
        if last_min > result:
            last_min = result
            last_row = row
        if result == 0:
            break

    # 调整后的第0列
    head = [None] + list(last_row)
    # 调整后的第-1列
    tail = list(last_row) + [None]

    # 调整新列表
    arr = []
    for ll, hh, tt in zip(nested_list, head, tail):
        d = {}
        if hh is not None:
            d[hh] = 0
        for l in ll:
            if (l == hh) or (l == tt):
                continue
            d[l] = 1
        if tt is not None:
            d[tt] = 2

        arr.append(list(d.keys()))
    return arr, head, tail


def chains_sort(old_ldl, chains, head, tail):
    """三层嵌套结构根据接龙表进行复制"""
    new_ldl = []
    new_head = []
    new_tail = []
    for i, row in enumerate(chains):
        # 构造
        hh = head[i]
        tt = tail[i]
        new_head.append(old_ldl[i].get(hh, []))
        new_tail.append(old_ldl[i].get(tt, []))

        last_row = {}
        new_ldl.append(last_row)
        for r in row:
            last_row[r] = old_ldl[i][r]

    return new_ldl, new_head, new_tail


def chians_move(head, tail):
    """会修改原数据结构"""
    for hh, tt in reversed(list(zip(head[1:], tail[:-1]))):
        tt.extend(hh)
        hh.clear()
