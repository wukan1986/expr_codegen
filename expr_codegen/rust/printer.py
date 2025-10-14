import inspect

from sympy import Basic, Function, StrPrinter


# TODO: 如有新添加函数，但表达式有变更才需要在此补充对应的打印代码，否则可以省略

class RustStrPrinter(StrPrinter):
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
        if expr.name in ('_NONE_', '_TRUE_', '_FALSE_'):
            return expr.name
        return f'col("{expr.name}")'

    def _print_Equality(self, expr):
        new_args = [f"eq({self._print(arg)})" for arg in expr.args]
        return ".".join(new_args)[2:]

    def _print_Or(self, expr):
        new_args = [f"or({self._print(arg)})" for arg in expr.args]
        return ".".join(new_args)[2:]

    def _print_Xor(self, expr):
        new_args = [f"xor({self._print(arg)})" for arg in expr.args]
        return ".".join(new_args)[3:]

    def _print_And(self, expr):
        new_args = [f"and({self._print(arg)})" for arg in expr.args]
        return ".".join(new_args)[3:]

    def _print_Not(self, expr):
        return "(%s).not()" % self._print(expr.args[0])

    def _print_gp_(self, expr):
        """gp_函数都转换成cs_函数，但要丢弃第一个参数"""
        new_args = [self._print(arg) for arg in expr.args[1:]]
        func_name = expr.func.__name__[3:]
        return "cs_%s(%s)" % (func_name, ",".join(new_args))

    def _print_Integer(self, expr):
        caller_frame = inspect.stack()[2]
        caller_name = caller_frame.function
        if caller_name in ("_print_Pow", "_print_Add", "_print_Mul", "_print_Relational"):
            return "lit(%s)" % super()._print_Integer(expr)
        else:
            return super()._print_Integer(expr)

    def _print_Float(self, expr):
        caller_frame = inspect.stack()[2]
        caller_name = caller_frame.function
        if caller_name in ("_print_Pow", "_print_Add", "_print_Mul", "_print_Relational"):
            return "lit(%s)" % super()._print_Float(expr)
        else:
            return super()._print_Float(expr)

    def _print_Relational(self, expr):

        charmap = {
            "<": "lt",
            ">": "gt",
            ">=": "gt_eq",
            "<=": "lt_eq",
        }

        if expr.rel_op in charmap:
            return '(%s).%s(%s)' % (self._print(expr.lhs), charmap[expr.rel_op], self._print(expr.rhs))

        return super()._print_Relational(expr)
