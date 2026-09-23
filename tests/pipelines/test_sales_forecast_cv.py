"""Temporal CV chronology tests for the HealthCore sales-forecast evaluation.

Uses ``data/raw/healthcore_sales.csv``. No API or Prefect. 2024–2025 stay out of CV.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from data.process.sales_forecast import TARGET_COLUMN, TEST_START
from data.process.sales_forecast_eval import (
    N_SPLITS,
    iter_prefix_folds,
    load_cv_universe,
    temporal_fold_splits,
)


def test_timeseries_split_preserves_chronological_order() -> None:
    train_raw = load_cv_universe()
    assert (train_raw["month"] < TEST_START).all()
    assert train_raw["month"].is_monotonic_increasing

    folds = temporal_fold_splits(train_raw)
    assert len(folds) == N_SPLITS
    assert N_SPLITS == 5

    previous_val_min: int | None = None
    for fold in folds:
        train_idx = fold.train_idx
        val_idx = fold.val_idx
        assert np.all(np.diff(train_idx) > 0)
        assert np.all(np.diff(val_idx) > 0)
        assert int(train_idx.max()) < int(val_idx.min())
        assert fold.train_months.max() < fold.val_months.min()
        if previous_val_min is not None:
            assert int(val_idx.min()) > previous_val_min
        previous_val_min = int(val_idx.min())


def test_prefix_fold_lag_does_not_use_future_months() -> None:
    train_raw = load_cv_universe()
    by_month = train_raw.set_index("month")[TARGET_COLUMN]
    checked = False
    for fold, fold_train, fold_val in iter_prefix_folds(train_raw):
        assert fold_train["month"].max() < fold_val["month"].min()
        assert fold_val["month"].max() == fold.val_months.max()
        row = fold_val.iloc[0]
        month = pd.Timestamp(row["month"])
        previous = month - pd.offsets.MonthBegin(1)
        assert previous <= month
        assert previous <= fold.val_months.max()
        if previous in by_month.index:
            assert row["revenue_lag_1"] == by_month.loc[previous]
            checked = True
    assert checked
