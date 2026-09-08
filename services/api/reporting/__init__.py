"""HTTP surface for the Monthly Clinic Supply Performance pipeline.

Separate from services/api/telemetry/. Imports flows and queries from data/pipelines/.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

def _find_repo_root() -> Path:
    env = os.getenv("HEALTHCORE_REPO_ROOT", "").strip()
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "pipelines" / "pipeline.py").is_file():
            return parent
    docker = Path("/opt/healthcore")
    if (docker / "data" / "pipelines" / "pipeline.py").is_file():
        return docker
    return here.parents[3]


_REPO_ROOT = _find_repo_root()
_API_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_REPO_ROOT), str(_API_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

os.environ.setdefault("PREFECT_CLI_PROMPT", "false")
os.environ["PREFECT_HOME"] = str(_REPO_ROOT / ".prefect")
try:
    from data.pipelines.paths import configure_prefect_runtime

    configure_prefect_runtime()
except Exception:
    pass
