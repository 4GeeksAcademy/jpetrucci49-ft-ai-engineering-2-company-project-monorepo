"""Train-window evaluation of the 07.2 HealthCore ``revenue_usd`` forecast.

Temporal CV and the learning curve use **2016–2023 only**. 2024–2025 stay the
07.2 holdout. Features and the scaler are fit on each fold's prefix so later
folds cannot leak into earlier ones.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from data.process.sales_forecast import (
    EVAL_DIR,
    FEATURE_COLUMNS,
    SCALE_COLUMNS,
    TARGET_COLUMN,
    TEST_START,
    XGB_PARAMS,
    add_causal_features,
    drop_incomplete_features,
    load_sales,
)

N_SPLITS = 5
LEARNING_CURVE_PNG = EVAL_DIR / "sales_forecast_learning_curve.png"
CV_METRICS_JSON = EVAL_DIR / "sales_forecast_cv_metrics.json"
EVALUATION_REPORT = EVAL_DIR / "evaluation_report.md"
LEARNING_CURVE_PREFIX_MONTHS = (36, 48, 60, 72, 84, 96)
LEARNING_CURVE_VAL_MONTHS = 12


@dataclass(frozen=True)
class FoldSplit:
    """One TimeSeriesSplit fold on the raw 2016–2023 month index."""

    fold: int
    train_idx: np.ndarray
    val_idx: np.ndarray
    train_months: pd.Series
    val_months: pd.Series


@dataclass
class FoldScores:
    fold: int
    n_train: int
    n_val: int
    val_month_start: str
    val_month_end: str
    train_mae: float
    val_mae: float
    train_rmse: float
    val_rmse: float
    val_rmse_pct: float
    train_rmse_pct: float


@dataclass
class LearningCurvePoint:
    n_train: int
    prefix_months: int
    train_rmse: float
    val_rmse: float
    train_mae: float
    val_mae: float


@dataclass
class Diagnosis:
    fit: str
    stability: str
    cv_rmse_ratio: float
    cv_rmse_std_over_mean: float
    action: str


@dataclass
class EvaluationArtifacts:
    folds: list[FoldScores]
    summary: dict[str, Any]
    curve: list[LearningCurvePoint]
    diagnosis: Diagnosis
    report_markdown: str = field(default="")


def make_forecast_pipeline() -> Pipeline:
    """Per-fold scaler on lag/roll columns; calendar features pass through."""
    preprocess = ColumnTransformer(
        transformers=[("scale", StandardScaler(), list(SCALE_COLUMNS))],
        remainder="passthrough",
    )
    return Pipeline(
        [
            ("prep", preprocess),
            ("model", XGBRegressor(**XGB_PARAMS)),
        ]
    )


def load_cv_universe(path: Path | str | None = None) -> pd.DataFrame:
    """Consolidated monthly sales for 2016–2023 only, sorted, 0..n-1 index."""
    sales = load_sales(path)
    train = sales.loc[sales["month"] < TEST_START].sort_values("month")
    return train.reset_index(drop=True)


def temporal_fold_splits(train_raw: pd.DataFrame) -> list[FoldSplit]:
    """``TimeSeriesSplit(n_splits=5)`` on the sorted train-year frame. No shuffle."""
    frame = train_raw.sort_values("month").reset_index(drop=True)
    if (frame["month"] >= TEST_START).any():
        raise ValueError("CV universe must not include 2024–2025")
    splitter = TimeSeriesSplit(n_splits=N_SPLITS)
    folds: list[FoldSplit] = []
    for fold, (train_idx, val_idx) in enumerate(splitter.split(frame)):
        train_idx = np.asarray(train_idx)
        val_idx = np.asarray(val_idx)
        _assert_fold_order(train_idx, val_idx)
        train_months = frame.iloc[train_idx]["month"]
        val_months = frame.iloc[val_idx]["month"]
        if train_months.max() >= val_months.min():
            raise ValueError("fold mixes train and val months")
        folds.append(
            FoldSplit(
                fold=fold,
                train_idx=train_idx,
                val_idx=val_idx,
                train_months=train_months.reset_index(drop=True),
                val_months=val_months.reset_index(drop=True),
            )
        )
    _assert_folds_move_forward(folds)
    return folds


def _assert_fold_order(train_idx: np.ndarray, val_idx: np.ndarray) -> None:
    if train_idx.size == 0 or val_idx.size == 0:
        raise ValueError("empty train or val fold")
    if np.any(np.diff(train_idx) <= 0) or np.any(np.diff(val_idx) <= 0):
        raise ValueError("fold indices are not strictly increasing")
    if int(train_idx.max()) >= int(val_idx.min()):
        raise ValueError("val indices overlap or precede train")


def _assert_folds_move_forward(folds: list[FoldSplit]) -> None:
    for previous, current in zip(folds, folds[1:]):
        if int(current.val_idx.min()) <= int(previous.val_idx.min()):
            raise ValueError("later fold does not move forward in time")


def prefix_featured_split(
    train_raw: pd.DataFrame, fold: FoldSplit
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Causal features on ``month <= val.max`` only — later folds are not in the frame."""
    frame = train_raw.sort_values("month").reset_index(drop=True)
    val_end = pd.Timestamp(fold.val_months.max())
    prefix = frame.loc[frame["month"] <= val_end].copy()
    if (prefix["month"] > val_end).any():
        raise ValueError("prefix includes months after this fold's val window")
    featured = drop_incomplete_features(add_causal_features(prefix))
    train_set = set(pd.to_datetime(fold.train_months))
    val_set = set(pd.to_datetime(fold.val_months))
    fold_train = featured.loc[featured["month"].isin(train_set)].reset_index(drop=True)
    fold_val = featured.loc[featured["month"].isin(val_set)].reset_index(drop=True)
    if fold_train.empty or fold_val.empty:
        raise ValueError(f"fold {fold.fold} has empty train or val after lag dropna")
    if fold_train["month"].max() >= fold_val["month"].min():
        raise ValueError("featured fold mixes train and val months")
    return fold_train, fold_val


