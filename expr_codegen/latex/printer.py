from sympy import Symbol, Function, Basic
from sympy.core.sorting import default_sort_key
from sympy.printing.latex import LatexPrinter, accepted_latex_functions


class ExprLatexPrinter(LatexPrinter):
    """改版的Latex表达式打印。

    主要解决不少函数和符号中的下划线被转成下标的问题
    """

    def _print(self, expr, **kwargs) -> str:
        """Internal dispatcher

        Tries the following concepts to print an expression:
            1. Let the object print itself if it knows how.
            2. Take the best fitting method defined in the printer.
            3. As fall-back use the emptyPrinter method for the printer.
        """
        self._print_level += 1
        try:
            # If the printer defines a name for a printing method
            # (Printer.printmethod) and the object knows for itself how it
            # should be printed, use that method.
            if self.printmethod and hasattr(expr, self.printmethod):
                if not (isinstance(expr, type) and issubclass(expr, Basic)):
                    return getattr(expr, self.printmethod)(self, **kwargs)

            # See if the class of expr is known, or if one of its super
            # classes is known, and use that print function
            # Exception: ignore the subclasses of Undefined, so that, e.g.,
            # Function('gamma') does not get dispatched to _print_gamma
            classes = type(expr).__mro__
            # if AppliedUndef in classes:
            #     classes = classes[classes.index(AppliedUndef):]
            # if UndefinedFunction in classes:
            #     classes = classes[classes.index(UndefinedFunction):]
            # Another exception: if someone subclasses a known function, e.g.,
            # gamma, and changes the name, then ignore _print_gamma
            if Function in classes:
                i = classes.index(Function)
                classes = tuple(c for c in classes[:i] if \
                                c.__name__ == classes[0].__name__ or \
                                c.__name__.endswith("Base")) + classes[i:]
            for cls in classes:
                printmethodname = '_print_' + cls.__name__
                printmethod = getattr(self, printmethodname, None)
                if printmethod is not None:
                    return printmethod(expr, **kwargs)
            # Unknown object, fall back to the emptyPrinter.
            return self.emptyPrinter(expr)
        finally:
            self._print_level -= 1

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

    def _print_abs_(self, expr, exp=None):
        return self._print_Abs(expr, exp)

    def _print_log_(self, expr, exp=None):
        return self._print_log(expr, exp)

    def _print_max_(self, expr, exp=None):
        # return self._print_Max(expr, exp)
        args = sorted(expr.args, key=default_sort_key)
        texargs = [r"%s" % self._print(symbol) for symbol in args]
        tex = r"\%s\left(%s\right)" % ('max', ", ".join(texargs))
        if exp is not None:
            return r"%s^{%s}" % (tex, exp)
        else:
            return tex

    def _print_min_(self, expr, exp=None):
        args = sorted(expr.args, key=default_sort_key)
        texargs = [r"%s" % self._print(symbol) for symbol in args]
        tex = r"\%s\left(%s\right)" % ('min', ", ".join(texargs))
        if exp is not None:
            return r"%s^{%s}" % (tex, exp)
        else:
            return tex


def latex(expr, mode='equation*', mul_symbol='times', **settings):
    """表达式转LATEX字符串"""
    settings.update({'mode': mode, 'mul_symbol': mul_symbol})
    return ExprLatexPrinter(settings).doprint(expr)


def display_latex(expr):
    """显示LATEX表达式，在VSCode或Notebook中显示正常"""
    from IPython.display import Markdown, display

    return display(Markdown(latex(expr)))
