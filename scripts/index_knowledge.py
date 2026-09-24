#!/usr/bin/env python3
"""Index HealthCore policy documents into Qdrant collection healthcore_knowledge."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / "services" / "api" / ".env", override=True)
except ImportError:
    pass

from data.process.rag import (  # noqa: E402
    COLLECTION,
    qdrant_url,
    rag_api_key,
    setup,
)


def main() -> int:
    target = qdrant_url()
    mode = "API embeddings" if rag_api_key() else "local hashed embeddings"
    count = setup()
    print(f"Indexed {count} chunks into {COLLECTION} at {target} ({mode})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"index_knowledge: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
