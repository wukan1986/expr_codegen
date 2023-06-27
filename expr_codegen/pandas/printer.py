from sympy import StrPrinter, Basic, Function
from sympy.printing.precedence import precedence


# TODO: 如有新添加函数，需要在此补充对应的打印代码

class PandasStrPrinter(StrPrinter):
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

    def _print_Symbol(self, expr):
        # return expr.name
        return f"df['{expr.name}']"

    def _print_two_args(self, expr, func_name):
        prec = precedence(expr)
        if precedence(expr.args[0]) < prec:
            return "(%s).%s(%s)" % (self._print(expr.args[0]), func_name, self._print(expr.args[1]))
        else:
            return "%s.%s(%s)" % (self._print(expr.args[0]), func_name, self._print(expr.args[1]))

    def _print_rolling_args(self, expr, func_name):
        prec = precedence(expr)
        if precedence(expr.args[0]) < prec:
            return "(%s).rolling(%s).%s()" % (self._print(expr.args[0]), self._print(expr.args[1]), func_name)
        else:
            return "%s.rolling(%s).%s()" % (self._print(expr.args[0]), self._print(expr.args[1]), func_name)

    def _print_one_args(self, expr, func_name):
        prec = precedence(expr)
        if precedence(expr.args[0]) < prec:
            return "(%s).%s()" % (self._print(expr.args[0]), func_name)
        else:
            return "%s.%s()" % (self._print(expr.args[0]), func_name)

    def _print_ts_mean(self, expr):
        return self._print_rolling_args(expr, 'mean')

    def _print_ts_delta(self, expr):
        return self._print_two_args(expr, 'diff')

    def _print_ts_delay(self, expr):
        return self._print_two_args(expr, 'shift')

    def _print_ts_corr(self, expr):
        return "(%s).rolling(%s).corr(%s)" % (self._print(expr.args[0]), self._print(expr.args[2]), self._print(expr.args[1]))

    def _print_cs_rank(self, expr):
        return "(%s).rank(pct=True)" % (self._print(expr.args[0]),)

    def _print_log(self, expr):
        return "np.log(%s)" % (self._print(expr.args[0]),)

    def _print_abs(self, expr):
        return self._print_one_args(expr, 'abs')

    def _print_sign(self, expr):
        return self._print_one_args(expr, 'sign')

    def _print_gp_rank(self, expr):
        return "(%s).rank(pct=True)" % (self._print(expr.args[0]),)
