"""Adding another output must not change a time-series expression's null groups."""

import polars as pl
from polars.testing import assert_frame_equal
import pytest

from expr_codegen import codegen_exec
from polars_ta.prefix.wq import ts_mean, ts_delay  # noqa: F401


def execute(frame, source, over_null):
    return codegen_exec(frame.lazy(), source, over_null=over_null, extra_codes="").collect()


@pytest.mark.parametrize("over_null", ["partition_by", "order_by", None])
@pytest.mark.parametrize("source", [
    "out = ts_mean(close, 2) / ts_mean(close, 4)",
    "out = ts_mean(ts_mean(close, 2), 3)",
    "out = ts_delay(close, 1) + ts_mean(close, 4)",
])
def test_time_series_output_is_invariant_to_sibling_outputs(over_null, source):
    frame = pl.DataFrame({"asset": ["A"] * 9 + ["B"] * 9, "date": list(range(9)) * 2,
        "close": [1., 2., 3., None, 5., 6., 7., 8., 9., None, 12., 13., 14., 15., 16., 17., 18., 19.]})
    single = execute(frame, source, over_null)
    batch = execute(frame, source + "\nother = ts_mean(close, 2)\nlonger = ts_mean(close, 4)", over_null)
    assert_frame_equal(single.select("asset", "date", "out"), batch.select("asset", "date", "out"))


def test_nested_windows_keep_each_stages_warmup():
    frame = pl.DataFrame({"asset": ["A"] * 8, "date": list(range(8)), "close": [float(i) for i in range(8)]})
    actual = execute(frame, "out = ts_mean(ts_mean(close, 2), 3)", "partition_by")
    expected = frame.with_columns(pl.col("close").rolling_mean(2).alias("first")).with_columns(
        pl.col("first").rolling_mean(3).alias("out"))
    assert_frame_equal(actual.select("asset", "date", "out"), expected.select("asset", "date", "out"))


@pytest.mark.parametrize("over_null", ["partition_by", "order_by"])
def test_nested_window_does_not_inherit_downstream_inputs_null_mask(over_null):
    frame = pl.DataFrame({"asset": ["A"] * 10, "date": list(range(10)),
        "close": [float(i) for i in range(10)],
        "high": [10., None, 12., 13., 14., None, 16., 17., 18., 19.]})
    actual = execute(frame, "out = ts_mean(ts_mean(close, 2) + high, 3)", over_null)
    first = frame.with_columns(pl.col("close").rolling_mean(2).alias("inner"))
    # The downstream operation excludes its missing inputs, but those missing
    # values must not alter the upstream rolling mean's history.
    valid = pl.col("inner").is_not_null() & pl.col("high").is_not_null()
    rolling = (pl.col("inner") + pl.col("high")).rolling_mean(3)
    expected = first.with_columns((rolling.over(valid, "asset", order_by="date") if over_null == "partition_by"
        else rolling.over("asset", order_by=[valid, "date"])).alias("out"))
    assert_frame_equal(actual.select("asset", "date", "out"), expected.select("asset", "date", "out"))


@pytest.mark.parametrize("policy", ["partition_by", "order_by", None])
def test_nested_windows_preserve_per_expression_null_policy(policy):
    frame = pl.DataFrame({"asset": ["A"] * 10, "date": list(range(10)),
                          "close": [1., 2., None, 4., 5., 6., 7., 8., 9., 10.]})
    directive = " # --over_null" + (" " + policy if policy else "")
    actual = execute(frame, "out = ts_mean(ts_mean(close, 2), 3)" + directive, "order_by")
    def window(value, inputs):
        mask = pl.all_horizontal([pl.col(name).is_not_null() for name in inputs])
        if policy == "partition_by":
            return value.over(mask, "asset", order_by="date")
        if policy == "order_by":
            return value.over("asset", order_by=[mask, "date"])
        return value.over("asset", order_by="date")
    expected = frame.with_columns(window(pl.col("close").rolling_mean(2), ["close"]).alias("first"))
    expected = expected.with_columns(window(pl.col("first").rolling_mean(3), ["first"]).alias("out"))
    assert_frame_equal(actual.select("asset", "date", "out"), expected.select("asset", "date", "out"))


@pytest.mark.parametrize("skip_simplify", [False, True])
def test_shared_windows_do_not_cross_null_directives(skip_simplify):
    frame = pl.DataFrame({"asset": ["A"] * 10, "date": list(range(10)),
        "close": [1., 2., None, 4., 5., 6., 7., 8., 9., 10.]})
    sources = ["out_a = ts_mean(ts_mean(close, 2), 3)",
               "out_b = ts_mean(ts_mean(close, 2), 3) # --over_null"]
    def run(source):
        return codegen_exec(frame.lazy(), source, extra_codes="", over_null="order_by",
                            skip_simplify=skip_simplify).collect()
    batch = run("\n".join(sources))
    for name, source in zip(["out_a", "out_b"], sources):
        assert_frame_equal(batch.select("asset", "date", name), run(source).select("asset", "date", name))
    assert batch["out_a"].null_count() != batch["out_b"].null_count()


def test_cse_symbols_do_not_shadow_input_columns():
    frame = pl.DataFrame({"asset": ["A"] * 8, "date": list(range(8)),
                          "_x_0": [float(i) for i in range(8)]})
    actual = execute(frame, "out = ts_mean(ts_mean(_x_0, 2), 3)", None)
    expected = frame.with_columns(pl.col("_x_0").rolling_mean(2).alias("inner")).with_columns(
        pl.col("inner").rolling_mean(3).alias("out"))
    assert_frame_equal(actual.select("asset", "date", "out"), expected.select("asset", "date", "out"))
