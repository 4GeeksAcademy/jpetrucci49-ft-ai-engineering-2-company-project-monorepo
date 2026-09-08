"""CLI entry for Monthly Clinic Supply Performance.

Schedule: 06:00 UTC on the 1st of each month (first working day board pack).
Run: python data/pipelines/pipeline.py
     python data/pipelines/pipeline.py --month-start 2026-08-01
See data/pipelines/PIPELINE_DESIGN.md §3.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.pipelines.paths import ensure_import_paths  # noqa: E402

ensure_import_paths()
os.environ.setdefault("PREFECT_API_ENABLE_METRICS", "false")

from data.pipelines.monthly_clinic_supply_performance.flow import (  # noqa: E402
    run_monthly_clinic_supply_performance,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run HealthCore monthly_clinic_supply_performance (Prefect 3)."
    )
    parser.add_argument(
        "--month-start",
        default=None,
        help="UTC month as YYYY-MM-DD (defaults to the previous calendar month).",
    )
    parser.add_argument(
        "--no-sample",
        action="store_true",
        help="Do not fall back to data/raw/telemetry_events_sample.json if extract fails.",
    )
    args = parser.parse_args(argv)
    result = run_monthly_clinic_supply_performance(
        month_start=args.month_start,
        allow_sample=not args.no_sample,
    )
    print(json.dumps(result, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
