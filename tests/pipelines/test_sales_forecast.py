"""Split and causal-feature tests for the HealthCore sales forecast.

Uses ``data/raw/healthcore_sales.csv`` (CONTEXT column names). No API or Prefect.
"""

from __future__ import annotations

import pandas as pd

from data.process.sales_forecast import (
    FEATURE_COLUMNS,
    SERIES_END,
    SERIES_START,
    TARGET_COLUMN,
    TEST_START,
    add_causal_features,
    drop_incomplete_features,
    load_sales,
    split_train_test_8_2,
)


def test_sales_series_is_complete_and_positive() -> None:
    sales = load_sales()
    expected = pd.date_range(SERIES_START, SERIES_END, freq="MS")
    assert len(sales) == 120
    assert sales["month"].tolist() == list(expected)
    assert (sales[TARGET_COLUMN] > 0).all()
    assert (sales["region"] == "consolidated").all()


def test_train_test_split_eight_and_two_years() -> None:
    featured = add_causal_features(load_sales())
    train, test = split_train_test_8_2(featured)

    assert len(train) == 96
    assert len(test) == 24
    assert train["month"].min() == SERIES_START
    assert train["month"].max() == pd.Timestamp("2023-12-01")
    assert test["month"].min() == TEST_START
    assert test["month"].max() == SERIES_END
    assert train["month"].max() < test["month"].min()
    assert set(train["month"]).isdisjoint(set(test["month"]))

    test_after_dropna = drop_incomplete_features(test)
    assert len(test_after_dropna) == 24
    assert test_after_dropna[list(FEATURE_COLUMNS)].notna().all().all()


def test_lag_and_rolling_are_causal() -> None:
    sales = load_sales()
    featured = add_causal_features(sales)
    row = featured.loc[featured["month"] == pd.Timestamp("2018-01-01")].iloc[0]
    by_month = sales.set_index("month")[TARGET_COLUMN]

    assert row["revenue_lag_1"] == by_month.loc[pd.Timestamp("2017-12-01")]
    assert row["revenue_lag_12"] == by_month.loc[pd.Timestamp("2017-01-01")]
    expected_roll = float(
        by_month.loc[
            [
                pd.Timestamp("2017-12-01"),
                pd.Timestamp("2017-11-01"),
                pd.Timestamp("2017-10-01"),
            ]
        ].mean()
    )
    assert row["revenue_roll_mean_3"] == expected_roll
    assert row["revenue_lag_1"] != row[TARGET_COLUMN]
    assert row["revenue_roll_mean_3"] != row[TARGET_COLUMN]
