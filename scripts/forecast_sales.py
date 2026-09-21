#!/usr/bin/env python3
"""Train HealthCore consolidated monthly ``revenue_usd`` forecast (XGBoost)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.process.sales_forecast import (  # noqa: E402
    PLOT_PNG,
    run_forecast,
    plot_test_forecast,
    write_metrics,
)


def main() -> int:
    artifacts = run_forecast()
    residual_std = float(
        (artifacts.train["revenue_usd"].to_numpy() - artifacts.y_train_pred).std()
    )
    metrics_path = write_metrics(artifacts.metrics)
    plot_path = plot_test_forecast(
        artifacts.test,
        artifacts.y_test_pred,
        residual_std,
        PLOT_PNG,
    )

    print("HealthCore sales forecast — consolidated revenue_usd")
    print(f"  train rows (after lag dropna): {len(artifacts.train)}")
    print(f"  test rows (2024-2025):         {len(artifacts.test)}")
    print()
    print("Decompose (train only, additive period=12)")
    print(f"  {artifacts.decompose.summary}")
    print()
    print("Test metrics")
    print(f"  MSE (USD²) .................. {artifacts.metrics['mse']:.2f}")
    print(
        "  MSE as % of avg monthly rev . "
        f"{artifacts.metrics['mse_pct_of_avg_revenue']:.2f}%"
    )
    print(f"  PSI (visits_count) .......... {artifacts.metrics['psi_visits_count']:.4f}")
    print(f"  PSI (revenue_usd) ........... {artifacts.metrics['psi_revenue_usd']:.4f}")
    print(f"  Gini ........................ {artifacts.metrics['gini']:.4f}")
    print(f"  K2 Score (KS) ............... {artifacts.metrics['k2_score']:.4f}")
    print()
    print("Feature importances")
    for name, value in sorted(
        artifacts.feature_importances.items(), key=lambda item: item[1], reverse=True
    ):
        print(f"  {name:22} {value:.4f}")
    print()
    print(f"Wrote {metrics_path}")
    print(f"Wrote {plot_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 — CLI: fail closed with a clear message
        print(f"forecast_sales: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
