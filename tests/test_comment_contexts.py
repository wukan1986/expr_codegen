"""Compare directive propagation with separately materialized Polars windows."""
import polars as pl
from polars.testing import assert_frame_equal
import pytest

from expr_codegen.tool import codegen_exec


SOURCES = {
    "mixed_default": (
        "out = ts_mean(close, 2) + ts_mean(high, 2) # --over_null=None\n"
        "other = ts_mean(close, 2) #"),
    "mixed_explicit": (
        "a = ts_mean(close, 2) # --over_null=None\n"
        "b = ts_mean(close, 2) # --over_null=order_by"),
    "common_input": (
        "first = ts_mean((close+high)*(close+low),2) + ts_mean((close+high)*(close+volume),2) # --over_null=None\n"
        "second = ts_mean(open,2) + ts_mean(open,3) # --over_null=partition_by"),
    "nested": "out = ts_mean(ts_mean(ts_mean(close,2),2),2) # --over_null=None",
    "intermediate": "_inner = ts_mean(close,2) # --over_null=None\nout = _inner",
    "named_default_producer": (
        "inner = ts_mean(close,2) #\n"
        "out = ts_mean(inner,2) # --over_null=None\n"
        "other = inner #"),
}


@pytest.fixture
def frame():
    return pl.DataFrame({
        "asset": ["A"] * 10 + ["B"] * 10, "date": list(range(10)) * 2,
        "close": [1., 2., None, 4., 5., 6., 7., 8., 9., 10., 11., 12., 13., 14., None, 16., 17., 18., 19., 20.],
        "high": [float(i + 2) for i in range(20)],
        "low": [float(i + .5) for i in range(20)],
        "volume": [float(i + 5) for i in range(20)],
        "open": [1., 2., 3., None, 5., 6., 7., None, 9., 10., 11., None, 13., 14., 15., 16., 17., 18., 19., 20.],
    })


def mean(frame, column, window, policy, output):
    value = pl.col(column).rolling_mean(window)
    if policy == "partition_by":
        value = value.over(pl.col(column).is_not_null(), "asset", order_by="date")
    elif policy == "order_by":
        value = value.over("asset", order_by=[pl.col(column).is_not_null(), "date"])
    else:
        value = value.over("asset", order_by="date")
    return frame.with_columns(value.alias(output))


def expected(frame, case, default_policy):
    if case == "mixed_default":
        frame = mean(mean(frame, "close", 2, None, "_c"), "high", 2, None, "_h")
        frame = mean(frame, "close", 2, default_policy, "other")
        return frame.with_columns((pl.col("_c") + pl.col("_h")).alias("out")), ["out", "other"]
    if case == "mixed_explicit":
        return mean(mean(frame, "close", 2, None, "a"), "close", 2, "order_by", "b"), ["a", "b"]
    if case == "named_default_producer":
        frame = mean(mean(frame, "close", 2, default_policy, "inner"), "inner", 2, None, "out")
        return frame.with_columns(pl.col("inner").alias("other")), ["inner", "out", "other"]
    if case == "common_input":
        frame = frame.with_columns(
            ((pl.col("close") + pl.col("high")) * (pl.col("close") + pl.col("low"))).alias("_p"),
            ((pl.col("close") + pl.col("high")) * (pl.col("close") + pl.col("volume"))).alias("_q"))
        frame = mean(mean(frame, "_p", 2, None, "_p_mean"), "_q", 2, None, "_q_mean")
        frame = mean(mean(frame, "open", 2, "partition_by", "_o2"), "open", 3, "partition_by", "_o3")
        return frame.with_columns((pl.col("_p_mean") + pl.col("_q_mean")).alias("first"),
                                  (pl.col("_o2") + pl.col("_o3")).alias("second")), ["first", "second"]
    frame = mean(frame, "close", 2, None, "out")
    if case == "nested":
        frame = mean(mean(frame, "out", 2, None, "_second"), "_second", 2, None, "out")
    return frame, ["out"]


@pytest.mark.parametrize("policy", ["partition_by", "order_by"])
@pytest.mark.parametrize("skip_simplify", [False, True])
@pytest.mark.parametrize("case", SOURCES)
def test_comment_contexts_match_materialized_windows(frame, case, skip_simplify, policy):
    result = codegen_exec(frame.lazy(), SOURCES[case], extra_codes="", over_null=policy,
                          skip_simplify=skip_simplify).collect()
    reference, columns = expected(frame, case, policy)
    selected = ["asset", "date", *columns]
    assert_frame_equal(result.select(selected).sort(["asset", "date"]),
                       reference.select(selected).sort(["asset", "date"]))
