from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles

router = APIRouter()
HR_ROLES = ("admin", "hr")


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


@router.post("/reminders/run")
def run_reminders(current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    store = get_store()
    now = datetime.now(timezone.utc)
    today = date.today().isoformat()
    reminders = []
    existing_keys = {
        item.get("reminder_key") for item in store.list_module_records("notification_logs", org_id)
        if item.get("reminder_key")
    }

    def add_reminder(user_id: str, key: str, event: str, title: str, message: str, entity_type: str, entity_id: str) -> None:
        if key in existing_keys:
            return
        reminder = store.create_module_record("notification_logs", {
            "org_id": org_id,
            "user_id": user_id,
            "event": event,
            "title": title,
            "message": message,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "reminder_key": key,
            "read_at": None,
            "created_at": now.isoformat(),
        })
        existing_keys.add(key)
        reminders.append(reminder)

    for task in store.list_module_records("onboarding_tasks", org_id):
        if task.get("status") != "completed" and task.get("due_date", "") < today and task.get("employee_user_id"):
            add_reminder(task["employee_user_id"], f"onboarding:{task['id']}:{task['due_date']}", "reminder.onboarding.overdue", "Onboarding task overdue", f"{task['title']} was due {task['due_date']}.", "onboarding_task", task["id"])

    expiry_cutoff = (date.today() + timedelta(days=30)).isoformat()
    for document in store.list_module_records("employee_documents", org_id):
        expiry = document.get("expiry_date")
        if expiry and today <= expiry <= expiry_cutoff and document.get("owner_user_id"):
            add_reminder(document["owner_user_id"], f"document-expiry:{document['id']}:{expiry}", "reminder.document.expiring", "Document expiry approaching", f"Your {document['category']} document expires on {expiry}.", "employee_document", document["id"])

    stale_cutoff = (date.today() - timedelta(days=2)).isoformat()
    for request in store.list_module_records("attendance_regularization_requests", org_id):
        if request.get("status") == "pending" and request.get("submitted_at", "")[:10] <= stale_cutoff:
            for user in store.users.values():
                if user.get("org_id") == org_id and user.get("role") in {"admin", "hr", "manager"}:
                    add_reminder(user["id"], f"regularization:{request['id']}:{user['id']}", "reminder.attendance.regularization", "Regularization awaiting review", f"An attendance request for {request['work_date']} is still pending.", "attendance_regularization_request", request["id"])

    store.add_audit_log(current_user["id"], org_id, "notifications.reminders.executed", {"created_count": len(reminders)})
    return {"created_count": len(reminders), "reminders": reminders}