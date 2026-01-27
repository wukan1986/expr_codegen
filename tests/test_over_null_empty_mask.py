import expr_codegen  # type: ignore[import-untyped]


def _code(exec_line: str, *, over_null: str, skip_simplify: bool) -> str:
    code = expr_codegen.codegen_exec(
        None,
        exec_line,
        date="trade_date",
        asset="symbol",
        over_null=over_null,  # type: ignore[arg-type]
        convert_xor=True,
        skip_simplify=skip_simplify,
        extra_codes="",
    )
    assert isinstance(code, str)
    return code


def test_partition_by_empty_null_mask_does_not_generate_invalid_over_call() -> None:
    code = _code("f0 = ts_rank(RET - RET, 20)", over_null="partition_by", skip_simplify=False)
    assert ".over(," not in code
    assert "order_by=[," not in code


def test_order_by_empty_null_mask_does_not_generate_invalid_over_list() -> None:
    code = _code("f0 = ts_rank(RET - RET, 20)", over_null="order_by", skip_simplify=False)
    assert ".over(," not in code
    assert "order_by=[," not in code


def test_partition_by_skip_simplify_true_constant_tree_does_not_generate_invalid_over_call() -> None:
    # In typical downstream usage, skip_simplify=True; SymPy may still canonicalize and
    # cancel symbols during parsing (e.g. -RET - -RET -> 0), producing an empty mask.
    code = _code("f0 = ts_rank(-RET - -RET, 20)", over_null="partition_by", skip_simplify=True)
    assert ".over(," not in code
    assert "order_by=[," not in code


def test_order_by_skip_simplify_true_constant_tree_does_not_generate_invalid_over_list() -> None:
    code = _code("f0 = ts_rank(-RET - -RET, 20)", over_null="order_by", skip_simplify=True)
    assert ".over(," not in code
    assert "order_by=[," not in code
