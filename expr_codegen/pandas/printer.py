from sympy import Basic, Function, StrPrinter
from sympy.printing.precedence import precedence, PRECEDENCE


# TODO: 如有新添加函数，但表达式有变更才需要在此补充对应的打印代码，否则可以省略

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
            # print('=' * 60)
            for cls in classes:
                printmethodname = '_print_' + cls.__name__
                # print(printmethodname, expr)
                printmethod = getattr(self, printmethodname, None)
                if printmethod is not None:
                    return printmethod(expr, **kwargs)
            # Unknown object, fall back to the emptyPrinter.
            return self.emptyPrinter(expr)
        finally:
            self._print_level -= 1

    def _print_Symbol(self, expr):
        return f"df[{expr.name}]"

    def _print_Equality(self, expr):
        PREC = precedence(expr)
        return "%s==%s" % (self.parenthesize(expr.args[0], PREC), self.parenthesize(expr.args[1], PREC))

    def _print_Or(self, expr):
        PREC = PRECEDENCE["Mul"]
        return "%s | %s" % (self.parenthesize(expr.args[0], PREC), self.parenthesize(expr.args[1], PREC))

    def _print_Xor(self, expr):
        PREC = PRECEDENCE["Mul"]
        return "%s ^ %s" % (self.parenthesize(expr.args[0], PREC), self.parenthesize(expr.args[1], PREC))

    def _print_And(self, expr):
        PREC = PRECEDENCE["Mul"]
        return "%s & %s" % (self.parenthesize(expr.args[0], PREC), self.parenthesize(expr.args[1], PREC))

    def _print_Not(self, expr):
        PREC = PRECEDENCE["Mul"]
        return "~%s" % self.parenthesize(expr.args[0], PREC)

    def _print_if_else(self, expr):
        return "np.where(%s, %s, %s)" % (self._print(expr.args[0]), self._print(expr.args[1]), self._print(expr.args[2]))

    def _print_ts_mean(self, expr):
        PREC = precedence(expr)
        return "%s.rolling(%s).mean()" % (self.parenthesize(expr.args[0], PREC), self._print(expr.args[1]))

    def _print_ts_std_dev(self, expr):
        PREC = precedence(expr)
        return "%s.rolling(%s).std(ddof=0)" % (self.parenthesize(expr.args[0], PREC), self._print(expr.args[1]))

    def _print_ts_arg_max(self, expr):
        return "bn.move_argmax(%s, %s)" % (self._print(expr.args[0]), self._print(expr.args[1]))

    def _print_ts_arg_min(self, expr):
        return "bn.move_argmin(%s, %s)" % (self._print(expr.args[0]), self._print(expr.args[1]))

    def _print_ts_product(self, expr):
        PREC = precedence(expr)
        return "%s.rolling(%s).apply(np.product, raw=True)" % (self.parenthesize(expr.args[0], PREC), self._print(expr.args[1]))

    def _print_ts_max(self, expr):
        PREC = precedence(expr)
        return "%s.rolling(%s).max()" % (self.parenthesize(expr.args[0], PREC), self._print(expr.args[1]))

    def _print_ts_min(self, expr):
        PREC = precedence(expr)
        return "%s.rolling(%s).min()" % (self.parenthesize(expr.args[0], PREC), self._print(expr.args[1]))

    def _print_ts_delta(self, expr):
        PREC = precedence(expr)
        return "%s.diff(%s)" % (self.parenthesize(expr.args[0], PREC), self._print(expr.args[1]))

    def _print_ts_delay(self, expr):
        PREC = precedence(expr)
        return "%s.shift(%s)" % (self.parenthesize(expr.args[0], PREC), self._print(expr.args[1]))

    def _print_ts_corr(self, expr):
        PREC = precedence(expr)
        return "%s.rolling(%s).corr(%s, ddof=0)" % (self.parenthesize(expr.args[0], PREC), self._print(expr.args[2]), self._print(expr.args[1]))

    def _print_ts_covariance(self, expr):
        PREC = precedence(expr)
        return "%s.rolling(%s).cov(%s, ddof=0)" % (self.parenthesize(expr.args[0], PREC), self._print(expr.args[2]), self._print(expr.args[1]))

    def _print_ts_rank(self, expr):
        PREC = precedence(expr)
        return "%s.rolling(%s).rank(pct=True)" % (self.parenthesize(expr.args[0], PREC), self._print(expr.args[1]))

    def _print_ts_sum(self, expr):
        PREC = precedence(expr)
        return "%s.rolling(%s).sum()" % (self.parenthesize(expr.args[0], PREC), self._print(expr.args[1]))

    def _print_ts_decay_linear(self, expr):
        return "ta.WMA(%s, %s)" % (self._print(expr.args[0]), self._print(expr.args[1]))

    def _print_cs_rank(self, expr):
        PREC = precedence(expr)
        return "%s.rank(pct=True)" % self.parenthesize(expr.args[0], PREC)

    def _print_cs_scale(self, expr):
        return "scale(%s)" % self._print(expr.args[0])

    def _print_log(self, expr):
        return "np.log(%s)" % self._print(expr.args[0])

    def _print_abs_(self, expr):
        PREC = precedence(expr)
        if expr.args[0].is_Number:
            return "np.abs(%s)" % expr.args[0]
        else:
            return "%s.abs()" % self.parenthesize(expr.args[0], PREC)

    def _print_max_(self, expr):
        return "np.maximum(%s, %s)" % (self._print(expr.args[0]), self._print(expr.args[1]))

    def _print_min_(self, expr):
        return "np.minimum(%s, %s)" % (self._print(expr.args[0]), self._print(expr.args[1]))

    def _print_sign(self, expr):
        return "np.sign(%s)" % self._print(expr.args[0])

    def _print_gp_rank(self, expr):
        PREC = precedence(expr)
        return "%s.rank(pct=True)" % self.parenthesize(expr.args[0], PREC)

    def _print_gp_neutralize(self, expr):
        return "neutralize(%s)" % self._print(expr.args[1])
