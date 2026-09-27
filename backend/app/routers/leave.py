from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user, require_roles

router = APIRouter()


leave_store = {}


@router.post("/applications", status_code=status.HTTP_201_CREATED)
def create_leave_application(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    app_id = f"leave-{len(leave_store) + 1}"
    item = {
        "id": app_id,
        "user_id": current_user["id"],
        "org_id": current_user["org_id"],
        "leave_type": payload["leave_type"],
        "start_date": payload["start_date"],
        "end_date": payload["end_date"],
        "reason": payload["reason"],
        "status": "pending",
    }
    leave_store[app_id] = item
    return item


@router.get("/applications")
def list_leave_applications(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return [item for item in leave_store.values() if item["org_id"] == current_user["org_id"]]


@router.patch("/applications/{application_id}/approve")
def approve_leave_application(
    application_id: str,
    payload: Optional[Dict[str, Any]] = None,
    current_user: Dict[str, Any] = Depends(require_roles("admin", "hr", "manager")),
):
    item = leave_store.get(application_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave application not found")
    if item["org_id"] != current_user["org_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.get("role") not in {"admin", "hr", "manager"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    item["status"] = "approved"
    item["approved_by"] = current_user["id"]
    item["comment"] = (payload or {}).get("comment", "")
    return item