def iter_prefix_folds(train_raw: pd.DataFrame) -> Iterator[tuple[FoldSplit, pd.DataFrame, pd.DataFrame]]:
    for fold in temporal_fold_splits(train_raw):
        yield fold, *prefix_featured_split(train_raw, fold)


def _scores(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, float]:
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(root_mean_squared_error(y_true, y_pred))
    mean_rev = float(np.mean(y_true))
    rmse_pct = 100.0 * rmse / mean_rev if mean_rev else math.nan
    return mae, rmse, rmse_pct


def score_fold(fold: FoldSplit, fold_train: pd.DataFrame, fold_val: pd.DataFrame) -> FoldScores:
    pipeline = make_forecast_pipeline()
    x_train = fold_train[list(FEATURE_COLUMNS)]
    x_val = fold_val[list(FEATURE_COLUMNS)]
    y_train = fold_train[TARGET_COLUMN].to_numpy(dtype=float)
    y_val = fold_val[TARGET_COLUMN].to_numpy(dtype=float)
    pipeline.fit(x_train, y_train)
    train_hat = np.asarray(pipeline.predict(x_train), dtype=float)
    val_hat = np.asarray(pipeline.predict(x_val), dtype=float)
    train_mae, train_rmse, train_rmse_pct = _scores(y_train, train_hat)
    val_mae, val_rmse, val_rmse_pct = _scores(y_val, val_hat)
    return FoldScores(
        fold=fold.fold,
        n_train=len(fold_train),
        n_val=len(fold_val),
        val_month_start=pd.Timestamp(fold_val["month"].min()).strftime("%Y-%m-%d"),
        val_month_end=pd.Timestamp(fold_val["month"].max()).strftime("%Y-%m-%d"),
        train_mae=train_mae,
        val_mae=val_mae,
        train_rmse=train_rmse,
        val_rmse=val_rmse,
        val_rmse_pct=val_rmse_pct,
        train_rmse_pct=train_rmse_pct,
    )


def run_temporal_cv(train_raw: pd.DataFrame) -> list[FoldScores]:
    return [score_fold(fold, train, val) for fold, train, val in iter_prefix_folds(train_raw)]


