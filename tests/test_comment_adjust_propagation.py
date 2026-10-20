"""Regression: explicit over_null must reach unannotated dependencies."""
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


@pytest.mark.parametrize("policy", ["partition_by", "order_by"])
def test_explicit_directive_reaches_unannotated_dependency(bars, policy):
    source = ("first = ts_mean(close, 2) #\n"
              "middle = ts_mean(first, 2) # --over_null=None\n"
              "out = ts_mean(middle, 2) #")
    expected = mean(mean(mean(bars, "close", None, "first"), "first", None, "middle"),
                    "middle", policy, "out")

    generated = StringIO()
    result = codegen_exec(
        bars.lazy(), source, output_file=generated, over_null=policy
    ).collect()

    assert generated.getvalue()
    columns = ["row_id", "first", "middle", "out"]
    assert_frame_equal(
        result.select(columns).sort("row_id"),
        expected.select(columns).sort("row_id"),
    )
