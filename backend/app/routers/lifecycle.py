import csv
import io
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.notification_service import notify_user
from app.services.team_service import get_team_user_ids

router = APIRouter()
store = get_store()
HR_ROLES = ("admin", "hr")
REVIEW_ROLES = ("admin", "hr", "manager")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _record(collection: str, record_id: str, org_id: str, label: str) -> Dict[str, Any]:
    record = store.get_module_record(collection, record_id, org_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return record


def _owned(collection: str, current_user: Dict[str, Any], owner_field: str = "user_id") -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    records = store.list_module_records(collection, org_id)
    if current_user.get("role") not in REVIEW_ROLES:
        records = [item for item in records if item.get(owner_field) == current_user["id"]]
    return records


@router.post("/duty-requests", status_code=status.HTTP_201_CREATED)
def create_duty_request(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    try:
        start = date.fromisoformat(payload["start_date"])
        end = date.fromisoformat(payload["end_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Duty dates must use YYYY-MM-DD") from exc
    location = str(payload.get("location", "")).strip()
    purpose = str(payload.get("purpose", "")).strip()
    duty_type = payload.get("duty_type", "field")
    if end < start or not location or not purpose or duty_type not in {"office", "field"}:
        raise HTTPException(status_code=422, detail="Valid dates, duty type, location, and purpose are required")
    duty = store.create_module_record("duty_assignments", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "duty_type": duty_type,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "location": location,
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "purpose": purpose,
        "status": "pending_approval",
        "requested_at": datetime.now(timezone.utc).isoformat(),
    })
    for manager in store.users.values():
        if manager.get("org_id") == org_id and manager.get("role") in REVIEW_ROLES:
            notify_user(org_id, manager["id"], "duty.requested", "Duty request", f"{current_user['first_name']} requested {duty_type} duty at {location}.", "duty_assignment", duty["id"])
    store.add_audit_log(current_user["id"], org_id, "duty.request.submitted", {"record_id": duty["id"]})
    return duty


@router.get("/duty-requests")
def list_duty_requests(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _owned("duty_assignments", current_user)


@router.patch("/duty-requests/{duty_id}/decision")
def decide_duty_request(duty_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*REVIEW_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    duty = _record("duty_assignments", duty_id, org_id, "Duty request")
    if current_user.get("role") == "manager" and duty.get("user_id") not in get_team_user_ids(current_user):
        raise HTTPException(status_code=404, detail="Duty request not found")
    decision = payload.get("status")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Status must be approved or rejected")
    if duty["status"] != "pending_approval":
        raise HTTPException(status_code=409, detail="Duty request has already been reviewed")
    updated = store.update_module_record("duty_assignments", duty_id, org_id, {
        "status": decision,
        "approved_by": current_user["id"] if decision == "approved" else None,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_comment": str(payload.get("comment", "")).strip(),
    })
    if decision == "approved" and duty.get("duty_type") == "field":
        store.create_module_record("field_duty_locations", {
            "org_id": org_id,
            "duty_id": duty_id,
            "user_id": duty["user_id"],
            "location": duty["location"],
            "latitude": duty.get("latitude"),
            "longitude": duty.get("longitude"),
            "active_from": duty["start_date"],
            "active_to": duty["end_date"],
            "purpose": duty["purpose"],
        })
    notify_user(org_id, duty["user_id"], f"duty.{decision}", f"Duty request {decision}", f"Your duty request for {duty['location']} was {decision}.", "duty_assignment", duty_id)
    store.add_audit_log(current_user["id"], org_id, f"duty.request.{decision}", {"record_id": duty_id})
    return updated


@router.post("/duty-requests/{duty_id}/location-ping", status_code=status.HTTP_201_CREATED)
def record_field_duty_location(duty_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    duty = _record("duty_assignments", duty_id, org_id, "Duty assignment")
    today = date.today().isoformat()
    if duty.get("user_id") != current_user["id"] or duty.get("status") != "approved" or duty.get("duty_type") != "field" or not duty["start_date"] <= today <= duty["end_date"]:
        raise HTTPException(status_code=403, detail="Location pings are only allowed for your approved active field duty")
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Valid location coordinates are required") from exc
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=422, detail="Location coordinates are out of range")
    ping = store.create_module_record("location_ping_logs", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "duty_id": duty_id,
        "event": "field_duty_checkin",
        "latitude": latitude,
        "longitude": longitude,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "retention_purpose": "approved_field_duty",
    })
    return ping


@router.get("/field-duty/location-history")
def list_field_duty_location_history(user_id: Optional[str] = None, current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    target_id = user_id or current_user["id"]
    if target_id != current_user["id"] and current_user.get("role") not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Field-duty location history is restricted")
    return [item for item in store.list_module_records("location_ping_logs", org_id) if item.get("user_id") == target_id and item.get("retention_purpose") == "approved_field_duty"]


@router.post("/letter-templates", status_code=status.HTTP_201_CREATED)
def create_letter_template(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    name = str(payload.get("name", "")).strip()
    body = str(payload.get("body", "")).strip()
    if not name or not body:
        raise HTTPException(status_code=422, detail="Template name and body are required")
    return store.create_module_record("letter_templates", {
        "org_id": org_id,
        "name": name,
        "letter_type": payload.get("letter_type", "custom"),
        "body": body,
        "variables": payload.get("variables", []),
        "active": True,
        "created_by": current_user["id"],
    })


@router.get("/letter-templates")
def list_letter_templates(current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> List[Dict[str, Any]]:
    return store.list_module_records("letter_templates", _org_id(current_user))


@router.post("/letters/issue", status_code=status.HTTP_201_CREATED)
def issue_letter(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    template = _record("letter_templates", str(payload.get("template_id", "")), org_id, "Letter template")
    employee = store.get_user_by_email(str(payload.get("employee_email", "")))
    if employee is None or employee.get("org_id") != org_id:
        raise HTTPException(status_code=422, detail="Employee must belong to this organization")
    rendered = template["body"]
    values = payload.get("values", {})
    for variable in template.get("variables", []):
        key = variable if isinstance(variable, str) else variable.get("name")
        if key:
            rendered = rendered.replace("{{" + key + "}}", str(values.get(key, "")))
    if "{{" in rendered:
        raise HTTPException(status_code=422, detail="All template variables must be supplied")
    issuance = store.create_module_record("letter_issuances", {
        "org_id": org_id,
        "template_id": template["id"],
        "user_id": employee["id"],
        "letter_type": template["letter_type"],
        "title": template["name"],
        "rendered_content": rendered,
        "status": "issued",
        "issued_by": current_user["id"],
        "issued_at": datetime.now(timezone.utc).isoformat(),
    })
    notify_user(org_id, employee["id"], "letter.issued", "HR letter available", f"A {template['letter_type']} letter is available.", "letter_issuance", issuance["id"])
    store.add_audit_log(current_user["id"], org_id, "letter.issued", {"record_id": issuance["id"], "user_id": employee["id"]})
    return issuance


@router.get("/letters")
def list_letters(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _owned("letter_issuances", current_user)


@router.post("/letters/{letter_id}/signature-requests", status_code=status.HTTP_201_CREATED)
def request_signature(letter_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    letter = _record("letter_issuances", letter_id, org_id, "Issued letter")
    signer_email = str(payload.get("signer_email", "")).strip().lower()
    signer = store.get_user_by_email(signer_email)
    if signer is None or signer.get("org_id") != org_id or signer["id"] != letter["user_id"]:
        raise HTTPException(status_code=422, detail="Signer must be the employee receiving this letter")
    signature = store.create_module_record("esignature_requests", {
        "org_id": org_id,
        "letter_id": letter_id,
        "user_id": signer["id"],
        "signer_email": signer_email,
        "status": "requested",
        "requested_by": current_user["id"],
        "requested_at": datetime.now(timezone.utc).isoformat(),
    })
    store.update_module_record("letter_issuances", letter_id, org_id, {"signature_status": "requested", "signature_request_id": signature["id"]})
    notify_user(org_id, signer["id"], "signature.requested", "Signature requested", f"Please review and sign {letter['title']}.", "esignature_request", signature["id"])
    return signature


@router.get("/signatures")
def list_signature_requests(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _owned("esignature_requests", current_user)


@router.patch("/signatures/{signature_id}/sign")
def sign_letter(signature_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    signature = _record("esignature_requests", signature_id, org_id, "Signature request")
    if signature["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Signature request not found")
    if signature["status"] != "requested":
        raise HTTPException(status_code=409, detail="Signature request has already been processed")
    if not payload.get("confirmed"):
        raise HTTPException(status_code=422, detail="Explicit signature confirmation is required")
    signed_at = datetime.now(timezone.utc).isoformat()
    updated = store.update_module_record("esignature_requests", signature_id, org_id, {
        "status": "signed",
        "signed_at": signed_at,
        "signature_text": f"{current_user['first_name']} {current_user['last_name']}",
        "confirmation": True,
    })
    store.update_module_record("letter_issuances", signature["letter_id"], org_id, {"signature_status": "signed", "signed_at": signed_at})
    store.add_audit_log(current_user["id"], org_id, "letter.signed", {"record_id": signature_id})
    return updated


@router.post("/reports/{report_type}")
def export_report(
    report_type: str,
    filters: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES)),
) -> Response:
    org_id = _org_id(current_user)
    report_modules = {
        "employees": "employees",
        "attendance": "attendance_records",
        "leave": "leave_applications",
        "expenses": "expense_claims",
        "payroll": "payslips",
        "overtime": "overtime_records",
        "recruitment": "candidate_applications",
        "onboarding": "onboarding_tasks",
        "performance": "performance_reviews",
        "documents": "employee_documents",
        "pf": "pf_contribution_records",
        "esi": "esi_contribution_records",
        "tax": "tax_declarations",
        "insurance": "insurance_claims",
        "exit": "exit_requests",
    }
    module = report_modules.get(report_type)
    if module is None:
        raise HTTPException(status_code=404, detail="Report type not found")
    records = store.list_employees(org_id) if module == "employees" else store.list_module_records(module, org_id)
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    department = filters.get("department")
    location = filters.get("location")
    employee_id = filters.get("employee_id")
    status_filter = filters.get("status")
    date_field = "work_date" if report_type in {"attendance", "overtime"} else ("expense_date" if report_type == "expenses" else ("start_date" if report_type == "leave" else None))
    if date_field and (start_date or end_date):
        records = [item for item in records if (not start_date or item.get(date_field, "") >= start_date) and (not end_date or item.get(date_field, "") <= end_date)]
    if department:
        employee_emails = {item["email"] for item in store.list_employees(org_id) if item.get("department") == department}
        employee_ids = {user["id"] for user in store.users.values() if user.get("org_id") == org_id and user.get("email") in employee_emails}
        records = [item for item in records if item.get("user_id", item.get("employee_user_id")) in employee_ids or item.get("email") in employee_emails]
    if location:
        employee_emails = {item["email"] for item in store.list_employees(org_id) if item.get("location") == location}
        employee_ids = {user["id"] for user in store.users.values() if user.get("org_id") == org_id and user.get("email") in employee_emails}
        records = [item for item in records if item.get("user_id", item.get("employee_user_id")) in employee_ids or item.get("email") in employee_emails]
    if employee_id:
        records = [item for item in records if item.get("user_id", item.get("employee_user_id")) == employee_id or item.get("id") == employee_id]
    if status_filter:
        records = [item for item in records if item.get("status") == status_filter]
    output = io.StringIO()
    if records:
        headers = sorted({key for item in records for key in item if key != "storage_path"})
        writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for item in records:
            writer.writerow({key: value if isinstance(value, (str, int, float, bool)) or value is None else str(value) for key, value in item.items() if key != "storage_path"})
    store.add_audit_log(current_user["id"], org_id, "report.exported", {"report_type": report_type, "record_count": len(records), "filters": filters})
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={report_type}-report.csv"})
