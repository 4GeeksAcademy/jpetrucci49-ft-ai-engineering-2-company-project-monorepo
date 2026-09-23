#!/usr/bin/env python3
"""Temporal CV + learning curve for the HealthCore consolidated revenue forecast."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.process.sales_forecast_eval import (  # noqa: E402
    CV_METRICS_JSON,
    EVALUATION_REPORT,
    LEARNING_CURVE_PNG,
    plot_learning_curve,
    run_evaluation,
    write_cv_metrics,
    write_evaluation_report,
)


def main() -> int:
    artifacts = run_evaluation()
    json_path = write_cv_metrics(artifacts.summary, artifacts.diagnosis, CV_METRICS_JSON)
    png_path = plot_learning_curve(artifacts.curve, LEARNING_CURVE_PNG)
    report_path = write_evaluation_report(artifacts.report_markdown, EVALUATION_REPORT)

    print("HealthCore sales forecast — train-window evaluation (2016–2023)")
    print(f"  folds: {artifacts.summary['n_splits']}")
    print(
        "  val RMSE (chosen): "
        f"{artifacts.summary['val_rmse_mean']:.0f} ± {artifacts.summary['val_rmse_std']:.0f} USD"
    )
    print(
        "  val MAE: "
        f"{artifacts.summary['val_mae_mean']:.0f} ± {artifacts.summary['val_mae_std']:.0f} USD"
    )
    print(
        "  val RMSE%: "
        f"{artifacts.summary['val_rmse_pct_mean']:.2f}% ± {artifacts.summary['val_rmse_pct_std']:.2f}"
    )
    print(f"  fit: {artifacts.diagnosis.fit}")
    print(f"  stability: {artifacts.diagnosis.stability}")
    print()
    print(f"Wrote {json_path}")
    print(f"Wrote {png_path}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 — CLI: fail closed
        print(f"evaluate_sales_forecast: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
