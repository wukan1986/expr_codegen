import os
from typing import Sequence, Dict

import jinja2
from jinja2 import FileSystemLoader, TemplateNotFound

from expr_codegen.expr import TS, CS, GP
from expr_codegen.model import ListDictList
from expr_codegen.polars_group.printer import PolarsStrPrinter


def get_groupby_from_tuple(tup, func_name, drop_cols):
    """从传入的元组中生成分组运行代码"""
    prefix2, *_ = tup

    if prefix2 == TS:
        # 组内需要按时间进行排序，需要维持顺序
        prefix2, asset = tup
        return f'df = df.sort(_ASSET_, _DATE_).group_by(_ASSET_).map_groups({func_name}).drop(*{drop_cols})'
    if prefix2 == CS:
        prefix2, date = tup
        return f'df = df.sort(_DATE_).group_by(_DATE_).map_groups({func_name}).drop(*{drop_cols})'
    if prefix2 == GP:
        prefix2, date, group = tup
        return f'df = df.sort(_DATE_, "{group}").group_by(_DATE_, "{group}").map_groups({func_name}).drop(*{drop_cols})'

    return f'df = {func_name}(df).drop(*{drop_cols})'


def symbols_to_code(syms, alias):
    a = [f"{s}" for s in syms]
    b = [f"r'{alias.get(s, s)}'" for s in syms]  #
    b = [f"'{alias.get(s, s)}'" for s in syms]
    return f"""_ = [{','.join(b)}]
[{','.join(a)}] = [pl.col(i) for i in _]"""


def codegen(exprs_ldl: ListDictList, exprs_src, syms_dst,
            filename='template.py.j2',
            date='date', asset='asset',
            alias: Dict[str, str] = {},
            extra_codes: Sequence[str] = (),
            **kwargs):
    """基于模板的代码生成"""
    # 打印Polars风格代码
    p = PolarsStrPrinter()

    # polars风格代码
    funcs = {}
    # 分组应用代码。这里利用了字典按插入顺序排序的特点，将排序放在最前
    groupbys = {'sort': ''}
    # 处理过后的表达式
    exprs_dst = []
    syms_out = []

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
                    func_code.append(f"    )")
                    func_code.append(f"# " + '=' * 40)
                    func_code.append(f"    df = df.with_columns(")
                    exprs_dst.append(f"#" + '=' * 40 + func_name)
                else:
                    va, ex, sym = kv
                    s1 = str(ex)
                    s2 = p.doprint(ex)
                    if s1 != s2:
                        # 不想等，打印注释，显示会更直观察
                        func_code.append(f"# {va} = {s1}")

                    func_code.append(f"{va}={s2},")
                    exprs_dst.append(f"{va} = {s1}")
                    if va not in syms_dst:
                        syms_out.append(va)
            func_code.append(f"    )")
            func_code = func_code[1:]

            if k[0] == TS:
                # if len(groupbys['sort']) == 0:
                #     groupbys['sort'] = f'df = df.sort(_ASSET_, _DATE_)'
                # 时序需要排序
                func_code = [f'    df = df.sort(_DATE_)'] + func_code

            # polars风格代码列表
            funcs[func_name] = '\n'.join(func_code)
            # 只有下划线开头再删除
            ds = [x for x in drop_symbols[j] if x.startswith('_')]
            # 分组应用代码
            groupbys[func_name] = get_groupby_from_tuple(k, func_name, ds)

    syms1 = symbols_to_code(syms_dst, alias)
    syms2 = symbols_to_code(syms_out, alias)

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
