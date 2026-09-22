# HealthCore sales forecast — evaluation report

Audience: **Sandra** (dashboard go/no-go) and **Tom** (USD). Aggregated monthly `revenue_usd` only — no patient-level data.

Universe: `data/raw/healthcore_sales.csv`, `region == "consolidated"`, train years **2016–2023**. The 2024–2025 holdout is not used in CV or the learning curve.

Artifacts: [`sales_forecast_learning_curve.png`](./sales_forecast_learning_curve.png), [`sales_forecast_cv_metrics.json`](./sales_forecast_cv_metrics.json). Regenerate with `uv run python scripts/evaluate_sales_forecast.py`.

---

## 1. Fit

**Classification: overfitting**

5-fold `TimeSeriesSplit` (no shuffle), prefix-only causal features, scaler fit on fold-train:

| Split | MAE (USD) | RMSE (USD) | RMSE % of fold-val mean `revenue_usd` |
| --- | ---: | ---: | ---: |
| Train (mean ± std) | 2781 ± 3456 | 3643 ± 4590 | 0.14% |
| Validation (mean ± std) | 160709 ± 30983 | 189384 ± 35092 | 6.75% ± 1.38 |

Val / train RMSE ratio: **51.98×**.

Learning curve (expanding 2016–2023 prefix; last 12 months of each prefix as val):

| Prefix months | Train *n* | Train RMSE | Val RMSE |
| ---: | ---: | ---: | ---: |
| 36 | 12 | 119 | 101526 |
| 48 | 24 | 412 | 171144 |
| 60 | 36 | 1999 | 147921 |
| 72 | 48 | 4387 | 160759 |
| 84 | 60 | 7956 | 175542 |
| 96 | 72 | 11493 | 211825 |

At the largest prefix, train RMSE is 11493 USD and val RMSE is 211825 USD. The train line stays far below the val line as *n* grows — the 07.2 `XGBRegressor` (`max_depth=3`, `n_estimators=200`, `random_state=42`) can memorize train Jul–Aug / Oct–Dec rather than only the CONTEXT seasonal shape.

---

## 2. Stability

How performance moves when the **training portion** changes (same 5 folds):

| Fold | *n* train | *n* val | Val window | Train MAE | Val MAE | Train RMSE | Val RMSE | Val RMSE% |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 4 | 16 | 2017-05-01 – 2018-08-01 | 18 | 176355 | 24 | 213074 | 8.68% |
| 1 | 20 | 16 | 2018-09-01 – 2019-12-01 | 281 | 153672 | 357 | 174672 | 6.34% |
| 2 | 36 | 16 | 2020-01-01 – 2021-04-01 | 1547 | 109489 | 1999 | 135166 | 4.83% |
| 3 | 52 | 16 | 2021-05-01 – 2022-08-01 | 3654 | 179344 | 4669 | 202376 | 6.98% |
| 4 | 68 | 16 | 2022-09-01 – 2023-12-01 | 8403 | 184684 | 11167 | 221629 | 6.92% |

Chosen metric **RMSE**: **189384 ± 35092** USD (`std/mean` = 0.19).

**Stability: stable** (std/mean ≤ 0.35).

CONTEXT §4: annual growth alternates about 2–6% and the level rises. Later folds sit on higher `revenue_usd`. If USD RMSE climbs but **RMSE%** stays in a narrower band (6.75% ± 1.38), that is **scale**, not a shuffle bug.

---

## 3. MAE vs RMSE

**Primary metric: RMSE** (and RMSE as % of that fold’s mean `revenue_usd`).

CONTEXT §3 asks Tom and Sandra to read error as a **percentage of average monthly revenue** — both MAE and RMSE are USD, then divided by mean `revenue_usd`. Sandra’s cost is missing an **atypical August drop** (capacity) versus a normal low season; Oct–Dec is **+15–20%** and Jul–Aug **−12–18%**. Those tails dominate the dollar miss. RMSE weights a missed flu-season peak or a capacity collapse more than a typical ±5% month. MAE is reported as the typical-month companion; it is not the go/no-go number.

---

## 4. Action

**Cut tree capacity so the model cannot memorize train Jul–Aug / Oct–Dec: set `n_estimators=80` and `max_depth=2` (keep `revenue_lag_12` and `random_state=42`). Re-run this 5-fold train-only CV; stop when val/train RMSE (now 52.0×) falls below 2×. Do not retune on 2024–2025 and do not add same-row visits.**

Success check (if a knob changes): re-run `scripts/evaluate_sales_forecast.py` only — val/train RMSE ratio < 2 and val RMSE% still in single digits. Do not fit that change on 2024–2025.
