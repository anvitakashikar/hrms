from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_store
from app.dependencies.auth import get_current_user

router = APIRouter()
store = get_store()
EDITABLE_FIELDS = {"first_name", "last_name", "phone", "address", "emergency_contact_name", "emergency_contact_phone"}


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _profile(user: Dict[str, Any]) -> Dict[str, Any]:
    org_id = _org_id(user)
    employee = store.get_employee_by_user_email(org_id, user["email"])
    safe_employee = {}
    if employee:
        safe_employee = {key: employee.get(key) for key in ("id", "employee_code", "department", "designation", "status", "created_at")}
    return {
        "id": user["id"],
        "email": user["email"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "role": user["role"],
        "phone": user.get("phone", employee.get("phone") if employee else None),
        "address": user.get("address", employee.get("address") if employee else None),
        "emergency_contact_name": user.get("emergency_contact_name"),
        "emergency_contact_phone": user.get("emergency_contact_phone"),
        "employee": safe_employee,
    }


@router.get("/profile")
def get_my_profile(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    return _profile(current_user)


@router.patch("/profile")
def update_my_profile(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    updates = {key: str(payload[key]).strip() if payload[key] is not None else None for key in EDITABLE_FIELDS if key in payload}
    if not updates:
        raise HTTPException(status_code=422, detail="No editable profile fields were provided")
    if "first_name" in updates and not updates["first_name"]:
        raise HTTPException(status_code=422, detail="First name cannot be empty")
    if "last_name" in updates and not updates["last_name"]:
        raise HTTPException(status_code=422, detail="Last name cannot be empty")
    before = {key: current_user.get(key) for key in updates}
    updated = store.update_user(current_user["id"], updates)
    employee = store.get_employee_by_user_email(org_id, current_user["email"])
    if employee:
        employee_updates = {key: updates[key] for key in ("first_name", "last_name", "phone", "address") if key in updates}
        store.update_employee(employee["id"], org_id, employee_updates)
    store.add_audit_log(current_user["id"], org_id, "employee.profile.updated", {"previous": before, "new": updates})
    return _profile(updated)
