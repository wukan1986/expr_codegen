from sympy import Basic, Function, StrPrinter
from sympy.core.numbers import Float, Integer, Rational
from sympy.printing.precedence import precedence, PRECEDENCE


# TODO: 如有新添加函数，但表达式有变更才需要在此补充对应的打印代码，否则可以省略

class PolarsStrPrinter(StrPrinter):
    @staticmethod
    def _lit_number(expr) -> str:
        if isinstance(expr, Integer):
            return f"pl.lit({int(expr)})"
        if isinstance(expr, Float):
            return f"pl.lit({float(expr)!r})"
        if isinstance(expr, Rational):
            return f"pl.lit({float(expr)!r})"
        if isinstance(expr, Basic) and getattr(expr, "is_number", False):
            try:
                if getattr(expr, "is_integer", False):
                    return f"pl.lit({int(expr)})"
            except Exception:
                pass
            try:
                return f"pl.lit({float(expr)!r})"
            except Exception:
                return f"pl.lit({expr})"
        return f"pl.lit({expr})"

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

                # 所有以gp_开头的函数都转换成cs_开头
                if printmethodname.startswith('_print_gp_'):
                    printmethodname = "_print_gp_"

                printmethod = getattr(self, printmethodname, None)
                if printmethod is not None:
                    return printmethod(expr, **kwargs)
            # Unknown object, fall back to the emptyPrinter.
            return self.emptyPrinter(expr)
        finally:
            self._print_level -= 1

    def _print_Symbol(self, expr):
        return expr.name

    def _print_Equality(self, expr):
        PREC = precedence(expr)
        return "%s == %s" % (self.parenthesize(expr.args[0], PREC), self.parenthesize(expr.args[1], PREC))

    def _print_Unequality(self, expr):
        PREC = precedence(expr)
        return "%s != %s" % (self.parenthesize(expr.args[0], PREC), self.parenthesize(expr.args[1], PREC))

    def _print_Or(self, expr):
        PREC = PRECEDENCE["Mul"]
        return " | ".join(self.parenthesize(arg, PREC) for arg in expr.args)

    def _print_Xor(self, expr):
        PREC = PRECEDENCE["Mul"]
        return " ^ ".join(self.parenthesize(arg, PREC) for arg in expr.args)

    def _print_And(self, expr):
        PREC = PRECEDENCE["Mul"]
        return " & ".join(self.parenthesize(arg, PREC) for arg in expr.args)

    def _print_Not(self, expr):
        PREC = PRECEDENCE["Mul"]
        return "~%s" % self.parenthesize(expr.args[0], PREC)

    def _print_gp_(self, expr):
        """gp_函数都转换成cs_函数，但要丢弃第一个参数"""
        new_args = [self._print(arg) for arg in expr.args[1:]]
        func_name = expr.func.__name__[3:]
        return "cs_%s(%s)" % (func_name, ",".join(new_args))

    def _print_Function(self, expr):
        fn = expr.func.__name__
        args = list(expr.args)

        def _is_constant_expr(a) -> bool:
            if not isinstance(a, Basic):
                return False
            try:
                return not bool(getattr(a, "free_symbols", set()))
            except Exception:
                return False

        def _is_numeric_only(a) -> bool:
            if isinstance(a, (Integer, Float, Rational)):
                return True
            if isinstance(a, Basic) and getattr(a, "is_number", False):
                try:
                    return not bool(getattr(a, "free_symbols", set()))
                except Exception:
                    return False
            return False

        lift_numeric_arg_positions = {
            "abs": {0},
            "abs_": {0},
            "sign": {0},
            "sign_": {0},
            "cs_rank": {0},
            "signed_power": {0},
        }.get(fn)
        if lift_numeric_arg_positions:
            printed = []
            for i, a in enumerate(args):
                if i in lift_numeric_arg_positions and _is_numeric_only(a):
                    printed.append(self._lit_number(a))
                else:
                    printed.append(self._print(a))
            return f"{fn}({', '.join(printed)})"

        if fn.startswith("ts_"):
            if len(args) >= 2:
                series_args, scalar_tail = args[:-1], args[-1:]
            else:
                series_args, scalar_tail = args, []

            printed = []
            for a in series_args:
                # polars_ta's ts_* expects a per-row series input for its "series args".
                # A scalar Expr like pl.lit(1) will produce all-null results for shift/rolling.
                # If an arg becomes a constant-only expression (e.g. RET-RET+1 -> 1), broadcast it.
                if _is_constant_expr(a):
                    inner = self._lit_number(a) if _is_numeric_only(a) else self._print(a)
                    printed.append(f"pl.repeat({inner}, pl.len())")
                else:
                    printed.append(self._print(a))
            printed.extend(self._print(a) for a in scalar_tail)
            return f"{fn}({', '.join(printed)})"

        return super()._print_Function(expr)
