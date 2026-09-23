#!/usr/bin/env python3
"""Recall@3 for HealthCore desk-knowledge questions (all four CONTEXT documents)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.pipelines.rag import retrieve  # noqa: E402
from data.process.rag import setup  # noqa: E402

QUERIES = REPO_ROOT / "data" / "eval" / "test-queries.json"
OUT = REPO_ROOT / "data" / "eval" / "rag_recall.json"
MIN_RECALL = 0.80


def _is_hit(row: dict, expected_source: str, needle: str | None) -> bool:
    if row.get("source_document") != expected_source:
        return False
    if needle and needle.lower() not in str(row.get("text", "")).lower():
        return False
    return True


def main() -> int:
    setup()
    questions = json.loads(QUERIES.read_text(encoding="utf-8"))
    hits = 0
    details: list[dict] = []
    for item in questions:
        question = item["question"]
        expected = item["expected_source_document"]
        needle = item.get("expected_text_contains")
        results = retrieve(question, k=3, min_score=0.0)
        matched = any(_is_hit(row, expected, needle) for row in results)
        hits += int(matched)
        details.append(
            {
                "question": question,
                "expected_source_document": expected,
                "hit": matched,
                "top_sources": [row.get("source_document") for row in results],
            }
        )
    n = len(questions)
    recall = hits / n if n else 0.0
    payload = {"hits": hits, "n": n, "recall_at_3": recall, "details": details}
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Recall@3: {hits}/{n} = {recall:.2%}")
    print(f"Wrote {OUT}")
    if recall < MIN_RECALL:
        print(f"index_knowledge: recall {recall:.2%} is below {MIN_RECALL:.0%}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"eval_rag_recall: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
