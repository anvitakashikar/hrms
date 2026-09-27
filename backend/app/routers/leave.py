from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.holiday_service import get_applicable_holiday_dates
from app.services.notification_service import notify_reviewers, notify_user
from app.services.policy_service import get_policy_value

router = APIRouter()
store = get_store()
REVIEW_ROLES = ("admin", "hr", "manager")
HR_ROLES = ("admin", "hr")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


@router.post("/types", status_code=status.HTTP_201_CREATED)
def create_leave_type(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=422, detail="Leave type name is required")
    org_id = _org_id(current_user)
    if any(item["name"].casefold() == name.casefold() for item in store.list_module_records("leave_types", org_id)):
        raise HTTPException(status_code=409, detail="Leave type already exists")
    return store.create_module_record("leave_types", {
        "org_id": org_id,
        "name": name,
        "paid": bool(payload.get("paid", True)),
        "annual_allowance": max(0, float(payload.get("annual_allowance", 0))),
        "active": True,
        "created_by": current_user["id"],
    })


@router.get("/types")
def list_leave_types(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    return store.list_module_records("leave_types", current_user["org_id"])


@router.post("/applications", status_code=status.HTTP_201_CREATED)
def create_leave_application(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    try:
        start = date.fromisoformat(payload["start_date"])
        end = date.fromisoformat(payload["end_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Leave dates must use YYYY-MM-DD") from exc
    if end < start:
        raise HTTPException(status_code=422, detail="End date must not precede start date")
    maximum_days = get_policy_value(current_user, "leave", "max_consecutive_days")
    if maximum_days is not None and (end - start).days + 1 > int(maximum_days):
        raise HTTPException(status_code=422, detail=f"Leave request exceeds the configured limit of {maximum_days} days")
    leave_type = str(payload.get("leave_type", "")).strip()
    if not leave_type or not str(payload.get("reason", "")).strip():
        raise HTTPException(status_code=422, detail="Leave type and reason are required")
    configured_types = [item for item in store.list_module_records("leave_types", org_id) if item.get("active")]
    if configured_types and leave_type not in {item["name"] for item in configured_types}:
        raise HTTPException(status_code=422, detail="Select an active leave type")
    holidays = get_applicable_holiday_dates(current_user)
    chargeable_days = sum(
        1 for ordinal in range((end - start).days + 1)
        if (day := date.fromordinal(start.toordinal() + ordinal)).weekday() < 5 and day.isoformat() not in holidays
    )
    item = store.create_module_record("leave_applications", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "employee_email": current_user["email"],
        "leave_type": leave_type,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "calendar_days": (end - start).days + 1,
        "chargeable_days": chargeable_days,
        "reason": str(payload["reason"]).strip(),
        "status": "pending",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    notify_reviewers(org_id, "leave.submitted", "Leave request submitted", f"{current_user['first_name']} submitted a {leave_type} request.", "leave_application", item["id"])
    store.add_audit_log(current_user["id"], org_id, "leave.application.submitted", {"record_id": item["id"]})
    return item


@router.get("/applications")
def list_leave_applications(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    items = store.list_module_records("leave_applications", current_user["org_id"])
    if current_user.get("role") not in REVIEW_ROLES:
        items = [item for item in items if item.get("user_id") == current_user["id"]]
    return items


@router.patch("/applications/{application_id}/approve")
def approve_leave_application(
    application_id: str,
    payload: Optional[Dict[str, Any]] = None,
    current_user: Dict[str, Any] = Depends(require_roles(*REVIEW_ROLES)),
) -> Dict[str, Any]:
    return _review_leave(application_id, "approved", payload or {}, current_user)


@router.patch("/applications/{application_id}/reject")
def reject_leave_application(
    application_id: str,
    payload: Optional[Dict[str, Any]] = None,
    current_user: Dict[str, Any] = Depends(require_roles(*REVIEW_ROLES)),
) -> Dict[str, Any]:
    return _review_leave(application_id, "rejected", payload or {}, current_user)


def _review_leave(application_id: str, decision: str, payload: Dict[str, Any], current_user: Dict[str, Any]) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    item = store.get_module_record("leave_applications", application_id, org_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Leave application not found")
    if item["status"] != "pending":
        raise HTTPException(status_code=409, detail="Leave application has already been reviewed")
    comment = str(payload.get("comment", "")).strip()
    updated = store.update_module_record("leave_applications", application_id, org_id, {
        "status": decision,
        "reviewed_by": current_user["id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "comment": comment,
    })
    notify_user(org_id, item["user_id"], f"leave.{decision}", f"Leave request {decision}", f"Your leave request for {item['start_date']} to {item['end_date']} was {decision}.", "leave_application", application_id)
    store.add_audit_log(current_user["id"], org_id, f"leave.application.{decision}", {"record_id": application_id, "comment": comment})
    return updated


@router.patch("/applications/{application_id}/cancel")
def cancel_leave_application(application_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    item = store.get_module_record("leave_applications", application_id, org_id)
    if item is None or item.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="Leave application not found")
    if item["status"] != "pending":
        raise HTTPException(status_code=409, detail="Only pending leave applications can be cancelled")
    updated = store.update_module_record("leave_applications", application_id, org_id, {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()})
    store.add_audit_log(current_user["id"], org_id, "leave.application.cancelled", {"record_id": application_id})
    return updated
