import ast
import re
from ast import expr

from black import Mode, format_str
from sympy import Add, Mul, Pow, Eq, Not, Xor

from expr_codegen.expr import register_symbols, dict_to_exprs


class SyntaxTransformer(ast.NodeTransformer):
    """修改语法。注意：一定要修改语法后才能改名"""

    def __init__(self, convert_xor):
        # ^ 是异或还是乘方呢？
        self.convert_xor = convert_xor

    def visit_Assign(self, node):
        t = node.targets[0]
        nodes = []
        if isinstance(t, ast.Tuple):
            for i, dim in enumerate(t.dims):
                _v = ast.Call(
                    func=ast.Name(id='unpack', ctx=ast.Load()),
                    args=[node.value, ast.Constant(i)],
                    keywords=[],
                )
                n = ast.Assign([dim], _v, ctx=ast.Load())
                nodes.append(n)
            return nodes

        self.generic_visit(node)
        return node

    def visit_Compare(self, node):
        assert len(node.comparators) == 1, f"不支持连续等号，请手工添加括号, {ast.unparse(node)}"

        self.generic_visit(node)
        return node

    def visit_IfExp(self, node):
        # 三元表达式。需要在外部提前替换成or True if else
        # 只要body区域，出现了or True，就认为是特殊处理过的
        if isinstance(node.body, ast.BoolOp) and isinstance(node.body.op, ast.Or):
            if isinstance(node.body.values[-1], ast.Constant):
                if node.body.values[-1].value:
                    node.test, node.body = node.body.values[0], node.test

        node = ast.Call(
            func=ast.Name(id='if_else', ctx=ast.Load()),
            args=[node.test, node.body, node.orelse],
            keywords=[],
        )

        self.generic_visit(node)
        return node

    def visit_BinOp(self, node):
        # TypeError: unsupported operand type(s) for *: 'StrictLessThan' and 'int'
        if isinstance(node.op, (ast.Mult, ast.Add, ast.Div, ast.Sub)):
            # (OPEN < CLOSE) * -1
            if isinstance(node.left, ast.Compare):
                node.left = ast.Call(
                    func=ast.Name(id='int_', ctx=ast.Load()),
                    args=[node.left],
                    keywords=[],
                )
            # -1*(OPEN < CLOSE)
            if isinstance(node.right, ast.Compare):
                node.right = ast.Call(
                    func=ast.Name(id='int_', ctx=ast.Load()),
                    args=[node.right],
                    keywords=[],
                )
            # 这种情况，已经包含
            # (OPEN < CLOSE)*(OPEN < CLOSE)

        if isinstance(node.op, ast.BitXor):
            # ^ 运算符，转换为pow还是xor
            if self.convert_xor:
                node = ast.Call(
                    func=ast.Name(id='Pow', ctx=ast.Load()),
                    args=[node.left, node.right],
                    keywords=[],
                )
            else:
                node = ast.Call(
                    func=ast.Name(id='Xor', ctx=ast.Load()),
                    args=[node.left, node.right],
                    keywords=[],
                )

        self.generic_visit(node)
        return node

    def visit_UnaryOp(self, node):
        # ~ts_delay 报错，替换成Not(ts_delay)
        if isinstance(node.op, ast.Invert):
            node = ast.Call(
                func=ast.Name(id='Not', ctx=ast.Load()),
                args=[node.operand],
                keywords=[],
            )

        self.generic_visit(node)
        return node

    def visit_Subscript(self, node):
        if isinstance(node.slice, ast.Constant) and node.slice.value == 0:
            node = node.value
        elif isinstance(node.slice, ast.UnaryOp) and isinstance(node.slice.operand, ast.Constant) and node.slice.operand.value == 0:
            node = node.value
        else:
            node = ast.Call(
                func=ast.Name(id='ts_delay', ctx=ast.Load()),
                args=[node.value, node.slice],
                keywords=[],
            )
        self.generic_visit(node)
        return node


