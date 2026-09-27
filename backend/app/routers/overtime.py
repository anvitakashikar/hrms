from datetime import date, datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.notification_service import notify_reviewers, notify_user
from app.services.team_service import get_team_user_ids

router = APIRouter()
store = get_store()
REVIEW_ROLES = ("admin", "hr", "manager")
HR_ROLES = ("admin", "hr")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _get_record(collection: str, record_id: str, org_id: str) -> Dict[str, Any]:
    record = store.get_module_record(collection, record_id, org_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Overtime record not found")
    return record


@router.post("/rules", status_code=status.HTTP_201_CREATED)
def create_overtime_rule(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    name = str(payload.get("name", "Standard overtime")).strip()
    try:
        multiplier = float(payload.get("rate_multiplier", 1.5))
        standard_hours = float(payload.get("standard_hours_per_day", 8))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Overtime rates must be numeric") from exc
    if multiplier <= 0 or standard_hours <= 0 or standard_hours > 24:
        raise HTTPException(status_code=422, detail="Rate multiplier and standard hours must be positive")
    return store.create_module_record("overtime_rate_rules", {
        "org_id": org_id,
        "name": name,
        "rate_multiplier": multiplier,
        "standard_hours_per_day": standard_hours,
        "active": True,
        "created_by": current_user["id"],
    })


@router.get("/rules")
def list_overtime_rules(current_user: Dict[str, Any] = Depends(require_roles(*REVIEW_ROLES))) -> List[Dict[str, Any]]:
    return store.list_module_records("overtime_rate_rules", _org_id(current_user))


@router.post("/requests", status_code=status.HTTP_201_CREATED)
def create_overtime_request(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    try:
        work_date = date.fromisoformat(payload["work_date"]).isoformat()
        minutes = int(payload["minutes"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="A valid work_date and integer minutes are required") from exc
    reason = str(payload.get("reason", "")).strip()
    if minutes <= 0 or not reason:
        raise HTTPException(status_code=422, detail="Positive overtime minutes and a reason are required")
    request = store.create_module_record("overtime_requests", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "work_date": work_date,
        "minutes": minutes,
        "reason": reason,
        "status": "pending",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    notify_reviewers(org_id, "overtime.requested", "Overtime request", f"{current_user['first_name']} requested {minutes} overtime minutes.", "overtime_request", request["id"])
    store.add_audit_log(current_user["id"], org_id, "overtime.request.submitted", {"record_id": request["id"]})
    return request


@router.get("/requests")
def list_overtime_requests(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    items = store.list_module_records("overtime_requests", org_id)
    if current_user.get("role") == "manager":
        team_ids = get_team_user_ids(current_user)
        items = [item for item in items if item.get("user_id") in team_ids]
    elif current_user.get("role") not in REVIEW_ROLES:
        items = [item for item in items if item.get("user_id") == current_user["id"]]
    return items


@router.patch("/requests/{request_id}/decision")
def decide_overtime_request(
    request_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*REVIEW_ROLES)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    decision = payload.get("status")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Status must be approved or rejected")
    request = _get_record("overtime_requests", request_id, org_id)
    if current_user.get("role") == "manager" and request.get("user_id") not in get_team_user_ids(current_user):
        raise HTTPException(status_code=404, detail="Overtime request not found")
    if request["status"] != "pending":
        raise HTTPException(status_code=409, detail="Overtime request has already been reviewed")
    updated = store.update_module_record("overtime_requests", request_id, org_id, {
        "status": decision,
        "reviewed_by": current_user["id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_comment": str(payload.get("comment", "")).strip(),
    })
    if decision == "approved":
        rules = [item for item in store.list_module_records("overtime_rate_rules", org_id) if item.get("active")]
        multiplier = float(rules[-1]["rate_multiplier"]) if rules else 1.0
        store.create_module_record("overtime_records", {
            "org_id": org_id,
            "user_id": request["user_id"],
            "request_id": request_id,
            "work_date": request["work_date"],
            "minutes": request["minutes"],
            "rate_multiplier": multiplier,
            "status": "approved",
            "approved_by": current_user["id"],
        })
    notify_user(org_id, request["user_id"], f"overtime.{decision}", f"Overtime {decision}", f"Your overtime request for {request['work_date']} was {decision}.", "overtime_request", request_id)
    store.add_audit_log(current_user["id"], org_id, f"overtime.request.{decision}", {"record_id": request_id})
    return updated


@router.get("/records")
def list_overtime_records(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    items = store.list_module_records("overtime_records", org_id)
    if current_user.get("role") == "manager":
        team_ids = get_team_user_ids(current_user)
        items = [item for item in items if item.get("user_id") in team_ids]
    elif current_user.get("role") not in REVIEW_ROLES:
        items = [item for item in items if item.get("user_id") == current_user["id"]]
    return items


@router.patch("/records/{record_id}/decision")
def decide_recorded_overtime(
    record_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*REVIEW_ROLES)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    decision = payload.get("status")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Status must be approved or rejected")
    record = _get_record("overtime_records", record_id, org_id)
    if current_user.get("role") == "manager" and record.get("user_id") not in get_team_user_ids(current_user):
        raise HTTPException(status_code=404, detail="Overtime record not found")
    if record["status"] != "pending_approval":
        raise HTTPException(status_code=409, detail="Overtime record is not awaiting approval")
    rules = [item for item in store.list_module_records("overtime_rate_rules", org_id) if item.get("active")]
    multiplier = float(rules[-1]["rate_multiplier"]) if rules else 1.0
    updated = store.update_module_record("overtime_records", record_id, org_id, {
        "status": decision,
        "rate_multiplier": multiplier if decision == "approved" else None,
        "approved_by": current_user["id"] if decision == "approved" else None,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_comment": str(payload.get("comment", "")).strip(),
    })
    store.add_audit_log(current_user["id"], org_id, f"overtime.record.{decision}", {"record_id": record_id})
    return updated


@router.get("/reports")
def overtime_report(current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    records = store.list_module_records("overtime_records", org_id)
    approved = [item for item in records if item.get("status") == "approved"]
    return {
        "record_count": len(approved),
        "total_minutes": sum(int(item.get("minutes", 0)) for item in approved),
        "employee_count": len({item.get("user_id") for item in approved}),
        "records": approved,
    }
