from typing import Any, Dict, Optional

from app.database import get_store


def notify_user(
    org_id: str,
    user_id: str,
    event: str,
    title: str,
    message: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> Dict[str, Any]:
    return get_store().create_module_record("notification_logs", {
        "org_id": org_id,
        "user_id": user_id,
        "event": event,
        "title": title,
        "message": message,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "read_at": None,
    })


def notify_reviewers(
    org_id: str,
    event: str,
    title: str,
    message: str,
    entity_type: str,
    entity_id: str,
) -> None:
    store = get_store()
    for user in store.users.values():
        if user.get("org_id") == org_id and user.get("role") in {"admin", "hr", "manager"}:
            notify_user(org_id, user["id"], event, title, message, entity_type, entity_id)