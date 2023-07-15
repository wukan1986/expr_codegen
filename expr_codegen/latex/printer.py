from sympy import Symbol
from sympy.printing.latex import LatexPrinter, accepted_latex_functions


class ExprLatexPrinter(LatexPrinter):
    """改版的Latex表达式打印。

    主要解决不少函数和符号中的下划线被转成下标的问题
    """

    def _hprint_Function(self, func: str) -> str:
        # func = self._deal_with_super_sub(func)
        superscriptidx = -1  # func.find("^")
        subscriptidx = -1  # func.find("_")
        func = func.replace('_', r'\_')
        if func in accepted_latex_functions:
            name = r"\%s" % func
        elif len(func) == 1 or func.startswith('\\') or subscriptidx == 1 or superscriptidx == 1:
            name = func
        else:
            if superscriptidx > 0 and subscriptidx > 0:
                name = r"\operatorname{%s}%s" % (
                    func[:min(subscriptidx, superscriptidx)],
                    func[min(subscriptidx, superscriptidx):])
            elif superscriptidx > 0:
                name = r"\operatorname{%s}%s" % (
                    func[:superscriptidx],
                    func[superscriptidx:])
            elif subscriptidx > 0:
                name = r"\operatorname{%s}%s" % (
                    func[:subscriptidx],
                    func[subscriptidx:])
            else:
                name = r"\operatorname{%s}" % func
        return name

    def _print_Symbol(self, expr: Symbol, style='plain'):
        name: str = self._settings['symbol_names'].get(expr)
        if name is not None:
            return name

        return expr.name.replace('_', r'\_')


def latex(expr, mode='equation*', mul_symbol='times', **settings):
    """表达式转LATEX字符串"""
    settings.update({'mode': mode, 'mul_symbol': mul_symbol})
    return ExprLatexPrinter(settings).doprint(expr)


def display_latex(expr):
    """显示LATEX表达式，在VSCode或Notebook中显示正常"""
    from IPython.display import Markdown, display

    return display(Markdown(latex(expr)))
