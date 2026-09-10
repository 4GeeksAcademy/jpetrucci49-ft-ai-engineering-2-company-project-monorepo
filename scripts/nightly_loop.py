#!/usr/bin/env python3
"""Compose worker: sleep until 02:05 UTC, then run nightly_export.py.

Not a FastAPI process. Used by the `nightly` service in docker-compose.yml.
Host/dev can use deploy/nightly.crontab instead.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXPORT = _REPO_ROOT / "scripts" / "nightly_export.py"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s job=nightly_export status=scheduler %(message)s",
)
logger = logging.getLogger("nightly_loop")


def seconds_until_next_0205_utc(now: datetime | None = None) -> float:
    current = now or datetime.now(timezone.utc)
    target = current.replace(hour=2, minute=5, second=0, microsecond=0)
    if current >= target:
        target += timedelta(days=1)
    return max(0.0, (target - current).total_seconds())


def main() -> int:
    while True:
        delay = seconds_until_next_0205_utc()
        logger.info("sleeping %.0fs until next 02:05 UTC", delay)
        time.sleep(delay)
        result = subprocess.run(
            [sys.executable, str(_EXPORT)],
            cwd=_REPO_ROOT,
            check=False,
        )
        logger.info("nightly_export.py exited %s", result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
