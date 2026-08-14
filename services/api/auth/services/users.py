"""User persistence and credential management."""

from __future__ import annotations

from datetime import datetime, timezone

from auth.database import get_users_table
from auth.models import (
    UserInDB,
    UserPublic,
    UserRegister,
    UserRegistrationResponse,
    UserRole,
    UserUpdate,
)
from auth.security import hash_password, verify_password
from auth.services import profiles as profile_service
from tinydb import Query


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _to_user_public(document: dict) -> UserPublic:
    data = {key: value for key, value in document.items() if key != "hashed_password"}
    return UserPublic.model_validate(data)


def _to_user_in_db(document: dict) -> UserInDB:
    return UserInDB.model_validate(document)


def get_user_by_id(user_id: int) -> UserInDB | None:
    document = get_users_table().get(doc_id=user_id)
    if document is None:
        return None
    return _to_user_in_db(document)


def get_user_by_email(email: str) -> UserInDB | None:
    normalized = _normalize_email(email)
    matches = get_users_table().search(Query().email == normalized)
    if not matches:
        return None
    return _to_user_in_db(matches[0])


def list_users() -> list[UserPublic]:
    documents = get_users_table().all()
    documents.sort(key=lambda doc: doc.get("email", ""))
    return [_to_user_public(doc) for doc in documents]


def create_user(payload: UserRegister) -> UserRegistrationResponse:
    normalized_email = _normalize_email(payload.email)
    if get_user_by_email(normalized_email) is not None:
        raise ValueError("A user with this email already exists.")

    table = get_users_table()
    now = _utc_now()
    document = {
        "email": normalized_email,
        "hashed_password": hash_password(payload.password),
        "is_active": True,
        "role": UserRole.user.value,
        "created_at": now.isoformat(),
    }
    doc_id = table.insert(document)
    table.update({"id": doc_id}, doc_ids=[doc_id])

    profile_name = payload.name or normalized_email.split("@", 1)[0]
    profile = profile_service.create_profile(
        doc_id,
        name=profile_name,
        phone=payload.phone,
        address=payload.address,
    )

    user = _to_user_public({**document, "id": doc_id, "created_at": now})
    return UserRegistrationResponse(user=user, profile=profile)


def update_user(user_id: int, payload: UserUpdate, *, allow_role_change: bool) -> UserPublic:
    table = get_users_table()
    document = table.get(doc_id=user_id)
    if document is None:
        raise LookupError("User not found.")

    updates: dict = {}

    if payload.email is not None:
        normalized = _normalize_email(payload.email)
        existing = get_user_by_email(normalized)
        if existing is not None and existing.id != user_id:
            raise ValueError("A user with this email already exists.")
        updates["email"] = normalized

    if payload.password is not None:
        updates["hashed_password"] = hash_password(payload.password)

    if payload.is_active is not None:
        updates["is_active"] = payload.is_active

    if payload.role is not None:
        if not allow_role_change:
            raise PermissionError("Only admins may change user roles.")
        updates["role"] = payload.role.value

    if not updates:
        return _to_user_public(document)

    table.update(updates, doc_ids=[user_id])
    return _to_user_public({**document, **updates})


def delete_user(user_id: int) -> None:
    table = get_users_table()
    if table.get(doc_id=user_id) is None:
        raise LookupError("User not found.")
    profile_service.delete_profile_by_user_id(user_id)
    table.remove(doc_ids=[user_id])


def update_password(user_id: int, new_password: str) -> None:
    table = get_users_table()
    if table.get(doc_id=user_id) is None:
        raise LookupError("User not found.")
    table.update({"hashed_password": hash_password(new_password)}, doc_ids=[user_id])


def change_password(user_id: int, current_password: str, new_password: str) -> None:
    user = get_user_by_id(user_id)
    if user is None:
        raise LookupError("User not found.")
    if not verify_password(current_password, user.hashed_password):
        raise ValueError("Current password is incorrect.")
    if current_password == new_password:
        raise ValueError("New password must be different from the current password.")
    update_password(user_id, new_password)
