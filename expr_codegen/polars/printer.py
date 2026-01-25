from sympy import Add, Basic, Float, Function, Integer, Mul, Pow, Rational, StrPrinter
from sympy.printing.precedence import precedence, PRECEDENCE


# TODO: 如有新添加函数，但表达式有变更才需要在此补充对应的打印代码，否则可以省略

class PolarsStrPrinter(StrPrinter):
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

    def _print_Function(self, expr) -> str:
        func_name = expr.func.__name__

        def _lit(v: object) -> str:
            if isinstance(v, bool):
                return "pl.lit(True)" if v else "pl.lit(False)"
            if isinstance(v, int):
                return f"pl.lit({v})"
            if isinstance(v, float):
                if v != v:  # NaN
                    return "pl.lit(float('nan'))"
                if v == float("inf"):
                    return "pl.lit(float('inf'))"
                if v == float("-inf"):
                    return "pl.lit(float('-inf'))"
                return f"pl.lit({repr(float(v))})"
            return f"pl.lit({repr(v)})"

        def _const_scalar(node: object) -> int | float | bool | None:
            # Only fold constant-only expressions to avoid accidental execution of
            # user-defined code. This is deliberately conservative.
            if isinstance(node, (int, float, bool)):
                return node
            if isinstance(node, Integer):
                return int(node)
            if isinstance(node, Float):
                return float(node)
            if isinstance(node, Rational):
                p, q = int(node.p), int(node.q)
                if q == 0:
                    return None
                v = p / q
                if float(v).is_integer():
                    return int(v)
                return float(v)
            if not isinstance(node, Basic):
                return None
            try:
                if getattr(node, "free_symbols", set()):
                    return None
            except Exception:
                return None
            if getattr(node, "is_number", False):
                try:
                    if getattr(node, "is_integer", False):
                        return int(node)
                except Exception:
                    pass
                try:
                    return float(node)
                except Exception:
                    return None
            return None

        def _fold_const_function_call(call: object) -> str | None:
            # Fold a small set of elementwise/conditional functions when all inputs
            # are constant-only. This avoids emitting runtime calls like `sign(0)`,
            # which may return numpy scalars (e.g. np.int64) and break Polars Lazy
            # type inference in some window/weights plans.
            if not getattr(call, "is_Function", False):
                return None
            fn = getattr(call.func, "__name__", "")
            args = list(getattr(call, "args", ()))

            vals = [_const_scalar(a) for a in args]
            if any(v is None for v in vals):
                return None

            try:
                if fn in ("abs_", "abs") and len(vals) == 1:
                    v = vals[0]
                    if isinstance(v, bool):
                        return _lit(1 if v else 0)
                    if isinstance(v, int):
                        return _lit(abs(v))
                    return _lit(abs(float(v)))

                if fn in ("sign", "sign_") and len(vals) == 1:
                    x = float(vals[0])
                    out = 0 if x == 0.0 else (1 if x > 0.0 else -1)
                    return _lit(out)

                if fn in ("neg_", "neg") and len(vals) == 1:
                    v = vals[0]
                    if isinstance(v, bool):
                        return _lit(-1 if v else 0)
                    if isinstance(v, int):
                        return _lit(-v)
                    return _lit(-float(v))

                if fn in ("log", "log_") and len(vals) == 1:
                    import math

                    x = float(vals[0])
                    return _lit(float(math.log(x)))

                if fn in ("min_", "min") and len(vals) >= 1:
                    xs = [float(v) for v in vals]
                    return _lit(float(min(xs)))

                if fn in ("max_", "max") and len(vals) >= 1:
                    xs = [float(v) for v in vals]
                    return _lit(float(max(xs)))

                if fn == "clip_" and len(vals) == 3:
                    x, lo, hi = (float(vals[0]), float(vals[1]), float(vals[2]))
                    return _lit(float(min(max(x, lo), hi)))

                if fn in ("if_else", "where_") and len(vals) == 3:
                    cond = vals[0]
                    # bool condition: choose branch directly
                    if isinstance(cond, bool):
                        return _lit(vals[1] if cond else vals[2])
                    # numeric truthy/falsy: 0 => False
                    try:
                        return _lit(vals[1] if float(cond) != 0.0 else vals[2])
                    except Exception:
                        return None
            except Exception:
                return None

            return None

        folded = _fold_const_function_call(expr)
        if folded is not None:
            return folded

        if func_name.startswith("ts_"):
            # For ts_* functions:
            # - The "series" args must be polars expressions (so numeric constants
            #   there should be wrapped as `pl.lit(...)`).
            # - The trailing numeric params (window sizes, etc.) must remain plain
            #   Python scalars (ints/floats), otherwise downstream libs may do
            #   `min_samples or ...` and trigger Expr.__bool__ errors.
            args = list(expr.args)

            def _is_numeric(arg: object) -> bool:
                if isinstance(arg, (Integer, Float, Rational)):
                    return True
                if isinstance(arg, Basic):
                    try:
                        if getattr(arg, "is_number", False) and not getattr(arg, "free_symbols", set()):
                            return True
                    except Exception:
                        return False
                return False

            def _scalar_str(arg: object) -> str:
                if isinstance(arg, Integer):
                    return str(int(arg))
                if isinstance(arg, Float):
                    return repr(float(arg))
                if isinstance(arg, Rational):
                    p, q = int(arg.p), int(arg.q)
                    if q == 1:
                        return str(p)
                    return repr(p / q)
                if isinstance(arg, Basic) and getattr(arg, "is_number", False):
                    # Numeric-only SymPy expressions (e.g. Mul(Integer(-1), Integer(0))).
                    try:
                        if getattr(arg, "is_integer", False):
                            return str(int(arg))
                    except Exception:
                        pass
                    try:
                        return repr(float(arg))
                    except Exception:
                        return self._print(arg)
                return self._print(arg)

            def _scalar_str_from_value(v: object) -> str:
                if isinstance(v, bool):
                    return "1" if v else "0"
                if isinstance(v, int):
                    return str(v)
                if isinstance(v, float):
                    return repr(float(v))
                return repr(v)

            def _try_const_value(node: object) -> int | float | bool | None:
                # Only evaluate constant-only expressions to avoid accidentally
                # executing user-defined code.
                if isinstance(node, (int, float, bool)):
                    return node
                if isinstance(node, Integer):
                    return int(node)
                if isinstance(node, Float):
                    return float(node)
                if isinstance(node, Rational):
                    p, q = int(node.p), int(node.q)
                    if q == 0:
                        return None
                    v = p / q
                    if float(v).is_integer():
                        return int(v)
                    return float(v)
                if not isinstance(node, Basic):
                    return None
                try:
                    if getattr(node, "free_symbols", set()):
                        return None
                except Exception:
                    return None

                # Native numeric-only SymPy expressions.
                if getattr(node, "is_number", False):
                    try:
                        if getattr(node, "is_integer", False):
                            return int(node)
                    except Exception:
                        pass
                    try:
                        return float(node)
                    except Exception:
                        return None

                # Basic arithmetic on constant subexpressions.
                if isinstance(node, Add):
                    vals = [_try_const_value(a) for a in node.args]
                    if any(v is None for v in vals):
                        return None
                    return float(sum(float(v) for v in vals))
                if isinstance(node, Mul):
                    vals = [_try_const_value(a) for a in node.args]
                    if any(v is None for v in vals):
                        return None
                    out = 1.0
                    for v in vals:
                        out *= float(v)
                    return float(out)
                if isinstance(node, Pow):
                    base = _try_const_value(node.args[0])
                    exp = _try_const_value(node.args[1])
                    if base is None or exp is None:
                        return None
                    try:
                        return float(float(base) ** float(exp))
                    except Exception:
                        return None

                # Safe subset of constant function evaluation.
                if getattr(node, "is_Function", False):
                    fn = getattr(node.func, "__name__", "")
                    vals = [_try_const_value(a) for a in node.args]
                    if any(v is None for v in vals):
                        return None
                    xs = [float(v) for v in vals]
                    try:
                        if fn in ("abs_", "abs") and len(xs) == 1:
                            return abs(xs[0])
                        if fn in ("sign", "sign_") and len(xs) == 1:
                            x = xs[0]
                            return 0.0 if x == 0.0 else (1.0 if x > 0.0 else -1.0)
                        if fn in ("neg_", "neg") and len(xs) == 1:
                            return -xs[0]
                        if fn in ("log", "log_") and len(xs) == 1:
                            import math

                            return float(math.log(xs[0]))
                        if fn in ("min_", "min") and len(xs) >= 1:
                            return float(min(xs))
                        if fn in ("max_", "max") and len(xs) >= 1:
                            return float(max(xs))
                        if fn == "clip_" and len(xs) == 3:
                            x, lo, hi = xs
                            return float(min(max(x, lo), hi))
                        if fn in ("if_else", "where_") and len(vals) == 3:
                            cond = vals[0]
                            if isinstance(cond, bool):
                                return _try_const_value(node.args[1] if cond else node.args[2])
                            # Treat numeric condition as truthy/falsy (0 => False).
                            try:
                                return _try_const_value(node.args[1] if float(cond) != 0.0 else node.args[2])
                            except Exception:
                                return None
                    except Exception:
                        return None
                return None

            last_non_num_idx = -1
            for i, arg in enumerate(args):
                if not _is_numeric(arg):
                    last_non_num_idx = i

            numeric_start = 1 if last_non_num_idx < 0 else last_non_num_idx + 1

            printed_args: list[str] = []
            for i, arg in enumerate(args):
                if _is_numeric(arg):
                    if i >= numeric_start:
                        # Trailing numeric parameters: keep them as scalars.
                        printed_args.append(_scalar_str(arg))
                    else:
                        # Series position numeric constants: lift to Expr.
                        # Important: numeric-only SymPy expressions must also be lifted,
                        # otherwise Python will evaluate them as scalars before calling ts_*.
                        printed_args.append(f"pl.lit({_scalar_str(arg)})")
                else:
                    if i < numeric_start:
                        v = _try_const_value(arg)
                        if v is not None:
                            printed_args.append(f"pl.lit({_scalar_str_from_value(v)})")
                            continue
                    printed_args.append(self._print(arg))

            return f"{func_name}({','.join(printed_args)})"

        return super()._print_Function(expr)

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
