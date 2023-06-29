from functools import reduce
from itertools import product

from expr_codegen.expr import CL


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
        last_v = None
        for k, v in zip(keys, values):
            if (k == (CL,)) and (last_v is not None):
                last_v.extend(v)
                v.clear()
            else:
                new_keys.append(k)
                new_values.append(v)
                last_v = v

    def optimize(self, back_opt=True, chains_opt=True):
        """将多组groupby根据规则进行合并，减少运行时间

        back_opt和chains_opt时。例如：ts、cl、ts，会先变成ts、ts，然后变成ts。大大提高速度

        Parameters
        ----------
        back_opt:
            不需要groupby的组，其实是可以直接合并到前一组的。例如‘+’，即可以放时序组中也可以放横截面组中
        chains_opt:
            首尾接龙优化。同一层的组进行重排序，让多层形成首尾接龙的，第二组的头中的列表可以合并到前一组尾。
            如： 第一层最后的时序分组和第二层开始的时序分组是可以一起计算的

        """
        if back_opt:
            self.back_merge()
            self.filter_empty()

        if chains_opt:
            # 接龙
            chains, head, tail = chains_create(self._list)
            self._list, new_head, new_tail = chains_sort(self._list, chains, head, tail)
            # 将数据从第二的龙头复制到第一行的龙尾
            chians_move(new_head, new_tail)
            self.filter_empty()


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
    """龙头复制到上一个龙尾"""
    for hh, tt in reversed(list(zip(head[1:], tail[:-1]))):
        tt.extend(hh)
        hh.clear()
