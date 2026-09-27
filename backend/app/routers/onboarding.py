from datetime import date, datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.notification_service import notify_user

router = APIRouter()
store = get_store()
MANAGERS = ("admin", "hr", "manager")
HR_ROLES = ("admin", "hr")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _assignee_user(assignee: Any, org_id: str) -> Dict[str, Any]:
    user = store.get_user_by_id(str(assignee)) if assignee else None
    if user is None and assignee:
        user = store.get_user_by_email(str(assignee))
    if user is None or user.get("org_id") != org_id:
        raise HTTPException(status_code=422, detail="Assignee must be a user in this organization")
    return user


@router.post("/checklists", status_code=status.HTTP_201_CREATED)
def create_checklist(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    title = str(payload.get("title", "")).strip()
    tasks = payload.get("tasks", [])
    if not title or not isinstance(tasks, list):
        raise HTTPException(status_code=422, detail="Checklist title and task list are required")
    normalized_tasks = []
    for item in tasks:
        task_title = str(item.get("title", "")).strip()
        if task_title:
            normalized_tasks.append({"title": task_title, "days_from_start": max(0, int(item.get("days_from_start", 0)))})
    if not normalized_tasks:
        raise HTTPException(status_code=422, detail="A checklist needs at least one task")
    return store.create_module_record("onboarding_checklists", {
        "org_id": org_id,
        "title": title,
        "description": str(payload.get("description", "")).strip(),
        "tasks": normalized_tasks,
        "active": True,
        "created_by": current_user["id"],
    })


@router.get("/checklists")
def list_checklists(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    return store.list_module_records("onboarding_checklists", current_user["org_id"])


@router.post("/checklists/{checklist_id}/assign", status_code=status.HTTP_201_CREATED)
def assign_checklist(
    checklist_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES)),
) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    checklist = store.get_module_record("onboarding_checklists", checklist_id, org_id)
    if checklist is None or not checklist.get("active"):
        raise HTTPException(status_code=404, detail="Active checklist not found")
    employee = _assignee_user(payload.get("user_id") or payload.get("assignee"), org_id)
    start_date = payload.get("start_date", date.today().isoformat())
    try:
        start = date.fromisoformat(start_date)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="start_date must use YYYY-MM-DD") from exc
    created = []
    for template_task in checklist["tasks"]:
        due = start.fromordinal(start.toordinal() + template_task["days_from_start"])
        task = store.create_module_record("onboarding_tasks", {
            "org_id": org_id,
            "checklist_id": checklist_id,
            "employee_user_id": employee["id"],
            "employee_email": employee["email"],
            "title": template_task["title"],
            "assignee_user_id": employee["id"],
            "assigned_by": current_user["id"],
            "due_date": due.isoformat(),
            "status": "pending",
        })
        created.append(task)
    notify_user(org_id, employee["id"], "onboarding.tasks_assigned", "Onboarding tasks assigned", f"{len(created)} onboarding tasks are ready for you.", "onboarding_checklist", checklist_id)
    store.add_audit_log(current_user["id"], org_id, "onboarding.checklist.assigned", {"record_id": checklist_id, "employee_user_id": employee["id"]})
    return created


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_onboarding_task(
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*MANAGERS)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    title = str(payload.get("title", "")).strip()
    if not title:
        raise HTTPException(status_code=422, detail="Task title is required")
    assignee = _assignee_user(payload.get("assignee_user_id") or payload.get("assignee"), org_id)
    due_date = payload.get("due_date")
    try:
        due_date = date.fromisoformat(due_date).isoformat()
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="due_date must use YYYY-MM-DD") from exc
    item = store.create_module_record("onboarding_tasks", {
        "org_id": org_id,
        "title": title,
        "employee_user_id": assignee["id"],
        "employee_email": assignee["email"],
        "assignee_user_id": assignee["id"],
        "assigned_by": current_user["id"],
        "due_date": due_date,
        "status": "pending",
    })
    notify_user(org_id, assignee["id"], "onboarding.task_assigned", "Onboarding task assigned", f"{title} is due {due_date}.", "onboarding_task", item["id"])
    store.add_audit_log(current_user["id"], org_id, "onboarding.task.created", {"record_id": item["id"]})
    return item


