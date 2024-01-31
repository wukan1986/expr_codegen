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


def source_to_asts(source):
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
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raw.append(node)
        # 特殊处理的节点
        if isinstance(node, ast.Assign):
            assigns.append(node)
    return raw_to_code(raw), assigns_to_dict(assigns)


def assigns_to_dict(assigns):
    """赋值表达式转成字典"""
    return {ast.unparse(a.targets): ast.unparse(a.value) for a in assigns}


def raw_to_code(raw):
    """导入语句转字符列表"""
    return '\n'.join([ast.unparse(a) for a in raw])
#
#
# value = f"""# 向编辑器登记自动完成关键字，按字母排序
#
# # 请在此添加表达式，`=`右边为表达式，`=`左边为新因子名。
# alpha_003=-1 * ts_corr(cs_rank(OPEN), cs_rank(VOLUME), 10)
#
# """
#
# # value = f"""# 向编辑器登记自动完成关键字，按字母排序
# #
# # def aaa():
# #     # 请在此添加表达式，`=`右边为表达式，`=`左边为新因子名。
# #     alpha_003=-1 * ts_corr(cs_rank(OPEN), cs_rank(VOLUME), 10)
# #
# # """
#
# source_to_asts(value)
