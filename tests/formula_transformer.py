import ast

from expr_codegen.codes import source_replace, RenameTransformer

source = """
OPEN>=CLOSE?1:0
OPEN>CLOSE?A==B?3:DE>FG?5:6:0
A=OPEN==CLOSE
B,C=(OPEN < CLOSE) * -1,1

ts_sum(min(((delta(vol,8)-(high*vol))+7.1),max(((open>=low?amt:low)/4.2),ts_sum((open<low?open:amt),8))),9)
max(((vwap-8.6)^ts_mean(close,7)),ts_sum(min(vwap,4.5),3))
(ts_mean((vwap>=vol?amt:vol),3)+((vol==low?vwap:vol)*10.3))

"""

source = """
_A = 1+2
_B = 3+4
C = _A+_B
_A = 10+20
_B = 30+40
D = _A+_B
"""

# 再也不怕出现有环了
source = """
_A = True+None
# F = 1>None
# _A = Add(1,True)
# 
# _A = _A+_A
# _B = _A+2
# _C = _A+_B
# 
# D = _A

"""
tree = ast.parse(source_replace(source))
t = RenameTransformer()

funcs_map = {'abs': 'abs_',
             'max': 'max_',
             'min': 'min_',
             'delta': 'ts_delta',
             'delay': 'ts_delay',
             }
args_map = {'True': "TRUE", 'False': "FALSE", 'None': "NONE"}
targets_map = {'_A': '_12'}

t.config_map(funcs_map, args_map, targets_map)

t.visit(tree)
print('=' * 60)
print(t.funcs_old)
print(t.args_old)
print(t.targets_old)
print('=' * 60)
print(t.funcs_new)
print(t.args_new)
print(t.targets_new)
print('=' * 60)
print(ast.unparse(tree))