class RenameTransformer(ast.NodeTransformer):
    """改名处理。改名前需要语法规范"""

    def __init__(self, funcs_map, targets_map, args_map=None):

        if args_map is None:
            # 保留字
            args_map = {'True': "_TRUE_", 'False': "_FALSE_", 'None': "_NONE_"}
        self.funcs_old = set()
        self.args_old = set()
        self.targets_old = set()
        self.funcs_new = set()
        self.args_new = set()
        self.targets_new = set()
        # 映射
        self.funcs_map = funcs_map
        # 由于None等常量无法在sympy中正确处理，只能改成Symbol变量
        # !!!一定要在drop_symbols时排除
        self.args_map = args_map
        # 只对非下划线开头的生效
        self.targets_map = targets_map

    def visit_Call(self, node):
        # 提取函数名
        self.funcs_old.add(node.func.id)
        node.func.id = self.funcs_map.get(node.func.id, node.func.id)
        self.funcs_new.add(node.func.id)
        # 提取参数名
        for i, arg in enumerate(node.args):
            if isinstance(arg, ast.Name):
                self.args_old.add(arg.id)
                arg.id = self.args_map.get(arg.id, arg.id)
                self.args_new.add(arg.id)
            if isinstance(arg, ast.Constant):
                old_arg_value = str(arg.value)
                if old_arg_value in self.args_map:
                    new_arg_value = self.args_map.get(old_arg_value, old_arg_value)
                    self.args_old.add(old_arg_value)
                    node.args[i] = ast.Name(new_arg_value, ctx=ast.Load())
                    self.args_new.add(new_arg_value)

        self.generic_visit(node)
        return node

    def __visit_Assign(self, target: expr):
        old_target_id = target.id
        new_target_id = self.targets_map.get(old_target_id, old_target_id)
        self.targets_old.add(old_target_id)

        # 赋值给下划线开头代码时，对其进行重命名，方便重复书写表达式时不冲突
        if old_target_id.startswith('_'):
            # 减少与cse中_x_冲突
            new_target_id = f'{old_target_id}_{len(self.targets_new)}_'

        if old_target_id != new_target_id:
            self.targets_new.add(new_target_id)
            target.id = new_target_id
            # 记录修改的变量名，之后会使用到
            self.args_map[old_target_id] = new_target_id

        if isinstance(target, ast.Constant):
            old_target_value = str(target.value)
            if old_target_value in self.args_map:
                new_target_value = self.args_map.get(old_target_value, old_target_value)
                self.args_old.add(old_target_value)
                target = ast.Name(new_target_value, ctx=ast.Load())
                self.args_new.add(new_target_value)

        return target

    def visit_Assign(self, node):
        # 调整位置，支持循环赋值
        # _A = _A+1 调整成 _A_001 = _A_000 + 1
        self.generic_visit(node)

        # 提取输出变量名
        for i, target in enumerate(node.targets):
            if isinstance(target, ast.Tuple):
                for j, t in enumerate(target.elts):
                    target.elts[j] = self.__visit_Assign(t)
            else:
                node.targets[i] = self.__visit_Assign(target)

        # 处理 alpha=close 这种情况
        if isinstance(node.value, ast.Name):
            self.args_old.add(node.value.id)
            node.value.id = self.args_map.get(node.value.id, node.value.id)
            self.args_new.add(node.value.id)
        if isinstance(node.value, ast.Constant):
            old_node_value = str(node.value.value)
            if old_node_value in self.args_map:
                new_node_value = self.args_map.get(old_node_value, old_node_value)
                self.args_old.add(old_node_value)
                node.value = ast.Name(new_node_value, ctx=ast.Load())
                self.args_new.add(new_node_value)

        return node

    def visit_Compare(self, node):
        # 比较符的左右也可能是变量，要处理
        if isinstance(node.left, ast.Name):
            self.args_old.add(node.left.id)
            node.left.id = self.args_map.get(node.left.id, node.left.id)
            self.args_new.add(node.left.id)

        for i, com in enumerate(node.comparators):
            if isinstance(com, ast.Name):
                self.args_old.add(com.id)
                com.id = self.args_map.get(com.id, com.id)
                self.args_new.add(com.id)
            if isinstance(com, ast.Constant):
                old_com_value = str(com.value)
                if old_com_value in self.args_map:
                    new_com_value = self.args_map.get(old_com_value, old_com_value)
                    self.args_old.add(old_com_value)
                    node.comparators[i] = ast.Name(new_com_value, ctx=ast.Load())
                    self.args_new.add(new_com_value)

        self.generic_visit(node)
        return node

    def visit_IfExp(self, node):
        if isinstance(node.body, ast.Name):
            self.args_old.add(node.body.id)
            node.body.id = self.args_map.get(node.body.id, node.body.id)
            self.args_new.add(node.body.id)
        if isinstance(node.orelse, ast.Name):
            self.args_old.add(node.orelse.id)
            node.orelse.id = self.args_map.get(node.orelse.id, node.orelse.id)
            self.args_new.add(node.orelse.id)

        self.generic_visit(node)
        return node

    def visit_BinOp(self, node):
        if isinstance(node.left, ast.Name):
            self.args_old.add(node.left.id)
            node.left.id = self.args_map.get(node.left.id, node.left.id)
            self.args_new.add(node.left.id)
        if isinstance(node.right, ast.Name):
            self.args_old.add(node.right.id)
            node.right.id = self.args_map.get(node.right.id, node.right.id)
            self.args_new.add(node.right.id)
        if isinstance(node.left, ast.Constant):
            old_node_value = str(node.left.value)
            if old_node_value in self.args_map:
                new_node_value = self.args_map.get(old_node_value, old_node_value)
                self.args_old.add(old_node_value)
                node.left = ast.Name(new_node_value, ctx=ast.Load())
                self.args_new.add(new_node_value)
        if isinstance(node.right, ast.Constant):
            old_node_value = str(node.right.value)
            if old_node_value in self.args_map:
                new_node_value = self.args_map.get(old_node_value, old_node_value)
                self.args_old.add(old_node_value)
                node.right = ast.Name(new_node_value, ctx=ast.Load())
                self.args_new.add(new_node_value)

        self.generic_visit(node)
        return node

    def visit_UnaryOp(self, node):
        # -x
        if isinstance(node.operand, ast.Name):
            self.args_old.add(node.operand.id)
            node.operand.id = self.args_map.get(node.operand.id, node.operand.id)
            self.args_new.add(node.operand.id)
        if isinstance(node.operand, ast.Constant):
            old_operand_value = str(node.operand.value)
            if old_operand_value in self.args_map:
                new_operand_value = self.args_map.get(old_operand_value, old_operand_value)
                self.args_old.add(old_operand_value)
                node.operand = ast.Name(new_operand_value, ctx=ast.Load())
                self.args_new.add(new_operand_value)

        self.generic_visit(node)
        return node

    def visit_Subscript(self, node):
        self.args_old.add(node.value.id)
        node.value.id = self.args_map.get(node.value.id, node.value.id)
        self.args_new.add(node.value.id)

        self.generic_visit(node)
        return node


