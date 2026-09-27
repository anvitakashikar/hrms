from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.notification_service import notify_user

router = APIRouter()
store = get_store()
HR_ROLES = ("admin", "hr")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _target_users(announcement: Dict[str, Any], org_id: str) -> List[Dict[str, Any]]:
    audience = announcement.get("audience", "organization")
    employees = [user for user in store.users.values() if user.get("org_id") == org_id]
    if audience == "employees":
        target_ids = set(announcement.get("target_user_ids", []))
        return [user for user in employees if user["id"] in target_ids]
    if audience == "department":
        matching_emails = {employee["email"] for employee in store.list_employees(org_id) if employee.get("department") == announcement.get("department")}
        return [user for user in employees if user["email"] in matching_emails]
    if audience == "location":
        matching_emails = {employee["email"] for employee in store.list_employees(org_id) if employee.get("location") == announcement.get("location")}
        return [user for user in employees if user["email"] in matching_emails]
    return employees


def _notify(announcement: Dict[str, Any]) -> None:
    for user in _target_users(announcement, announcement["org_id"]):
        notify_user(announcement["org_id"], user["id"], "announcement.published", announcement["title"], announcement["body"], "announcement", announcement["id"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_announcement(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    title = str(payload.get("title", "")).strip()
    body = str(payload.get("body", "")).strip()
    if not title or not body:
        raise HTTPException(status_code=422, detail="Announcement title and body are required")
    audience = payload.get("audience", "organization")
    if audience not in {"organization", "department", "location", "employees"}:
        raise HTTPException(status_code=422, detail="Unsupported announcement audience")
    if audience == "department" and not payload.get("department"):
        raise HTTPException(status_code=422, detail="Department audience requires a department")
    if audience == "location" and not payload.get("location"):
        raise HTTPException(status_code=422, detail="Location audience requires a location")
    target_ids = list(payload.get("target_user_ids", []))
    for email in payload.get("target_emails", []):
        user = store.get_user_by_email(str(email))
        if user is None or user.get("org_id") != org_id:
            raise HTTPException(status_code=422, detail="Target employees must belong to this organization")
        target_ids.append(user["id"])
    for user_id in target_ids:
        user = store.get_user_by_id(user_id)
        if user is None or user.get("org_id") != org_id:
            raise HTTPException(status_code=422, detail="Target employees must belong to this organization")
    if audience == "employees" and not target_ids:
        raise HTTPException(status_code=422, detail="Targeted employee audience requires at least one employee")
    scheduled_at = payload.get("scheduled_at")
    if scheduled_at:
        try:
            scheduled_at = datetime.fromisoformat(str(scheduled_at).replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="scheduled_at must be an ISO-8601 timestamp") from exc
    publish = bool(payload.get("publish", False))
    now = datetime.now(timezone.utc)
    future_schedule = scheduled_at and datetime.fromisoformat(scheduled_at) > now
    item = store.create_module_record("announcements", {
        "org_id": org_id,
        "title": title,
        "body": body,
        "audience": audience,
        "department": payload.get("department"),
        "location": payload.get("location"),
        "target_user_ids": target_ids,
        "scheduled_at": scheduled_at,
        "status": "scheduled" if publish and future_schedule else ("published" if publish else "draft"),
        "published_at": now.isoformat() if publish and not future_schedule else None,
        "created_by": current_user["id"],
    })
    if item["status"] == "published":
        _notify(item)
    store.add_audit_log(current_user["id"], org_id, "announcement.created", {"record_id": item["id"], "status": item["status"]})
    return item


@router.get("")
def list_announcements(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    org_id = current_user["org_id"]
    now = datetime.now(timezone.utc)
    reads = [item for item in store.list_module_records("announcement_reads", org_id) if item.get("user_id") == current_user["id"]]
    read_ids = {item["announcement_id"] for item in reads}
    items = store.list_module_records("announcements", org_id)
    result = []
    for item in items:
        if item.get("status") == "scheduled" and item.get("scheduled_at") and datetime.fromisoformat(item["scheduled_at"]) <= now:
            item = store.update_module_record("announcements", item["id"], org_id, {"status": "published", "published_at": now.isoformat()})
            _notify(item)
        if current_user.get("role") in HR_ROLES:
            visible = True
        else:
            published = item.get("status") == "published" or (item.get("status") == "scheduled" and item.get("scheduled_at") and datetime.fromisoformat(item["scheduled_at"]) <= now)
            visible = published and current_user in _target_users(item, org_id)
        if visible:
            result.append({**item, "read": item["id"] in read_ids})
    return sorted(result, key=lambda item: item.get("published_at") or item.get("scheduled_at") or item.get("created_at", ""), reverse=True)


@router.patch("/{announcement_id}")
def update_announcement(announcement_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    item = store.get_module_record("announcements", announcement_id, org_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if item["status"] == "published":
        raise HTTPException(status_code=409, detail="Unpublish an announcement before editing")
    allowed = {key: payload[key] for key in ("title", "body", "audience", "department", "location", "target_user_ids", "scheduled_at") if key in payload}
    updated = store.update_module_record("announcements", announcement_id, org_id, allowed)
    store.add_audit_log(current_user["id"], org_id, "announcement.updated", {"record_id": announcement_id})
    return updated


@router.post("/{announcement_id}/publish")
def publish_announcement(announcement_id: str, current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    item = store.get_module_record("announcements", announcement_id, org_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if item["status"] == "published":
        raise HTTPException(status_code=409, detail="Announcement is already published")
    scheduled_at = item.get("scheduled_at")
    now = datetime.now(timezone.utc)
    if scheduled_at and datetime.fromisoformat(scheduled_at) > now:
        updated = store.update_module_record("announcements", announcement_id, org_id, {"status": "scheduled"})
    else:
        updated = store.update_module_record("announcements", announcement_id, org_id, {"status": "published", "published_at": now.isoformat()})
        _notify(updated)
    store.add_audit_log(current_user["id"], org_id, "announcement.published", {"record_id": announcement_id, "status": updated["status"]})
    return updated


@router.post("/{announcement_id}/unpublish")
def unpublish_announcement(announcement_id: str, current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    item = store.get_module_record("announcements", announcement_id, org_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if item["status"] != "published":
        raise HTTPException(status_code=409, detail="Only published announcements can be unpublished")
    return store.update_module_record("announcements", announcement_id, org_id, {"status": "draft", "published_at": None})


@router.patch("/{announcement_id}/read")
def mark_announcement_read(announcement_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    item = store.get_module_record("announcements", announcement_id, org_id)
    if item is None or current_user not in _target_users(item, org_id):
        raise HTTPException(status_code=404, detail="Announcement not found")
    existing = next((read for read in store.list_module_records("announcement_reads", org_id) if read.get("announcement_id") == announcement_id and read.get("user_id") == current_user["id"]), None)
    if existing:
        return existing
    return store.create_module_record("announcement_reads", {
        "org_id": org_id,
        "announcement_id": announcement_id,
        "user_id": current_user["id"],
        "read_at": datetime.now(timezone.utc).isoformat(),
    })
