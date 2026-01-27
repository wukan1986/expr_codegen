import expr_codegen  # type: ignore[import-untyped]


def _code(expr: str) -> str:
    code = expr_codegen.codegen_exec(
        None,
        expr,
        date="trade_date",
        asset="symbol",
        over_null=None,
        convert_xor=True,
        skip_simplify=False,
        extra_codes="",
    )
    assert isinstance(code, str)
    return code


def test_abs_lifts_numeric_arg_to_pl_lit() -> None:
    code = _code("f0 = ts_rank(abs_(RET - RET), 20)")
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