def source_replace(source: str) -> str:
    # 三元表达式转换成 错误版if( )else，一定得在Transformer中修正
    num = 1
    while num > 0:
        # 利用or 的优先级最低，构造特殊的if else，只要出现，就认为位置要替换
        # C?T:F --> C or True if( T )else F
        source, num = re.subn(r'\?(.+?):(.+?)', r' or True if( \1 )else \2', source, flags=re.S)
        # break
    # 或、与
    source = source.replace('||', '|').replace('&&', '&')
    # IndentationError: unexpected indent
    # 嵌套函数前有空格，会报错
    source = format_str(source, mode=Mode(line_length=600, magic_trailing_comma=True))
    return source


def assigns_to_dict(assigns):
    """赋值表达式转成字典"""
    return {ast.unparse(a.targets): ast.unparse(a.value) for a in assigns}


def raw_to_code(raw):
    """导入语句转字符列表"""
    return '\n'.join([ast.unparse(a) for a in raw])


def sources_to_asts(*sources, convert_xor: bool):
    """输入多份源代码"""

    def _source_to_asts(source):
        """源代码"""
        tree = ast.parse(source_replace(source))

        if isinstance(tree.body[0], ast.FunctionDef):
            body = tree.body[0].body
        else:
            body = tree.body

        return body

    tree = ast.parse("")
    for arg in sources:
        tree.body.extend(_source_to_asts(arg))

    t1 = SyntaxTransformer(convert_xor)
    t1.visit(tree)
    t = RenameTransformer({}, {})
    t.visit(tree)

    raw = []
    assigns = []

    for node in tree.body:
        # 特殊处理的节点
        if isinstance(node, ast.Assign):
            assigns.append(node)
            continue
        # TODO 是否要把其它语句也加入？是否有安全问题？
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raw.append(node)
            continue
    return raw_to_code(raw), assigns_to_dict(assigns), t.funcs_new, t.args_new, t.targets_new


def _add_default_type(globals_):
    # 这种写法可以省去由用户导入Eq一类的工作
    globals_['Add'] = Add
    globals_['Mul'] = Mul
    globals_['Pow'] = Pow
    globals_['Eq'] = Eq
    globals_['Not'] = Not
    globals_['Xor'] = Xor
    return globals_


def sources_to_exprs(globals_, *sources, convert_xor: bool):
    """将源代码转换成表达式"""

    globals_ = _add_default_type(globals_)

    raw, assigns, funcs_new, args_new, targets_new = sources_to_asts(*sources, convert_xor=convert_xor)
    # 支持OPEN[1]转ts_delay(OPEN,1)
    funcs_new.add('ts_delay')

    register_symbols(funcs_new, globals_, is_function=True)
    register_symbols(args_new, globals_, is_function=False)
    register_symbols(targets_new, globals_, is_function=False)
    exprs_dict = dict_to_exprs(assigns, globals_)
    return raw, exprs_dict
