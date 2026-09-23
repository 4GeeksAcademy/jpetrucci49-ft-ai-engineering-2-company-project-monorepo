#!/usr/bin/env python3
"""Index HealthCore policy documents into Qdrant collection healthcore_knowledge."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.process.rag import COLLECTION, setup  # noqa: E402


def main() -> int:
    count = setup()
    print(f"Indexed {count} chunks into {COLLECTION}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"index_knowledge: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
