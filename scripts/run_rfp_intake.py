#!/usr/bin/env python3
"""Re-run RFP intake for an existing ticket (dev / smoke). Not a second HTTP API."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "api"
for path in (REPO_ROOT, API_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from inventory.database import init_inventory_schema  # noqa: E402
from data.pipelines.rfp_intake.graph import run_rfp_intake  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Reprocess an RFP intake ticket.")
    parser.add_argument("--ticket-id", required=True, help="Existing rfp_tickets.ticket_id")
    args = parser.parse_args()
    init_inventory_schema()
    result = run_rfp_intake(args.ticket_id)
    status = "intake_complete" if result.get("is_rfp") else "discarded"
    print(f"ticket_id={args.ticket_id} is_rfp={result.get('is_rfp')} outcome={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
