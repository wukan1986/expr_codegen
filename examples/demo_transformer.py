import ast
import sys

from expr_codegen.codes import source_replace, SympyTransformer

encoding = 'utf-8'
input_file = 'factors_test1.txt'
output_file = 'factors_test2.txt'

# ==========================
# 观察区，查看存在哪些变量和函数
with open(input_file, 'r', encoding=encoding) as f:
    sources = f.readlines()

    # 不要太大，防止内存不足
    source = '\n'.join(sources[:1000])

    tree = ast.parse(source_replace(source))
    t = SympyTransformer()
    t.visit(tree)

    print('=' * 60)
    print(t.funcs_old)
    print(t.args_old)
    print(t.targets_old)
    print('=' * 60)

# ==========================
# 映射
funcs_map = {'abs': 'abs_',
             'max': 'max_',
             'min': 'min_',
             'delta': 'ts_delta',
             'delay': 'ts_delay',
             'ts_argmin': 'ts_arg_min',
             'ts_argmax': 'ts_arg_max',
             # TODO 目前不支持的操作
             # 'cs_corr': '',
             # 'cs_std': '',
             }
args_map = {}
targets_map = {}

# TODO 如果后面文件太大，耗时太久，需要手工放开后面一段
sys.exit(-1)
# ==========================
with open(input_file, 'r', encoding=encoding) as f:
    sources = f.readlines()

    t = SympyTransformer()
    t.config_map(funcs_map, args_map, targets_map)

    outputs = []
    for i in range(0, len(sources), 1000):
        print(i)
        source = '\n'.join(sources[i:i + 1000])

        tree = ast.parse(source_replace(source))
        t.visit(tree)
        outputs.append(ast.unparse(tree))

    print('转码完成')
    with open(output_file, 'w') as f2:
        f2.writelines(outputs)
    print('保存成功')
