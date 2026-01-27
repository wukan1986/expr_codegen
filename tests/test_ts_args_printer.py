import expr_codegen  # type: ignore[import-untyped]


def _code(expr: str) -> str:
    code = expr_codegen.codegen_exec(
        None,
        expr,
        date="trade_date",
        asset="symbol",
        over_null=None,
        convert_xor=True,
        skip_simplify=True,
        extra_codes="",
    )
    assert isinstance(code, str)
    return code


def test_ts_delay_lifts_numeric_series_arg_but_keeps_window_scalar() -> None:
    code = _code("f0 = ts_delay(1, 5)")
    assert "ts_delay(pl.lit(1), 5)" in code
    assert "ts_delay(pl.lit(1), pl.lit(5))" not in code


def test_ts_corr_keeps_trailing_window_scalar() -> None:
    code = _code("f0 = ts_corr(RET, VOL, 20)")
    assert "pl.lit(20)" not in code
    assert "ts_corr(RET, VOL, 20)" in code


def test_ts_corr_lifts_numeric_series_arg() -> None:
    code = _code("f0 = ts_corr(1, VOL, 20)")
    assert "ts_corr(pl.lit(1), VOL, 20)" in code
