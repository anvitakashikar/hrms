from datetime import date, datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.notification_service import notify_user

router = APIRouter()
store = get_store()
HR_ROLES = ("admin", "hr")
REVIEW_ROLES = ("admin", "hr", "manager")
CLEARANCE_DEPARTMENTS = ("hr", "finance", "it", "documents", "assets")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _record(collection: str, record_id: str, org_id: str, label: str) -> Dict[str, Any]:
    item = store.get_module_record(collection, record_id, org_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return item


@router.post("/requests", status_code=status.HTTP_201_CREATED)
def create_exit_request(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    try:
        last_working_day = date.fromisoformat(payload["last_working_day"]).isoformat()
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="last_working_day must use YYYY-MM-DD") from exc
    reason = str(payload.get("reason", "")).strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Exit reason is required")
    employee = store.get_employee_by_user_email(org_id, current_user["email"])
    request = store.create_module_record("exit_requests", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "employee_id": employee["id"] if employee else None,
        "last_working_day": last_working_day,
        "reason": reason,
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    store.add_audit_log(current_user["id"], org_id, "exit.request.submitted", {"record_id": request["id"]})
    for user in store.users.values():
        if user.get("org_id") == org_id and user.get("role") in HR_ROLES:
            notify_user(org_id, user["id"], "exit.request.submitted", "Exit request submitted", f"{current_user['first_name']} submitted an exit request.", "exit_request", request["id"])
    return request


@router.get("/requests")
def list_exit_requests(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    items = store.list_module_records("exit_requests", org_id)
    if current_user.get("role") not in HR_ROLES:
        items = [item for item in items if item.get("user_id") == current_user["id"]]
    return items


@router.patch("/requests/{request_id}/decision")
def decide_exit_request(request_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    decision = payload.get("status")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Status must be approved or rejected")
    request = _record("exit_requests", request_id, org_id, "Exit request")
    if request["status"] != "submitted":
        raise HTTPException(status_code=409, detail="Exit request has already been reviewed")
    updated = store.update_module_record("exit_requests", request_id, org_id, {
        "status": decision,
        "reviewed_by": current_user["id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_comment": str(payload.get("comment", "")).strip(),
    })
    if decision == "approved" and request.get("employee_id"):
        store.update_employee(request["employee_id"], org_id, {"status": "notice_period", "last_working_day": request["last_working_day"]})
        for department in CLEARANCE_DEPARTMENTS:
            store.create_module_record("exit_clearance_checklists", {
                "org_id": org_id,
                "exit_request_id": request_id,
                "user_id": request["user_id"],
                "department": department,
                "status": "pending",
                "created_by": current_user["id"],
            })
            notify_user(org_id, request["user_id"], "exit.clearances.created", "Exit clearance started", "HR, Finance, IT, and Asset clearances are ready.", "exit_request", request_id)
    notify_user(org_id, request["user_id"], f"exit.request.{decision}", f"Exit request {decision}", f"Your exit request was {decision}.", "exit_request", request_id)
    store.add_audit_log(current_user["id"], org_id, f"exit.request.{decision}", {"record_id": request_id})
    return updated


@router.get("/clearances")
def list_exit_clearances(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    items = store.list_module_records("exit_clearance_checklists", org_id)
    if current_user.get("role") not in HR_ROLES:
        items = [item for item in items if item.get("user_id") == current_user["id"]]
    return items


@router.patch("/clearances/{clearance_id}")
def update_exit_clearance(clearance_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    clearance = _record("exit_clearance_checklists", clearance_id, org_id, "Clearance task")
    decision = payload.get("status")
    if decision not in {"cleared", "blocked"}:
        raise HTTPException(status_code=422, detail="Clearance status must be cleared or blocked")
    if decision == "cleared" and clearance["department"] == "assets":
        outstanding = [item for item in store.list_module_records("assets", org_id) if item.get("assigned_user_id") == clearance["user_id"] and item.get("status") in {"assigned", "acknowledged"}]
        if outstanding:
            raise HTTPException(status_code=409, detail="Return assigned assets before completing asset clearance")
    if decision == "cleared" and clearance["department"] == "documents":
        required_categories = [item for item in store.list_module_records("document_categories", org_id) if item.get("active") and item.get("required")]
        documents = store.list_module_records("employee_documents", org_id)
        missing = [category["name"] for category in required_categories if not any(item.get("owner_user_id") == clearance["user_id"] and item.get("category_id") == category["id"] and item.get("status") == "approved" for item in documents)]
        if missing:
            raise HTTPException(status_code=409, detail="Complete required document verification before clearance: " + ", ".join(missing))
    updated = store.update_module_record("exit_clearance_checklists", clearance_id, org_id, {
        "status": decision,
        "completed_by": current_user["id"],
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "comment": str(payload.get("comment", "")).strip(),
    })
    store.add_audit_log(current_user["id"], org_id, "exit.clearance.updated", {"record_id": clearance_id, "department": clearance["department"], "status": decision})
    return updated


@router.post("/interviews", status_code=status.HTTP_201_CREATED)
def create_exit_interview(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    exit_request = _record("exit_requests", str(payload.get("exit_request_id", "")), org_id, "Exit request")
    try:
        scheduled_at = datetime.fromisoformat(str(payload["scheduled_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="scheduled_at must be an ISO-8601 timestamp") from exc
    return store.create_module_record("exit_interviews", {
        "org_id": org_id,
        "exit_request_id": exit_request["id"],
        "user_id": exit_request["user_id"],
        "scheduled_at": scheduled_at.isoformat(),
        "status": "scheduled",
        "created_by": current_user["id"],
    })


@router.post("/interviews/{interview_id}/feedback")
def submit_exit_interview_feedback(interview_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    interview = _record("exit_interviews", interview_id, org_id, "Exit interview")
    feedback = str(payload.get("feedback", "")).strip()
    if not feedback:
        raise HTTPException(status_code=422, detail="Interview feedback is required")
    updated = store.update_module_record("exit_interviews", interview_id, org_id, {
        "status": "completed",
        "feedback": feedback,
        "exit_reason_category": payload.get("exit_reason_category"),
        "completed_by": current_user["id"],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    store.add_audit_log(current_user["id"], org_id, "exit.interview.completed", {"record_id": interview_id, "exit_request_id": interview["exit_request_id"]})
    return updated


@router.post("/settlements/preview", status_code=status.HTTP_200_OK)
def preview_fnf_settlement(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    exit_request = _record("exit_requests", str(payload.get("exit_request_id", "")), org_id, "Exit request")
    if exit_request["status"] != "approved":
        raise HTTPException(status_code=409, detail="Exit request must be approved before settlement")
    user_id = exit_request["user_id"]
    payslips = [item for item in store.list_module_records("payslips", org_id) if item.get("user_id") == user_id and item.get("status") == "available"]
    payslips.sort(key=lambda item: item.get("period_end", ""), reverse=True)
    monthly_salary = float(payslips[0]["earnings"].get("Base salary", 0)) if payslips else 0
    last_day = date.fromisoformat(exit_request["last_working_day"])
    salary_proration = round(monthly_salary * last_day.day / 30, 2)
    approved_expenses = [item for item in store.list_module_records("expense_claims", org_id) if item.get("user_id") == user_id and item.get("status") == "approved"]
    reimbursements = round(sum(float(item.get("amount", 0)) for item in approved_expenses), 2)
    overtime = [item for item in store.list_module_records("overtime_records", org_id) if item.get("user_id") == user_id and item.get("status") == "approved"]
    overtime_minutes = sum(int(item.get("minutes", 0)) for item in overtime)
    overtime_weighted_minutes = sum(int(item.get("minutes", 0)) * float(item.get("rate_multiplier", 1)) for item in overtime)
    overtime_amount = round(monthly_salary / (30 * 8 * 60) * overtime_weighted_minutes, 2)
    deductions = [item for item in store.list_module_records("employee_deductions", org_id) if item.get("user_id") == user_id and item.get("active")]
    deduction_total = round(sum(float(item.get("amount", 0)) for item in deductions), 2)
    clearance_items = [item for item in store.list_module_records("exit_clearance_checklists", org_id) if item.get("exit_request_id") == exit_request["id"]]
    gratuity = float(payload.get("gratuity_amount", 0))
    leave_settlement = float(payload.get("leave_settlement", 0))
    gross = round(salary_proration + reimbursements + overtime_amount + leave_settlement + gratuity, 2)
    net = round(gross - deduction_total, 2)
    return {
        "exit_request_id": exit_request["id"],
        "user_id": user_id,
        "salary_proration": salary_proration,
        "reimbursements": reimbursements,
        "approved_overtime_minutes": overtime_minutes,
        "approved_overtime_amount": overtime_amount,
        "leave_settlement": leave_settlement,
        "gratuity": gratuity,
        "deductions": deduction_total,
        "gross_total": gross,
        "net_total": net,
        "clearances_complete": bool(clearance_items) and all(item.get("status") == "cleared" for item in clearance_items),
        "status": "preview",
    }


@router.post("/settlements", status_code=status.HTTP_201_CREATED)
def create_fnf_settlement(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    preview = preview_fnf_settlement(payload, current_user)
    if not preview["clearances_complete"]:
        raise HTTPException(status_code=409, detail="All exit clearances must be complete before finalizing settlement")
    org_id = _org_id(current_user)
    settlement = store.create_module_record("fnf_settlements", {
        **preview,
        "org_id": org_id,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "finalized",
    })
    store.add_audit_log(current_user["id"], org_id, "exit.fnf_settlement.finalized", {"record_id": settlement["id"], "user_id": preview["user_id"]})
    notify_user(org_id, preview["user_id"], "exit.settlement.finalized", "Final settlement available", "Your full and final settlement has been prepared.", "fnf_settlement", settlement["id"])
    return settlement


@router.post("/gratuity", status_code=status.HTTP_201_CREATED)
def record_gratuity(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    exit_request = _record("exit_requests", str(payload.get("exit_request_id", "")), org_id, "Exit request")
    try:
        amount = float(payload["amount"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Gratuity amount is required") from exc
    if amount < 0:
        raise HTTPException(status_code=422, detail="Gratuity amount cannot be negative")
    gratuity = store.create_module_record("gratuity_records", {
        "org_id": org_id,
        "exit_request_id": exit_request["id"],
        "user_id": exit_request["user_id"],
        "amount": amount,
        "calculation_notes": str(payload.get("calculation_notes", "")).strip(),
        "recorded_by": current_user["id"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    store.add_audit_log(current_user["id"], org_id, "exit.gratuity.recorded", {"record_id": gratuity["id"]})
    return gratuity
