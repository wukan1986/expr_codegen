import os
from typing import Sequence

import jinja2
from jinja2 import FileSystemLoader, TemplateNotFound

from expr_codegen.expr import TS, CS, GP
from expr_codegen.model import ListDictList
from expr_codegen.pandas.printer import PandasStrPrinter


def get_groupby_from_tuple(tup, func_name, drop_cols):
    """从传入的元组中生成分组运行代码"""
    prefix2, *_ = tup

    if len(drop_cols)>0:
        drop_str = f'.drop(columns={drop_cols})'
    else:
        drop_str = ""

    if prefix2 == TS:
        # 组内需要按时间进行排序，需要维持顺序
        prefix2, asset = tup
        return f'df = df.groupby(by=[_ASSET_], group_keys=False).apply({func_name}){drop_str}'
    if prefix2 == CS:
        prefix2, date = tup
        return f'df = df.groupby(by=[_DATE_], group_keys=False).apply({func_name}){drop_str}'
    if prefix2 == GP:
        prefix2, date, group = tup
        return f'df = df.groupby(by=[_DATE_, "{group}"], group_keys=False).apply({func_name}){drop_str}'

    return f'df = {func_name}(df){drop_str}'


def symbols_to_code(syms):
    a = [f"{s}" for s in syms]
    b = [f"'{s}'" for s in syms]
    return f"""_ = [{','.join(b)}]
[{','.join(a)}] = _"""


def codegen(exprs_ldl: ListDictList, exprs_src, syms_dst,
            filename,
            date='date', asset='asset',
            extra_codes: Sequence[str] = (),
            ge_date_idx: int = 0,
            **kwargs):
    """基于模板的代码生成"""
    if filename is None:
        filename = 'template.py.j2'

    # 打印Pandas风格代码
    p = PandasStrPrinter()

    # polars风格代码
    funcs = {}
    # 分组应用代码。这里利用了字典按插入顺序排序的特点，将排序放在最前
    groupbys = {'sort': ''}
    # 处理过后的表达式
    exprs_dst = []
    syms_out = []
    ts_func_name = None
    drop_symbols = exprs_ldl.drop_symbols()
    j = -1
    for i, row in enumerate(exprs_ldl.values()):
        for k, vv in row.items():
            j += 1
            if len(vv) == 0:
                continue
            # 函数名
            func_name = f'func_{i}_{"__".join(k)}'
            func_code = []
            for kv in vv:
                if kv is None:
                    func_code.append(f"    # " + '=' * 40)
                    exprs_dst.append(f"#" + '=' * 40 + func_name)
                else:
                    va, ex, sym, comment = kv
                    func_code.append(f"    # {va} = {ex}\n    g[{va}] = {p.doprint(ex)}")
                    exprs_dst.append(f"{va} = {ex} {comment}")
                    if va not in syms_dst:
                        syms_out.append(va)

            if len(groupbys['sort']) == 0:
                groupbys['sort'] = f'df = df.sort_values(by=[_ASSET_, _DATE_]).reset_index(drop=True)'
            if k[0] == TS:
                ts_func_name = func_name
                # 时序需要排序
                func_code = [f'    g.df = df.sort_values(by=[_DATE_])'] + func_code
            else:
                # 时序需要排序
                func_code = [f'    g.df = df'] + func_code

            # polars风格代码列表
            funcs[func_name] = '\n'.join(func_code)
            # 只有下划线开头再删除
            ds = [x for x in drop_symbols[j] if x.startswith('_')]
            # 分组应用代码
            groupbys[func_name] = get_groupby_from_tuple(k, func_name, ds)

    syms1 = symbols_to_code(syms_dst)
    syms2 = symbols_to_code(syms_out)
    # filter_last处理
    _groupbys = {'sort': groupbys['sort']}
    if ts_func_name is None:
        _groupbys['_filter_last'] = "df = _filter_last(df, ge_date_idx)"
    for k, v in groupbys.items():
        _groupbys[k] = v
        if k == ts_func_name:
            _groupbys[k + '_filter_last'] = "df = _filter_last(df, ge_date_idx)"
    groupbys = _groupbys

    try:
        env = jinja2.Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
        template = env.get_template(filename)
    except TemplateNotFound:
        env = jinja2.Environment(loader=FileSystemLoader(os.path.dirname(filename)))
        template = env.get_template(os.path.basename(filename))

    return template.render(funcs=funcs, groupbys=groupbys,
                           exprs_src=exprs_src, exprs_dst=exprs_dst,
                           syms1=syms1, syms2=syms2,
                           date=date, asset=asset,
                           extra_codes=extra_codes)
