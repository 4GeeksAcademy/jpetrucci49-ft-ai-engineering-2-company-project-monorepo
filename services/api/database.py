"""TinyDB initialisation for the supplier directory."""

from __future__ import annotations

import os
from pathlib import Path

from tinydb import TinyDB

API_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = API_ROOT / "suppliers.json"
SUPPLIERS_TABLE = "suppliers"

_db: TinyDB | None = None


def get_db_path() -> Path:
    configured = os.environ.get("SUPPLIERS_DB_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_DB_PATH


def get_db() -> TinyDB:
    global _db
    if _db is None:
        _db = TinyDB(get_db_path())
    return _db


def get_suppliers_table():
    return get_db().table(SUPPLIERS_TABLE)
