# `data/eval` folder

This folder is for **evaluation and validation**: evaluation datasets, golden sets, experiment results, metrics, and artifacts used to measure quality for models, RAG, agents, or pipelines.

Sales forecast (7.2): `sales_forecast_metrics.json` and `sales_forecast_test.png` from `uv run python scripts/forecast_sales.py`.

Sales forecast evaluation (7.3): `sales_forecast_cv_metrics.json`, `sales_forecast_learning_curve.png`, and `evaluation_report.md` from `uv run python scripts/evaluate_sales_forecast.py` (2016–2023 only).

Desk knowledge (7.5): `test-queries.json` and `rag_recall.json` from `uv run python scripts/eval_rag_recall.py`.

- **Main purpose**: centralize evaluation inputs and outputs so improvements stay measurable across project milestones.
- **Recommendation**: document each evaluation set (what it measures, how it was built, success criteria) and avoid sensitive data; use synthetic or anonymized data when needed.

> _Spanish version: [README.es.md](./README.es.md)._
