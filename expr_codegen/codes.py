import ast
import re


class SympyTransformer(ast.NodeTransformer):
    """将ast转换成Sympy要求的格式"""

    def visit_Compare(self, node):
        # OPEN==CLOSE
        if isinstance(node.ops[0], ast.Eq):
            # 等号会直接比较变成False
            node = ast.Call(
                func=ast.Name(id='Eq', ctx=ast.Load()),
                args=[node.left, node.comparators[0]],
                keywords=[],
            )

        self.generic_visit(node)
        return node

    def visit_IfExp(self, node):
        # 三元表达式。需要在外部提前替换成if else
        # OPEN>=CLOSE?1:0
        # OPEN>CLOSE?A==B?3:DE>FG?5:6:0
        node = ast.Call(
            func=ast.Name(id='if_else', ctx=ast.Load()),
            args=[node.body, node.test, node.orelse],
            keywords=[],
        )

        self.generic_visit(node)
        return node

    def visit_BinOp(self, node):
        # TypeError: unsupported operand type(s) for *: 'StrictLessThan' and 'int'
        if isinstance(node.op, ast.Mult):
            # (OPEN < CLOSE) * -1
            if isinstance(node.left, ast.Compare):
                node.left = ast.Call(
                    func=ast.Name(id='if_else', ctx=ast.Load()),
                    args=[node.left, ast.Constant(value=1), ast.Constant(value=0)],
                    keywords=[],
                )
            # -1*(OPEN < CLOSE)
            if isinstance(node.right, ast.Compare):
                node.right = ast.Call(
                    func=ast.Name(id='if_else', ctx=ast.Load()),
                    args=[node.right, ast.Constant(value=1), ast.Constant(value=0)],
                    keywords=[],
                )
            # 这种情况要处理吗？
            # (OPEN < CLOSE)*(OPEN < CLOSE)
        self.generic_visit(node)
        return node


def sources_to_asts(*sources):
    """输入多份源代码"""
    raw = []
    assigns = {}
    for arg in sources:
        r, a = _source_to_asts(arg)
        raw.append(r)
        assigns.update(a)
    return '\n'.join(raw), assigns


def _source_to_asts(source):
    """源代码"""
    # 三元表达式转换成 错误if( )else
    source = re.sub(r':(.+?)', r' )else \1', source).replace('?', ' if( ')
    tree = ast.parse(source)
    SympyTransformer().visit(tree)

    raw = []
    assigns = []

    if isinstance(tree.body[0], ast.FunctionDef):
        body = tree.body[0].body
    else:
        body = tree.body

    for node in body:
        # 特殊处理的节点
        if isinstance(node, ast.Assign):
            assigns.append(node)
            continue
        # TODO 是否要把其它语句也加入？是否有安全问题？
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raw.append(node)
            continue
    return raw_to_code(raw), assigns_to_dict(assigns)


def assigns_to_dict(assigns):
    """赋值表达式转成字典"""
    return {ast.unparse(a.targets): ast.unparse(a.value) for a in assigns}


def raw_to_code(raw):
    """导入语句转字符列表"""
    return '\n'.join([ast.unparse(a) for a in raw])
