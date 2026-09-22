# HealthCore sales forecast (consolidated monthly revenue)

Sandra needs a credible next-month revenue signal before funding a network dashboard. Marcus and Tom already see the seasonal pattern; this pipeline fits one tree model on **`revenue_usd`** for **`region == "consolidated"`**.

Source: `data/raw/healthcore_sales.csv` (CONTEXT columns only). No patient identifiers.

## Run

```bash
uv sync
uv run python scripts/forecast_sales.py
```

Writes `data/eval/sales_forecast_metrics.json` and `data/eval/sales_forecast_test.png`. Regenerate the plot by re-running the script.

Logic lives in `data/process/sales_forecast.py` (not in the CLI). Tests: `uv run python -m pytest tests/pipelines/test_sales_forecast.py -q`.

## Algorithm

**XGBoost** (`XGBRegressor`, `random_state=42`).

| Criterion | Why XGBoost here |
| --- | --- |
| Data size | ~96 training months after the 8-year cut; a deep linear/ARIMA search is more tuning than the sample justifies. |
| Explainability | `feature_importances_` is enough for Tom/Sandra (lags vs calendar). |
| Time to tune | Modest `max_depth` (3) and `n_estimators` (200). |

Not Random Forest: the assignment asks for one model; `xgboost` is already in the root `pyproject.toml`.

Features (all causal): `revenue_lag_1`, `revenue_lag_12`, `revenue_roll_mean_3` (`shift(1)` then `rolling(3)`), `visits_lag_1`, `month_num`, `month_sin`, `month_cos`. Same-row `visits_count` and `avg_revenue_per_visit_usd` are excluded (concurrent with the target). Lag/roll columns are `StandardScaler`-fit on **train only**.

Split: train `2016-01`–`2023-12`, test `2024-01`–`2025-12`.

## Decompose vs CONTEXT §4

`seasonal_decompose` is **additive**, `period=12`, on **train revenue only** so 2024–2025 do not colour the story.

| CONTEXT | What we check |
| --- | --- |
| Annual growth `X=4%`, `Y=2%` (always +2–6%) | YoY change in yearly mean `revenue_usd` |
| Jul–Aug −12–18% vs average | Calendar-month lift vs train mean |
| Oct–Dec +15–20% vs average | Same |

On the 2016–2023 train window the CLI last printed:

- YoY mean-revenue growth always **positive**, alternating high/low as CONTEXT describes. A couple of years sit just outside 2–6% (about 1.2% and 6.9%) because we measure yearly **means of monthly totals**, not the generator’s exact `d`.
- **Jul–Aug** about **−17%** (inside −12 to −18%).
- **Oct–Dec** about **+15–16%**; December is just under +15%.

Signs match CONTEXT §4. The CSV was generated with `random_state=42`; we do not regenerate it.

## Metrics (test set)

Low **MSE** alone is not enough: it is scale-dependent (USD²) and a model that always predicts the mean can look “close” in dollars while failing to rank August vs an atypical drop, or while the visit mix has shifted.

| Metric | What it measures | Why Sandra / Tom care |
| --- | --- | --- |
| **MSE** | Mean squared error in **USD²**. Also **RMSE / mean test revenue × 100** (`mse_pct_of_avg_revenue`) so the error is a % of average monthly revenue. | Dollar miss, in language finance already uses. |
| **PSI** | Population Stability Index, 10 equal-width bins from **train**. Primary: `visits_count` train vs test (visit-volume shift). Also `revenue_usd` train vs test. | CONTEXT’s US/UK mix check. **This file has only `consolidated` rows**, so PSI cannot see a 75/25 US/UK mix change; `visits_count` is the available proxy. A high PSI here is mostly the **4% growth trend** (test years sit to the right of train), not evidence of a new clinic. |
| **Gini** | `2 × AUC − 1` after splitting test actuals at the median. Ranking quality, not dollar error. | Distinguish a normal August low-season month from an atypical drop (capacity). |
| **K2 Score** | Assignment name for the two-sample **KS statistic** (`ks_2samp(y_test, y_pred)`). | Distance between actual and predicted distributions. |

## Plot

`data/eval/sales_forecast_test.png`: 2024–2025 actual `revenue_usd` vs prediction, band = predicted ± 1.96 × **train** residual standard deviation.

Spec: `specs/07.2_TIMESERIES_SPECS.md`. Context: `context/07_CONTEXT.md`.