@router.get("/tasks")
def list_onboarding_tasks(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    items = store.list_module_records("onboarding_tasks", current_user["org_id"])
    if current_user.get("role") not in MANAGERS:
        items = [item for item in items if item.get("employee_user_id") == current_user["id"] or item.get("assignee_user_id") == current_user["id"]]
    return items


@router.patch("/tasks/{task_id}")
def update_onboarding_task(
    task_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    task = store.get_module_record("onboarding_tasks", task_id, org_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    allowed_statuses = {"pending", "in_progress", "completed", "blocked"}
    status_value = payload.get("status")
    if status_value not in allowed_statuses:
        raise HTTPException(status_code=422, detail="Unsupported onboarding task status")
    is_assignee = task.get("employee_user_id") == current_user["id"] or task.get("assignee_user_id") == current_user["id"]
    if not is_assignee and current_user.get("role") not in MANAGERS:
        raise HTTPException(status_code=403, detail="Only the assignee or HR can update this task")
    updates = {"status": status_value, "updated_by": current_user["id"]}
    if status_value == "completed":
        updates["completed_at"] = datetime.now(timezone.utc).isoformat()
    updated = store.update_module_record("onboarding_tasks", task_id, org_id, updates)
    store.add_audit_log(current_user["id"], org_id, "onboarding.task.updated", {"record_id": task_id, "status": status_value})
    return updated


@router.get("/dashboard")
def onboarding_dashboard(current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    tasks = store.list_module_records("onboarding_tasks", org_id)
    documents = store.list_module_records("employee_documents", org_id)
    today = date.today().isoformat()
    pending_tasks = [item for item in tasks if item.get("status") != "completed"]
    onboarding_users = {item.get("employee_user_id") for item in pending_tasks}
    return {
        "employees_onboarding": len(onboarding_users),
        "completed_tasks": sum(1 for item in tasks if item.get("status") == "completed"),
        "pending_tasks": len(pending_tasks),
        "overdue_tasks": sum(1 for item in pending_tasks if item.get("due_date", "") < today),
        "documents_pending_verification": sum(1 for item in documents if item.get("status") == "pending_verification"),
        "missing_required_documents": len([
            category for category in store.list_module_records("document_categories", org_id)
            if category.get("active") and category.get("required")
        ]) - sum(1 for item in documents if item.get("status") == "approved"),
        "tasks": tasks,
    }


@router.post("/assets", status_code=status.HTTP_201_CREATED)
def create_asset(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=422, detail="Asset name is required")
    asset = store.create_module_record("assets", {
        "org_id": org_id,
        "name": name,
        "asset_type": payload.get("asset_type", "equipment"),
        "serial_number": payload.get("serial_number"),
        "status": "available",
        "created_by": current_user["id"],
    })
    store.add_audit_log(current_user["id"], org_id, "asset.created", {"record_id": asset["id"]})
    return asset


@router.get("/assets")
def list_assets(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    assets = store.list_module_records("assets", current_user["org_id"])
    if current_user.get("role") not in HR_ROLES:
        assets = [item for item in assets if item.get("assigned_user_id") == current_user["id"]]
    return assets


@router.post("/assets/{asset_id}/assign")
def assign_asset(asset_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    asset = store.get_module_record("assets", asset_id, org_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset["status"] != "available":
        raise HTTPException(status_code=409, detail="Asset is not available")
    employee = _assignee_user(payload.get("user_id") or payload.get("employee_email"), org_id)
    assigned = store.update_module_record("assets", asset_id, org_id, {
        "assigned_user_id": employee["id"],
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "expected_return_date": payload.get("expected_return_date"),
        "status": "assigned",
        "acknowledged_at": None,
    })
    store.create_module_record("asset_assignments", {
        "org_id": org_id,
        "asset_id": asset_id,
        "user_id": employee["id"],
        "assigned_by": current_user["id"],
        "assigned_at": assigned["assigned_at"],
        "status": "assigned",
    })
    notify_user(org_id, employee["id"], "asset.assigned", "Asset assigned", f"{asset['name']} has been assigned to you.", "asset", asset_id)
    store.add_audit_log(current_user["id"], org_id, "asset.assigned", {"record_id": asset_id, "employee_user_id": employee["id"]})
    return assigned


@router.patch("/assets/{asset_id}/acknowledge")
def acknowledge_asset(asset_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    asset = store.get_module_record("assets", asset_id, org_id)
    if asset is None or asset.get("assigned_user_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="Asset assignment not found")
    if asset.get("status") != "assigned":
        raise HTTPException(status_code=409, detail="Asset is not awaiting acknowledgement")
    return store.update_module_record("assets", asset_id, org_id, {"status": "acknowledged", "acknowledged_at": datetime.now(timezone.utc).isoformat()})


@router.patch("/assets/{asset_id}/return")
def return_asset(asset_id: str, current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    asset = store.get_module_record("assets", asset_id, org_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.get("status") not in {"assigned", "acknowledged"}:
        raise HTTPException(status_code=409, detail="Asset is not currently assigned")
    store.create_module_record("asset_assignments", {
        "org_id": org_id,
        "asset_id": asset_id,
        "user_id": asset["assigned_user_id"],
        "returned_by": current_user["id"],
        "returned_at": datetime.now(timezone.utc).isoformat(),
        "status": "returned",
    })
    updated = store.update_module_record("assets", asset_id, org_id, {"status": "available", "assigned_user_id": None, "returned_at": datetime.now(timezone.utc).isoformat()})
    store.add_audit_log(current_user["id"], org_id, "asset.returned", {"record_id": asset_id})
    return updated
