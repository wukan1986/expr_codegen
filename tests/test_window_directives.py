"""Check generated windows against separately materialized Polars expressions."""
from io import StringIO

import polars as pl
from polars.testing import assert_frame_equal
import pytest

from expr_codegen import codegen_exec


@pytest.fixture
def bars():
    return pl.DataFrame({
        "row_id": list(range(12)), "asset": ["A"] * 6 + ["B"] * 6,
        "date": list(range(6)) * 2,
        "close": [1., 2., None, 4., 5., 6., 11., None, 13., 14., 15., 16.],
        "high": [2., 3., 6., 8., None, 9., 3., 7., None, 9., 6., 4.],
    }).reverse()


def mean(frame, column, policy, output):
    value = pl.col(column).rolling_mean(2)
    if policy == "partition_by":
        value = value.over(pl.col(column).is_not_null(), "asset", order_by="date")
    elif policy == "order_by":
        value = value.over("asset", order_by=[pl.col(column).is_not_null(), "date"])
    else:
        value = value.over("asset", order_by="date")
    return frame.with_columns(value.alias(output))


def check(frame, source, expected, columns, policy, skip_simplify=False, extra_codes="", **axes):
    generated = StringIO()
    result = codegen_exec(frame.lazy(), source, extra_codes=extra_codes, output_file=generated,
                          over_null=policy, skip_simplify=skip_simplify, **axes).collect()
    assert generated.getvalue()
    selected = ["row_id", *columns]
    assert_frame_equal(result.select(selected).sort("row_id"),
                       expected.select(selected).sort("row_id"))


@pytest.mark.parametrize("policy", ["partition_by", "order_by"])
@pytest.mark.parametrize("skip_simplify", [False, True])
@pytest.mark.parametrize("case", ["default", "explicit", "nested"])
def test_independent_outputs_keep_their_null_policies(bars, policy, skip_simplify, case):
    if case == "default":
        source = ("out = ts_mean(close, 2) + ts_mean(high, 2) # --over_null=None\n"
                  "other = ts_mean(close, 2) #")
        expected = mean(mean(mean(bars, "close", None, "left"), "high", None, "right"),
                        "close", policy, "other")
        expected = expected.with_columns((pl.col("left") + pl.col("right")).alias("out"))
        columns = ["out", "other"]
    elif case == "explicit":
        source = ("a = ts_mean(close, 2) # --over_null=None\n"
                  "b = ts_mean(close, 2) # --over_null=order_by")
        expected = mean(mean(bars, "close", None, "a"), "close", "order_by", "b")
        columns = ["a", "b"]
    else:
        source = ("a = ts_mean(ts_mean(close, 2), 2) #\n"
                  "b = ts_mean(ts_mean(close, 2), 2) # --over_null=None")
        expected = mean(mean(bars, "close", policy, "first"), "first", policy, "a")
        expected = mean(mean(expected, "close", None, "second"), "second", None, "b")
        columns = ["a", "b"]
    check(bars, source, expected, columns, policy, skip_simplify)


@pytest.mark.parametrize("policy", ["partition_by", "order_by", None])
@pytest.mark.parametrize("skip_simplify", [False, True])
@pytest.mark.parametrize("negative", [False, True])
def test_window_alias_keeps_its_explicit_directive(bars, policy, skip_simplify, negative):
    consumer = {None: "partition_by", "partition_by": "order_by", "order_by": None}[policy]
    source = (f"_inner = ts_mean(close, 2) # --over_null={policy}\n"
              f"out = {'-' if negative else ''}_inner # --over_null={consumer}")
    expected = mean(bars, "close", policy, "stage").with_columns(
        (pl.col("stage") * (-1 if negative else 1)).alias("out"))
    check(bars, source, expected, ["out"], consumer, skip_simplify)


@pytest.mark.parametrize("axis", ["date", "asset"])
@pytest.mark.parametrize("skip_simplify", [False, True])
def test_generated_temporaries_do_not_replace_grouping_axes(bars, axis, skip_simplify):
    expected = mean(mean(bars, "close", None, "stage"), "stage", None, "out")
    check(bars.rename({axis: "_x_0"}), "out = ts_mean(ts_mean(close, 2), 2)",
          expected, ["out"], None, skip_simplify, **{axis: "_x_0"})


@pytest.mark.parametrize("policy", ["partition_by", "order_by"])
def test_recursive_directive_propagation_reaches_unannotated_dependencies(bars, policy):
    source = ("first = ts_mean(close, 2) #\n"
              "middle = ts_mean(first, 2) # --over_null=None\n"
              "out = ts_mean(middle, 2) #")
    expected = mean(mean(mean(bars, "close", None, "first"), "first", None, "middle"),
                    "middle", policy, "out")
    check(bars, source, expected, ["first", "middle", "out"], policy)


@pytest.mark.parametrize("policy, inherited", [("partition_by", None), ("order_by", None), (None, "partition_by")])
@pytest.mark.parametrize("skip_simplify", [False, True])
def test_inherited_directive_does_not_change_an_independent_equal_output(bars, policy, inherited, skip_simplify):
    source = ("left = ts_mean(close, 2)\n"
              "right = ts_mean(close, 2)\n"
              f"out = left + 1 # --over_null={inherited}")
    expected = mean(mean(bars, "close", inherited, "left"), "close", policy, "right")
    expected = expected.with_columns((pl.col("left") + 1).alias("out"))
    check(bars, source, expected, ["left", "right", "out"], policy, skip_simplify)


def test_helper_local_window_size_is_a_python_scalar(bars):
    helper = ("def ts_local_mean(value):\n"
              "    period = 2\n"
              "    return value.rolling_mean(period)\n")
    check(bars, "out = ts_local_mean(close)", mean(bars, "close", None, "out"),
          ["out"], None, extra_codes=helper)
