from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_store
from app.dependencies.auth import get_current_user

router = APIRouter()


@router.get("")
def list_notifications(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    items = get_store().list_module_records("notification_logs", current_user["org_id"])
    return sorted((item for item in items if item.get("user_id") == current_user["id"]), key=lambda item: item.get("created_at", ""), reverse=True)


@router.patch("/{notification_id}/read")
def mark_notification_read(notification_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    store = get_store()
    notification = store.get_module_record("notification_logs", notification_id, org_id)
    if notification is None or notification.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="Notification not found")
    return store.update_module_record("notification_logs", notification_id, org_id, {"read_at": datetime.now(timezone.utc).isoformat()})