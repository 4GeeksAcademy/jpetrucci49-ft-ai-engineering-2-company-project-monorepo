# `data/process` folder

Reusable transforms:

- `clinic_dimension.py` — telemetry clinic 1–12 → reporting slugs (`austin-north`, …)
- `inbound_cost.py` — `total_cost` or `quantity × unit_cost`
- `clinic_month_kpis.py` — the four CONTEXT KPIs at clinic × month
- `sales_forecast.py` — causal features, 8/2 split, XGBoost forecast of consolidated `revenue_usd`

This folder contains **processed/intermediate data** and/or artifacts produced by pipelines (for example: clean datasets, features, aggregates, intermediate tables, or transformation outputs).

- **Main purpose**: clearly separate “raw” data from data ready for analysis, modeling, or app consumption.
- **Recommendation**: document which pipeline produces each artifact, its schema, refresh cadence, and how quality is validated (checks, constraints, data tests).

> _Spanish version: [README.es.md](./README.es.md)._
