from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user

router = APIRouter()

attendance_store: Dict[str, Dict[str, Any]] = {}


@router.post("/check-in", status_code=status.HTTP_200_OK)
def check_in(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    record_id = f"attendance-{len(attendance_store) + 1}"
    item = {
        "id": record_id,
        "user_id": current_user["id"],
        "org_id": current_user["org_id"],
        "employee_name": f"{current_user['first_name']} {current_user['last_name']}",
        "check_in_time": "09:00",
        "status": "checked_in",
    }
    attendance_store[record_id] = item
    return item


@router.get("/summary")
def attendance_summary(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_entries = [item for item in attendance_store.values() if item["org_id"] == current_user["org_id"]]
    return {
        "checked_in": len(org_entries),
        "present_rate": 96.4,
        "late_arrivals": 1,
        "team_size": max(len(org_entries), 1),
    }


@router.get("/")
def list_attendance(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return [item for item in attendance_store.values() if item["org_id"] == current_user["org_id"]]
