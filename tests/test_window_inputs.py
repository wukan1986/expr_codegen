"""Window results depend on their actual inputs and the producer's null policy."""

import polars as pl
from polars.testing import assert_frame_equal
import pytest

from expr_codegen import codegen_exec


POLICIES = ["partition_by", "order_by", None]


@pytest.fixture
def bars():
    return pl.DataFrame({
        "row_id": list(range(20)),
        "asset": ["A"] * 10 + ["B"] * 10,
        "date": list(range(10)) * 2,
        "close": [1., 2., None, 4., 5., 6., 7., 8., 9., 10.,
                  11., None, 13., 14., 15., 16., 17., 18., 19., 20.],
        "high": [2., 3., 6., 8., 4., None, 9., 7., 10., 5.,
                 3., 7., None, 9., 6., 4., 2., 8., 5., 10.],
    }).reverse()


def execute(frame, source, policy, skip_simplify, **axes):
    return codegen_exec(
        frame.lazy(), source, extra_codes="", over_null=policy,
        skip_simplify=skip_simplify, **axes,
    ).collect()


def window(value, inputs, policy):
    """Independent Polars oracle, after each input expression is materialized."""
    valid = pl.all_horizontal([pl.col(name).is_not_null() for name in inputs])
    if policy == "partition_by":
        return value.over(valid, "asset", order_by="date")
    if policy == "order_by":
        return value.over("asset", order_by=[valid, "date"])
    return value.over("asset", order_by="date")


def assert_output(actual, expected):
    # Keep an independent row identifier: private axis names need not survive
    # the existing final projection that drops names beginning with "_".
    assert_frame_equal(
        actual.select("row_id", "out").sort("row_id"),
        expected.select("row_id", "out").sort("row_id"),
    )


@pytest.mark.parametrize("axis", ["date", "asset"])
@pytest.mark.parametrize("skip_simplify", [False, True])
def test_temporary_names_do_not_overwrite_custom_axes(bars, axis, skip_simplify):
    expected = bars.with_columns(
        window(pl.col("close").rolling_mean(2), ["close"], None).alias("stage")
    ).with_columns(
        window(pl.col("stage").rolling_mean(3), ["stage"], None).alias("out")
    )
    actual = execute(
        bars.rename({axis: "_x_0"}), "out = ts_mean(ts_mean(close, 2), 3)",
        None, skip_simplify, **{axis: "_x_0"},
    )
    assert_output(actual, expected)


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("skip_simplify", [False, True])
@pytest.mark.parametrize("transformation", ["fill", "mask"])
def test_window_uses_transformed_inputs_with_or_without_siblings(
    bars, policy, skip_simplify, transformation,
):
    if transformation == "fill":
        source_input = "fill_null(close, 10)"
        value = pl.col("close").fill_null(10)
    else:
        source_input = "if_else(close == 5, None, close)"
        value = pl.when(pl.col("close") == 5).then(None).otherwise(pl.col("close"))
    expected = bars.with_columns(value.alias("actual_input")).with_columns(
        window(pl.col("actual_input").rolling_mean(2), ["actual_input"], policy).alias("out")
    )
    source = f"out = ts_mean({source_input}, 2)"
    for siblings in ("", f"\nother = {source_input}"):
        assert_output(execute(bars, source + siblings, policy, skip_simplify), expected)


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("skip_simplify", [False, True])
def test_binary_window_uses_both_transformed_inputs(bars, policy, skip_simplify):
    expected = bars.with_columns(
        pl.col("close").fill_null(10).alias("left_input"),
        pl.when(pl.col("high") == 4).then(None).otherwise(pl.col("high")).alias("right_input"),
    ).with_columns(
        window(
            pl.rolling_cov("left_input", "right_input", window_size=3, ddof=1),
            ["left_input", "right_input"], policy,
        ).alias("out")
    )
    source = "out = ts_covariance(fill_null(close, 10), if_else(high == 4, None, high), 3, 1)"
    for siblings in ("", "\nleft_copy = fill_null(close, 10)\nright_copy = if_else(high == 4, None, high)"):
        assert_output(execute(bars, source + siblings, policy, skip_simplify), expected)


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("skip_simplify", [False, True])
@pytest.mark.parametrize("transformation", ["fill", "mask"])
def test_outer_window_uses_transformed_inner_window(bars, policy, skip_simplify, transformation):
    expected = bars.with_columns(
        window(pl.col("close").rolling_mean(2), ["close"], policy).alias("inner_value")
    )
    if transformation == "fill":
        source_input = "fill_null(ts_mean(close, 2), 10)"
        value = pl.col("inner_value").fill_null(10)
    else:
        source_input = "if_else(ts_mean(close, 2) == 5.5, None, ts_mean(close, 2))"
        value = pl.when(pl.col("inner_value") == 5.5).then(None).otherwise(pl.col("inner_value"))
    expected = expected.with_columns(value.alias("outer_input")).with_columns(
        window(pl.col("outer_input").rolling_mean(3), ["outer_input"], policy).alias("out")
    )
    source = f"out = ts_mean({source_input}, 3)"
    for siblings in ("", f"\nother = {source_input}"):
        assert_output(execute(bars, source + siblings, policy, skip_simplify), expected)


def directive(policy):
    return " # --over_null" + (f" {policy}" if policy else "")


@pytest.mark.parametrize("producer_policy", POLICIES)
@pytest.mark.parametrize("skip_simplify", [False, True])
@pytest.mark.parametrize("consumer", ["alias", "arithmetic", "window", "negative_chain"])
def test_temporary_keeps_producer_policy_when_consumers_have_another_policy(
    bars, producer_policy, skip_simplify, consumer,
):
    consumer_policy = {None: "partition_by", "partition_by": "order_by", "order_by": None}[producer_policy]
    expected = bars.with_columns(
        window(pl.col("close").rolling_mean(2), ["close"], producer_policy).alias("stage")
    )
    if consumer == "alias":
        source_output, value = "_inner", pl.col("stage")
    elif consumer == "arithmetic":
        source_output, value = "_inner + 1", pl.col("stage") + 1
    elif consumer == "negative_chain":
        source_output, value = "_negative", -pl.col("stage")
    else:
        source_output = "ts_mean(_inner, 3)"
        value = window(pl.col("stage").rolling_mean(3), ["stage"], consumer_policy)
    expected = expected.with_columns(value.alias("out"))
    source = "_inner = ts_mean(close, 2)" + directive(producer_policy)
    if consumer == "negative_chain":
        source += "\n_negative = -_inner" + directive(consumer_policy)
    source += f"\nout = {source_output}" + directive(consumer_policy)
    for siblings in ("", "\nother = _inner + 2"):
        assert_output(execute(bars, source + siblings, consumer_policy, skip_simplify), expected)


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("skip_simplify", [False, True])
def test_window_control_arguments_remain_scalar_values(bars, policy, skip_simplify):
    expected = bars.with_columns(
        window(pl.rolling_cov("close", "high", window_size=3, ddof=1), ["close", "high"], policy).alias("out")
    )
    actual = execute(bars, "out = ts_covariance(close, high, 3, 1)", policy, skip_simplify)
    assert_output(actual, expected)


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("source, period", [
    ("_n = 2\nout = ts_mean(close, _n)", 2),
    ("_n = 2\n_m = _n + 1\nout = ts_mean(close, _m)", 3),
])
def test_scalar_control_aliases_remain_scalar_after_simplification(bars, policy, source, period):
    expected = bars.with_columns(
        window(pl.col("close").rolling_mean(period), ["close"], policy).alias("out")
    )
    assert_output(execute(bars, source, policy, skip_simplify=False), expected)
