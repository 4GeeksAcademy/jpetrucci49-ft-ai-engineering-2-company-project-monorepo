"""Repo paths for pipeline I/O. data/raw = extracts; data/eval = validation snapshots."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "services" / "api"
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EVAL_DIR = DATA_DIR / "eval"
PROCESS_DIR = DATA_DIR / "process"
SAMPLE_EVENTS_PATH = RAW_DIR / "telemetry_events_sample.json"
LOCAL_REPORTING_DB = RAW_DIR / "reporting.db"

# Prefect 3 persists cache/results under PREFECT_HOME; keep it inside the repo.
_PREFECT_HOME = REPO_ROOT / ".prefect"


def _in_automated_test() -> bool:
    return (
        "pytest" in sys.modules
        or os.getenv("HEALTHCORE_API_TEST", "").strip().lower() in {"1", "true", "yes"}
        or os.getenv("PYTEST_CURRENT_TEST", "").strip() != ""
    )


def _load_prefect_keys_from_env_file(path: Path) -> None:
    """Fill missing PREFECT_* keys. Does not override a live environment."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key.startswith("PREFECT_") and key and key not in os.environ:
            os.environ[key] = value


def configure_prefect_runtime() -> None:
    """Point Prefect at repo `.prefect/`. Use Cloud when PREFECT_API_URL is set.

    Tests keep the ephemeral server. Do not put API keys in tracked files.
    """
    _PREFECT_HOME.mkdir(parents=True, exist_ok=True)
    (_PREFECT_HOME / "storage").mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PREFECT_CLI_PROMPT", "false")
    os.environ["PREFECT_HOME"] = str(_PREFECT_HOME)
    os.environ.setdefault(
        "PREFECT_RESULTS_LOCAL_STORAGE_PATH", str(_PREFECT_HOME / "storage")
    )
    if _in_automated_test():
        os.environ["PREFECT_SERVER_EPHEMERAL_ENABLED"] = "true"
        return
    _load_prefect_keys_from_env_file(REPO_ROOT / ".env")
    _load_prefect_keys_from_env_file(API_ROOT / ".env")
    api_url = os.getenv("PREFECT_API_URL", "").strip()
    if "prefect.cloud" in api_url:
        os.environ["PREFECT_SERVER_EPHEMERAL_ENABLED"] = "false"


configure_prefect_runtime()


def ensure_import_paths() -> None:
    configure_prefect_runtime()
    for path in (str(REPO_ROOT), str(API_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)


def extract_path_for(month_start) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    return RAW_DIR / f"extract_{month_start}.json"


def kpis_path_for(month_start) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    return RAW_DIR / f"kpis_{month_start}.json"


def eval_snapshot_path_for(month_start) -> Path:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    return EVAL_DIR / f"monthly_clinic_supply_performance_{month_start}.json"


def last_run_log_path() -> Path:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    return EVAL_DIR / "last_run.json"
