from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user, require_roles

router = APIRouter()

onboarding_store: Dict[str, Dict[str, Any]] = {}


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_onboarding_task(
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles("admin", "hr", "manager")),
) -> Dict[str, Any]:
    task_id = f"task-{len(onboarding_store) + 1}"
    item = {
        "id": task_id,
        "org_id": current_user["org_id"],
        "title": payload["title"],
        "assignee": payload.get("assignee", "unassigned"),
        "due_date": payload.get("due_date", "2026-10-01"),
        "status": payload.get("status", "pending"),
    }
    onboarding_store[task_id] = item
    return item


@router.get("/tasks")
def list_onboarding_tasks(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return [item for item in onboarding_store.values() if item["org_id"] == current_user["org_id"]]


@router.patch("/tasks/{task_id}")
def update_onboarding_task(
    task_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles("admin", "hr", "manager")),
) -> Dict[str, Any]:
    item = onboarding_store.get(task_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if item["org_id"] != current_user["org_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    item.update(payload)
    return item