def summarize_cv(folds: list[FoldScores]) -> dict[str, Any]:
    val_rmse = np.array([row.val_rmse for row in folds], dtype=float)
    val_mae = np.array([row.val_mae for row in folds], dtype=float)
    train_rmse = np.array([row.train_rmse for row in folds], dtype=float)
    train_mae = np.array([row.train_mae for row in folds], dtype=float)
    val_rmse_pct = np.array([row.val_rmse_pct for row in folds], dtype=float)
    train_rmse_pct = np.array([row.train_rmse_pct for row in folds], dtype=float)
    return {
        "n_splits": N_SPLITS,
        "chosen_metric": "rmse",
        "val_rmse_mean": float(val_rmse.mean()),
        "val_rmse_std": float(val_rmse.std(ddof=1)),
        "val_mae_mean": float(val_mae.mean()),
        "val_mae_std": float(val_mae.std(ddof=1)),
        "train_rmse_mean": float(train_rmse.mean()),
        "train_rmse_std": float(train_rmse.std(ddof=1)),
        "train_mae_mean": float(train_mae.mean()),
        "train_mae_std": float(train_mae.std(ddof=1)),
        "val_rmse_pct_mean": float(val_rmse_pct.mean()),
        "val_rmse_pct_std": float(val_rmse_pct.std(ddof=1)),
        "train_rmse_pct_mean": float(train_rmse_pct.mean()),
        "folds": [_fold_to_dict(row) for row in folds],
    }


def _fold_to_dict(row: FoldScores) -> dict[str, Any]:
    return {
        "fold": row.fold,
        "n_train": row.n_train,
        "n_val": row.n_val,
        "val_month_start": row.val_month_start,
        "val_month_end": row.val_month_end,
        "train_mae": row.train_mae,
        "val_mae": row.val_mae,
        "train_rmse": row.train_rmse,
        "val_rmse": row.val_rmse,
        "val_rmse_pct": row.val_rmse_pct,
        "train_rmse_pct": row.train_rmse_pct,
    }


def compute_learning_curve(train_raw: pd.DataFrame) -> list[LearningCurvePoint]:
    """Expanding prefix of 2016–2023; last 12 complete months are validation."""
    frame = train_raw.sort_values("month").reset_index(drop=True)
    points: list[LearningCurvePoint] = []
    for prefix_n in LEARNING_CURVE_PREFIX_MONTHS:
        prefix = frame.iloc[:prefix_n]
        featured = drop_incomplete_features(add_causal_features(prefix))
        if len(featured) <= LEARNING_CURVE_VAL_MONTHS + 4:
            continue
        fold_val = featured.iloc[-LEARNING_CURVE_VAL_MONTHS :]
        fold_train = featured.iloc[:-LEARNING_CURVE_VAL_MONTHS]
        pipeline = make_forecast_pipeline()
        pipeline.fit(fold_train[list(FEATURE_COLUMNS)], fold_train[TARGET_COLUMN])
        train_hat = pipeline.predict(fold_train[list(FEATURE_COLUMNS)])
        val_hat = pipeline.predict(fold_val[list(FEATURE_COLUMNS)])
        y_train = fold_train[TARGET_COLUMN].to_numpy(dtype=float)
        y_val = fold_val[TARGET_COLUMN].to_numpy(dtype=float)
        train_mae, train_rmse, _ = _scores(y_train, train_hat)
        val_mae, val_rmse, _ = _scores(y_val, val_hat)
        points.append(
            LearningCurvePoint(
                n_train=len(fold_train),
                prefix_months=prefix_n,
                train_rmse=train_rmse,
                val_rmse=val_rmse,
                train_mae=train_mae,
                val_mae=val_mae,
            )
        )
    if not points:
        raise ValueError("learning curve produced no points")
    return points


