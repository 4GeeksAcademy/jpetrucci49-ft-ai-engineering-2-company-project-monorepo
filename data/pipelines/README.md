# `data/pipelines` folder

This folder groups **all data pipelines in the monorepo** related to the company: ingestion, ETL/ELT, cleaning, transformation, and loading into analytical or production systems.

Each subfolder or file under `data/pipelines/` should represent **one pipeline or job set** (for example `sales-etl`, `telemetry-stream`, `customer-segmentation`) and include the required configuration (scripts, orchestration, connectors, schemas, etc.).

- **Main purpose**: consolidate in one place the data movement and transformation logic that powers the company’s applications and analytics.
- **Recommendation**: document pipelines as you add them—their goal, data sources and sinks, dependencies, and how to run them in development, testing, and production.

## HealthCore pipelines

- [PIPELINE_DESIGN.md](./PIPELINE_DESIGN.md) — Monthly Clinic Supply Performance (Okonkwo / Claire board pack). Prefect 3 flow `monthly_clinic_supply_performance`.
- Entry: `python data/pipelines/pipeline.py` (cron `0 6 1 * *` — 06:00 UTC on the 1st).
- [sales_forecast/README.md](./sales_forecast/README.md) — consolidated monthly `revenue_usd` forecast (XGBoost). CLI: `uv run python scripts/forecast_sales.py`. Eval: `uv run python scripts/evaluate_sales_forecast.py`.

> _Spanish version: [README.es.md](./README.es.md)._
