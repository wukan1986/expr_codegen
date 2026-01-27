import polars as pl
import random
import pytest

import expr_codegen  # type: ignore[import-untyped]

pytest.importorskip("polars_ta")


def _mini_panel(*, n_symbols: int = 3, n_days: int = 80) -> pl.LazyFrame:
    rng = random.Random(0)
    symbols = [f"S{i:03d}" for i in range(n_symbols)]
    dates = [f"2020-01-{i:02d}" for i in range(1, n_days + 1)]

    rows: list[tuple[object, ...]] = []
    for sym in symbols:
        for j, d in enumerate(dates):
            # Create some nulls via a simple gate, mimicking typical downstream usage.
            gate = (j % 7) != 0
            rows.append(
                (
                    sym,
                    d,
                    gate,
                    float(rng.random() - 0.5),  # RET5
                    float(rng.random() - 0.5),  # V_RET
                    float(rng.random() - 0.5),  # TREND
                )
            )

    df = pl.DataFrame(
        rows,
        schema=["symbol", "trade_date", "gate", "RET5", "V_RET", "TREND"],
        orient="row",
    )
    lf = df.lazy().sort(["symbol", "trade_date"]).with_columns(
        [
            pl.when(pl.col("gate"))
            .then(pl.col(name))
            .otherwise(None)
            .cast(pl.Float64, strict=False)
            .alias(name)
            for name in ["RET5", "V_RET", "TREND"]
        ]
    )
    return lf.drop("gate")


def _collect_exprs(panel: pl.LazyFrame, exec_lines: list[str]) -> None:
    exec_code = "\n".join(exec_lines)
    fcols = [line.split("=", 1)[0].strip() for line in exec_lines]
    lf = expr_codegen.codegen_exec(
        panel,
        exec_code,
        date="trade_date",
        asset="symbol",
        over_null="partition_by",
        convert_xor=True,
        skip_simplify=True,
        extra_codes="from polars_ta.prefix.wq import *",
    )
    assert isinstance(lf, pl.LazyFrame)

    # Mimic a typical usage pattern: filter -> select -> sort -> collect.
    signal_dates = [f"2020-01-{i:02d}" for i in range(21, 71, 5)]
    (
        lf.filter(pl.col("trade_date").is_in(signal_dates))
        .select(["symbol", "trade_date", *fcols])
        .sort(["symbol", "trade_date"])
        .collect()
    )


def test_polars_lazy_udf_return_type_inference_regression() -> None:
    # Regression test for a Polars LazyFrame failure in a window context:
    #   InvalidOperationError: UDF called without return type, but was not able to infer the output type.
    #
    # The problematic pattern is when codegen emits scalar literals into an Expr tree
    # via elementwise functions on constant-folded inputs (e.g. sign(V_RET - V_RET)).
    panel = _mini_panel()

    e0 = "f15 = ts_decay_linear(ts_delta(RET5, 5), 20) - sign(V_RET - V_RET)"
    e1 = (
        "f61 = V_RET - (TREND / (abs_(RET5) + if_else(abs_(RET5) == 0.0, 1e-06, 0.0)) - V_RET)"
    )

    # Alone: OK
    _collect_exprs(panel, [e0])
    _collect_exprs(panel, [e1])

    # Together: should also succeed (no scalar leaks into the expr tree).
    _collect_exprs(panel, [e0, e1])
