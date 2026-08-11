"""TinyDB initialisation for users and profiles."""

from __future__ import annotations

import os
from pathlib import Path

from tinydb import TinyDB

API_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUTH_DB_PATH = API_ROOT / "auth.json"
USERS_TABLE = "users"
PROFILES_TABLE = "profiles"

_db: TinyDB | None = None


def get_auth_db_path() -> Path:
    configured = os.environ.get("AUTH_DB_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_AUTH_DB_PATH


def get_auth_db() -> TinyDB:
    global _db
    if _db is None:
        _db = TinyDB(get_auth_db_path())
    return _db


def get_users_table():
    return get_auth_db().table(USERS_TABLE)


def get_profiles_table():
    return get_auth_db().table(PROFILES_TABLE)
