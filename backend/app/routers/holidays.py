from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.holiday_service import get_applicable_holidays

router = APIRouter()
store = get_store()
HR_ROLES = ("admin", "hr")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


@router.post("/calendars", status_code=status.HTTP_201_CREATED)
def create_calendar(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=422, detail="Calendar name is required")
    return store.create_module_record("holiday_calendars", {
        "org_id": _org_id(current_user),
        "name": name,
        "location": payload.get("location"),
        "department": payload.get("department"),
        "active": True,
        "created_by": current_user["id"],
    })


@router.get("/calendars")
def list_calendars(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    return store.list_module_records("holiday_calendars", current_user["org_id"])


@router.post("/calendars/{calendar_id}/assignments", status_code=status.HTTP_201_CREATED)
def assign_calendar(
    calendar_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    if store.get_module_record("holiday_calendars", calendar_id, org_id) is None:
        raise HTTPException(status_code=404, detail="Holiday calendar not found")
    user_id = payload.get("user_id")
    if user_id:
        user = store.get_user_by_id(user_id)
        if user is None or user.get("org_id") != org_id:
            raise HTTPException(status_code=422, detail="Assigned employee must belong to this organization")
    if not any((user_id, payload.get("department"), payload.get("location"))):
        raise HTTPException(status_code=422, detail="Assignment requires an employee, department, or location")
    return store.create_module_record("employee_holiday_calendar_mappings", {
        "org_id": org_id,
        "calendar_id": calendar_id,
        "user_id": user_id,
        "department": payload.get("department"),
        "location": payload.get("location"),
        "active": True,
    })


@router.post("", status_code=status.HTTP_201_CREATED)
def create_holiday(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    calendar_id = payload.get("calendar_id")
    if not calendar_id or store.get_module_record("holiday_calendars", calendar_id, org_id) is None:
        raise HTTPException(status_code=422, detail="A calendar in this organization is required")
    try:
        holiday_date = date.fromisoformat(payload["date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Holiday date must use YYYY-MM-DD") from exc
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=422, detail="Holiday name is required")
    holiday = store.create_module_record("holidays", {
        "org_id": org_id,
        "calendar_id": calendar_id,
        "name": name,
        "date": holiday_date.isoformat(),
        "category": str(payload.get("category", "public")).strip(),
        "location": payload.get("location"),
        "department": payload.get("department"),
        "created_by": current_user["id"],
    })
    store.add_audit_log(current_user["id"], org_id, "holiday.created", {"record_id": holiday["id"]})
    return holiday


@router.get("")
def list_holidays(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    holidays = store.list_module_records("holidays", current_user["org_id"])
    if year:
        holidays = [item for item in holidays if item["date"].startswith(str(year))]
    return sorted(holidays, key=lambda item: item["date"])


@router.patch("/{holiday_id}")
def update_holiday(
    holiday_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    allowed = {key: payload[key] for key in ("name", "date", "category", "location", "department", "calendar_id") if key in payload}
    if "date" in allowed:
        try:
            allowed["date"] = date.fromisoformat(allowed["date"]).isoformat()
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Holiday date must use YYYY-MM-DD") from exc
    if "calendar_id" in allowed and store.get_module_record("holiday_calendars", allowed["calendar_id"], org_id) is None:
        raise HTTPException(status_code=422, detail="Calendar not found")
    holiday = store.update_module_record("holidays", holiday_id, org_id, allowed)
    if holiday is None:
        raise HTTPException(status_code=404, detail="Holiday not found")
    store.add_audit_log(current_user["id"], org_id, "holiday.updated", {"record_id": holiday_id, "changes": allowed})
    return holiday


@router.delete("/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holiday(holiday_id: str, current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> None:
    org_id = _org_id(current_user)
    if not store.delete_module_record("holidays", holiday_id, org_id):
        raise HTTPException(status_code=404, detail="Holiday not found")
    store.add_audit_log(current_user["id"], org_id, "holiday.deleted", {"record_id": holiday_id})


def applicable_holidays(user: Dict[str, Any]) -> List[Dict[str, Any]]:
    return get_applicable_holidays(user)


@router.get("/mine")
def my_holidays(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    return applicable_holidays(current_user)