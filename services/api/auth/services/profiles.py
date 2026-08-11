"""Profile persistence helpers."""

from __future__ import annotations

from auth.database import get_profiles_table
from auth.models import ProfilePublic, ProfileUpdate
from tinydb import Query


def _to_profile(document: dict) -> ProfilePublic:
    return ProfilePublic.model_validate(document)


def get_profile_by_user_id(user_id: int) -> ProfilePublic | None:
    matches = get_profiles_table().search(Query().user_id == user_id)
    if not matches:
        return None
    return _to_profile(matches[0])


def profile_exists_for_user(user_id: int) -> bool:
    return get_profile_by_user_id(user_id) is not None


def create_profile(
    user_id: int,
    *,
    name: str,
    phone: str | None = None,
    address: str | None = None,
) -> ProfilePublic:
    if profile_exists_for_user(user_id):
        raise ValueError("Profile already exists for this user.")

    table = get_profiles_table()
    document = {
        "user_id": user_id,
        "name": name,
        "phone": phone,
        "address": address,
    }
    doc_id = table.insert(document)
    table.update({"id": doc_id}, doc_ids=[doc_id])
    return _to_profile({**document, "id": doc_id})


def update_profile(user_id: int, payload: ProfileUpdate) -> ProfilePublic:
    table = get_profiles_table()
    matches = table.search(Query().user_id == user_id)
    if not matches:
        raise LookupError("Profile not found.")

    document = matches[0]
    doc_id = document["id"]
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _to_profile(document)

    table.update(updates, doc_ids=[doc_id])
    return _to_profile({**document, **updates})


def delete_profile_by_user_id(user_id: int) -> None:
    table = get_profiles_table()
    matches = table.search(Query().user_id == user_id)
    for document in matches:
        table.remove(doc_ids=[document["id"]])