def plot_learning_curve(
    points: list[LearningCurvePoint],
    destination: Path | None = None,
) -> Path:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-healthcore")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = Path(destination) if destination is not None else LEARNING_CURVE_PNG
    path.parent.mkdir(parents=True, exist_ok=True)
    xs = [point.n_train for point in points]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(xs, [point.train_rmse for point in points], color="#1f4e5f", marker="o", label="Train RMSE")
    ax.plot(xs, [point.val_rmse for point in points], color="#c45c26", marker="o", label="Validation RMSE")
    ax.set_title("HealthCore consolidated revenue_usd — learning curve (train years 2016–2023)")
    ax.set_xlabel("Training months (after causal-feature dropna)")
    ax.set_ylabel("RMSE (USD)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def diagnose(summary: dict[str, Any], curve: list[LearningCurvePoint]) -> Diagnosis:
    train_rmse = float(summary["train_rmse_mean"])
    val_rmse = float(summary["val_rmse_mean"])
    val_pct = float(summary["val_rmse_pct_mean"])
    train_pct = float(summary["train_rmse_pct_mean"])
    ratio = val_rmse / train_rmse if train_rmse > 0 else math.inf
    std_over_mean = float(summary["val_rmse_std"]) / val_rmse if val_rmse else math.inf
    last = curve[-1]
    gap_persists = last.val_rmse > 2.0 * last.train_rmse

    if ratio > 2.0 and gap_persists:
        fit = "overfitting"
    elif val_pct > 12.0 and train_pct > 12.0 and ratio <= 2.0:
        fit = "underfitting"
    elif ratio < 2.0 and val_pct < 10.0:
        fit = "well fitted"
    elif ratio > 2.0:
        fit = "overfitting"
    else:
        fit = "well fitted"

    stability = "unstable" if std_over_mean > 0.35 else "stable"
    rmse_pct_std = float(summary["val_rmse_pct_std"])
    rmse_pct_mean = float(summary["val_rmse_pct_mean"])
    pct_stable = (rmse_pct_std / rmse_pct_mean) <= 0.35 if rmse_pct_mean else False

    if fit == "overfitting":
        action = (
            f"Cut tree capacity so the model cannot memorize train Jul–Aug / Oct–Dec: "
            f"set `n_estimators=80` and `max_depth=2` (keep `revenue_lag_12` and "
            f"`random_state=42`). Re-run this 5-fold train-only CV; stop when "
            f"val/train RMSE (now {ratio:.1f}×) falls below 2×. Do not retune on "
            f"2024–2025 and do not add same-row visits."
        )
    elif fit == "underfitting":
        action = (
            "Seasonality is not being used: raise `max_depth` to 4, keep "
            "`n_estimators=200` and `revenue_lag_12`, re-run train-only CV. "
            "Do not add same-row `visits_count` or `avg_revenue_per_visit_usd`."
        )
    elif stability == "unstable" and pct_stable:
        action = (
            "USD RMSE moves with CONTEXT 4% growth; RMSE% is flatter. Add a causal "
            "`years_since_2016` from `month` (no future), re-CV, and compare RMSE%. "
            "Do not collect more clinics or touch the holdout."
        )
    elif stability == "unstable":
        action = (
            "Add a causal `years_since_2016` from `month` and re-run 5-fold CV; "
            "success is `val_rmse_std / val_rmse_mean` ≤ 0.35. Do not change the CSV."
        )
    else:
        action = (
            "None — well fitted on the 2016–2023 window. Residual risk is the 07.2 "
            "under-prediction of late-2025 Q4 (growth/level), not a deeper tree."
        )

    return Diagnosis(
        fit=fit,
        stability=stability,
        cv_rmse_ratio=ratio,
        cv_rmse_std_over_mean=std_over_mean,
        action=action,
    )


def render_evaluation_report(
    summary: dict[str, Any],
    curve: list[LearningCurvePoint],
    diagnosis: Diagnosis,
) -> str:
    fold_rows = "\n".join(
        (
            f"| {row['fold']} | {row['n_train']} | {row['n_val']} | "
            f"{row['val_month_start']} – {row['val_month_end']} | "
            f"{row['train_mae']:.0f} | {row['val_mae']:.0f} | "
            f"{row['train_rmse']:.0f} | {row['val_rmse']:.0f} | "
            f"{row['val_rmse_pct']:.2f}% |"
        )
        for row in summary["folds"]
    )
    curve_rows = "\n".join(
        f"| {point.prefix_months} | {point.n_train} | {point.train_rmse:.0f} | {point.val_rmse:.0f} |"
        for point in curve
    )
    last = curve[-1]
    return f"""# HealthCore sales forecast — evaluation report

Audience: **Sandra** (dashboard go/no-go) and **Tom** (USD). Aggregated monthly `revenue_usd` only — no patient-level data.

Universe: `data/raw/healthcore_sales.csv`, `region == "consolidated"`, train years **2016–2023**. The 2024–2025 holdout is not used in CV or the learning curve.

Artifacts: [`sales_forecast_learning_curve.png`](./sales_forecast_learning_curve.png), [`sales_forecast_cv_metrics.json`](./sales_forecast_cv_metrics.json). Regenerate with `uv run python scripts/evaluate_sales_forecast.py`.

---

## 1. Fit

**Classification: {diagnosis.fit}**

5-fold `TimeSeriesSplit` (no shuffle), prefix-only causal features, scaler fit on fold-train:

| Split | MAE (USD) | RMSE (USD) | RMSE % of fold-val mean `revenue_usd` |
| --- | ---: | ---: | ---: |
| Train (mean ± std) | {summary['train_mae_mean']:.0f} ± {summary['train_mae_std']:.0f} | {summary['train_rmse_mean']:.0f} ± {summary['train_rmse_std']:.0f} | {summary['train_rmse_pct_mean']:.2f}% |
| Validation (mean ± std) | {summary['val_mae_mean']:.0f} ± {summary['val_mae_std']:.0f} | {summary['val_rmse_mean']:.0f} ± {summary['val_rmse_std']:.0f} | {summary['val_rmse_pct_mean']:.2f}% ± {summary['val_rmse_pct_std']:.2f} |

Val / train RMSE ratio: **{diagnosis.cv_rmse_ratio:.2f}×**.

Learning curve (expanding 2016–2023 prefix; last 12 months of each prefix as val):

| Prefix months | Train *n* | Train RMSE | Val RMSE |
| ---: | ---: | ---: | ---: |
{curve_rows}

At the largest prefix, train RMSE is {last.train_rmse:.0f} USD and val RMSE is {last.val_rmse:.0f} USD. The train line stays far below the val line as *n* grows — the 07.2 `XGBRegressor` (`max_depth=3`, `n_estimators=200`, `random_state=42`) can memorize train Jul–Aug / Oct–Dec rather than only the CONTEXT seasonal shape.

---

## 2. Stability

How performance moves when the **training portion** changes (same 5 folds):

| Fold | *n* train | *n* val | Val window | Train MAE | Val MAE | Train RMSE | Val RMSE | Val RMSE% |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
{fold_rows}

Chosen metric **RMSE**: **{summary['val_rmse_mean']:.0f} ± {summary['val_rmse_std']:.0f}** USD (`std/mean` = {diagnosis.cv_rmse_std_over_mean:.2f}).

**Stability: {diagnosis.stability}** ({'std/mean > 0.35' if diagnosis.stability == 'unstable' else 'std/mean ≤ 0.35'}).

CONTEXT §4: annual growth alternates about 2–6% and the level rises. Later folds sit on higher `revenue_usd`. If USD RMSE climbs but **RMSE%** stays in a narrower band ({summary['val_rmse_pct_mean']:.2f}% ± {summary['val_rmse_pct_std']:.2f}), that is **scale**, not a shuffle bug.

---

## 3. MAE vs RMSE

**Primary metric: RMSE** (and RMSE as % of that fold’s mean `revenue_usd`).

CONTEXT §3 asks Tom and Sandra to read error as a **percentage of average monthly revenue** — both MAE and RMSE are USD, then divided by mean `revenue_usd`. Sandra’s cost is missing an **atypical August drop** (capacity) versus a normal low season; Oct–Dec is **+15–20%** and Jul–Aug **−12–18%**. Those tails dominate the dollar miss. RMSE weights a missed flu-season peak or a capacity collapse more than a typical ±5% month. MAE is reported as the typical-month companion; it is not the go/no-go number.

---

## 4. Action

**{diagnosis.action}**

Success check (if a knob changes): re-run `scripts/evaluate_sales_forecast.py` only — val/train RMSE ratio < 2 and val RMSE% still in single digits. Do not fit that change on 2024–2025.
"""


def write_cv_metrics(summary: dict[str, Any], diagnosis: Diagnosis, destination: Path | None = None) -> Path:
    path = Path(destination) if destination is not None else CV_METRICS_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **summary,
        "diagnosis": diagnosis.fit,
        "stability": diagnosis.stability,
        "cv_rmse_ratio": diagnosis.cv_rmse_ratio,
        "cv_rmse_std_over_mean": diagnosis.cv_rmse_std_over_mean,
        "action": diagnosis.action,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def write_evaluation_report(markdown: str, destination: Path | None = None) -> Path:
    path = Path(destination) if destination is not None else EVALUATION_REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def run_evaluation(csv_path: Path | str | None = None) -> EvaluationArtifacts:
    train_raw = load_cv_universe(csv_path)
    folds = run_temporal_cv(train_raw)
    summary = summarize_cv(folds)
    curve = compute_learning_curve(train_raw)
    diagnosis = diagnose(summary, curve)
    report = render_evaluation_report(summary, curve, diagnosis)
    return EvaluationArtifacts(
        folds=folds,
        summary=summary,
        curve=curve,
        diagnosis=diagnosis,
        report_markdown=report,
    )
