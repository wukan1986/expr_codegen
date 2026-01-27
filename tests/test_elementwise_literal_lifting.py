import expr_codegen  # type: ignore[import-untyped]


def _code(expr: str, *, skip_simplify: bool = False) -> str:
    code = expr_codegen.codegen_exec(
        None,
        expr,
        date="trade_date",
        asset="symbol",
        over_null=None,
        convert_xor=True,
        skip_simplify=skip_simplify,
        extra_codes="",
    )
    assert isinstance(code, str)
    return code


def test_abs_lifts_numeric_arg_to_pl_lit() -> None:
    code = _code("f0 = abs_(RET - RET)")
    assert "abs_(pl.lit(0))" in code


def test_sign_lifts_numeric_arg_to_pl_lit() -> None:
    code = _code("f0 = sign(RET - RET)")
    assert "sign(pl.lit(0))" in code


def test_cs_rank_lifts_numeric_arg_to_pl_lit() -> None:
    code = _code("f0 = cs_rank(RET - RET)")
    assert "cs_rank(pl.lit(0))" in code


def test_signed_power_lifts_numeric_arg_to_pl_lit() -> None:
    code = _code("f0 = signed_power(RET - RET, 2)")
    assert "signed_power(pl.lit(0), 2)" in code


def test_sign_lifts_numeric_only_tree_to_pl_lit() -> None:
    code = _code("f0 = sign(-1 * (-1))")
    assert ("sign(pl.lit(1))" in code) or ("sign(pl.lit(1.0))" in code)


def test_sign_numeric_only_tree_from_skip_simplify_true_is_lifted() -> None:
    # In typical downstream usage, skip_simplify=True; parsing can still collapse to a numeric-only
    # expression tree (e.g. -RET - -RET + 1 -> -1 * (-1)).
    code = _code("f0 = sign(-RET - -RET + 1)", skip_simplify=True)
    assert ("sign(pl.lit(1))" in code) or ("sign(pl.lit(1.0))" in code)
