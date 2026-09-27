from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.notification_service import notify_user

router = APIRouter()
store = get_store()


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _record(collection: str, record_id: str, org_id: str, label: str) -> Dict[str, Any]:
    record = store.get_module_record(collection, record_id, org_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return record


def _posh_access(user: Dict[str, Any], org_id: str) -> bool:
    if user.get("org_id") != org_id:
        return False
    if user.get("role") == "admin":
        return True
    return any(item.get("user_id") == user["id"] and item.get("active") for item in store.list_module_records("posh_committee_members", org_id))


def _posh_complaint(complaint_id: str, org_id: str) -> Dict[str, Any]:
    complaint = store.get_module_record("posh_complaints", complaint_id, org_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="POSH case not found")
    return complaint


def _audit_sensitive_access(user: Dict[str, Any], org_id: str, record_type: str, record_id: str) -> None:
    store.create_module_record("sensitive_data_access_logs", {
        "org_id": org_id,
        "user_id": user["id"],
        "record_type": record_type,
        "record_id": record_id,
        "accessed_at": datetime.now(timezone.utc).isoformat(),
    })
    store.add_audit_log(user["id"], org_id, "sensitive_data.accessed", {"record_type": record_type, "record_id": record_id})


@router.post("/posh/committee", status_code=status.HTTP_201_CREATED)
def add_posh_committee_member(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles("admin"))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    user = store.get_user_by_id(str(payload.get("user_id", "")))
    if user is None or user.get("org_id") != org_id:
        raise HTTPException(status_code=422, detail="Committee member must belong to this organization")
    if user["id"] == current_user["id"] and payload.get("role") == "complaint_handler":
        raise HTTPException(status_code=422, detail="A complaint handler cannot assign themselves")
    return store.create_module_record("posh_committee_members", {
        "org_id": org_id,
        "user_id": user["id"],
        "name": payload.get("name") or f"{user['first_name']} {user['last_name']}",
        "committee_role": payload.get("committee_role", "member"),
        "term_start": payload.get("term_start"),
        "term_end": payload.get("term_end"),
        "active": True,
        "created_by": current_user["id"],
    })


@router.get("/posh/committee")
def list_posh_committee(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    if current_user.get("role") != "admin" and not _posh_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="POSH committee access is restricted")
    return store.list_module_records("posh_committee_members", org_id)


@router.post("/posh/acknowledgements", status_code=status.HTTP_201_CREATED)
def acknowledge_posh_policy(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    policy_version = str(payload.get("policy_version", "")).strip()
    if not policy_version:
        raise HTTPException(status_code=422, detail="Policy version is required")
    existing = [item for item in store.list_module_records("posh_policy_acknowledgements", org_id) if item.get("user_id") == current_user["id"] and item.get("policy_version") == policy_version]
    if existing:
        return existing[0]
    return store.create_module_record("posh_policy_acknowledgements", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "policy_version": policy_version,
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
    })


@router.get("/posh/acknowledgements")
def list_posh_acknowledgements(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    items = store.list_module_records("posh_policy_acknowledgements", org_id)
    if current_user.get("role") != "admin" and not _posh_access(current_user, org_id):
        items = [item for item in items if item.get("user_id") == current_user["id"]]
    return items


@router.post("/posh/complaints", status_code=status.HTTP_201_CREATED)
def submit_posh_complaint(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    description = str(payload.get("description", "")).strip()
    incident_date = str(payload.get("incident_date", "")).strip()
    if not description or not incident_date:
        raise HTTPException(status_code=422, detail="Incident date and complaint description are required")
    complaint = store.create_module_record("posh_complaints", {
        "org_id": org_id,
        "complainant_user_id": current_user["id"],
        "respondent_name": str(payload.get("respondent_name", "")).strip(),
        "incident_date": incident_date,
        "description": description,
        "confidentiality_requested": bool(payload.get("confidentiality_requested", True)),
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    for member in store.list_module_records("posh_committee_members", org_id):
        if member.get("active"):
            notify_user(org_id, member["user_id"], "posh.case.submitted", "Restricted POSH case submitted", "A restricted case requires committee review.", "posh_complaint", complaint["id"])
    _audit_sensitive_access(current_user, org_id, "posh_complaint", complaint["id"])
    return {"id": complaint["id"], "status": complaint["status"], "submitted_at": complaint["submitted_at"]}


@router.get("/posh/complaints")
def list_posh_complaints(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    if not _posh_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="POSH case access is restricted to the administrator and committee")
    items = store.list_module_records("posh_complaints", org_id)
    for item in items:
        _audit_sensitive_access(current_user, org_id, "posh_complaint", item["id"])
    return items


@router.patch("/posh/complaints/{complaint_id}/status")
def update_posh_case_status(complaint_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    if not _posh_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="POSH case access is restricted to the administrator and committee")
    status_value = payload.get("status")
    if status_value not in {"under_review", "resolved", "closed", "referred"}:
        raise HTTPException(status_code=422, detail="Unsupported POSH case status")
    complaint = _posh_complaint(complaint_id, org_id)
    updated = store.update_module_record("posh_complaints", complaint_id, org_id, {
        "status": status_value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    store.create_module_record("posh_case_timeline", {
        "org_id": org_id,
        "complaint_id": complaint_id,
        "actor_user_id": current_user["id"],
        "event": "status_changed",
        "status": status_value,
        "note": str(payload.get("note", "")).strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    _audit_sensitive_access(current_user, org_id, "posh_complaint", complaint_id)
    return {"id": updated["id"], "status": updated["status"]}


@router.get("/posh/complaints/{complaint_id}/timeline")
def posh_case_timeline(complaint_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    if not _posh_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="POSH case access is restricted to the administrator and committee")
    _posh_complaint(complaint_id, org_id)
    _audit_sensitive_access(current_user, org_id, "posh_case_timeline", complaint_id)
    return [item for item in store.list_module_records("posh_case_timeline", org_id) if item.get("complaint_id") == complaint_id]


@router.post("/privacy/consents", status_code=status.HTTP_201_CREATED)
def record_consent(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    purpose = str(payload.get("purpose", "")).strip()
    if not purpose:
        raise HTTPException(status_code=422, detail="Consent purpose is required")
    granted = bool(payload.get("granted", True))
    item = store.create_module_record("consent_logs", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "purpose": purpose,
        "granted": granted,
        "policy_version": payload.get("policy_version"),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    store.add_audit_log(current_user["id"], org_id, "privacy.consent.recorded", {"record_id": item["id"], "purpose": purpose, "granted": granted})
    return item

def _owner_items(collection: str, user: Dict[str, Any]) -> List[Dict[str, Any]]:
    org_id = _org_id(user)
    items = store.list_module_records(collection, org_id)
    if user.get("role") != "admin":
        items = [item for item in items if item.get("user_id") == user["id"]]
    else:
        store.add_audit_log(user["id"], org_id, "sensitive_data.organization_access", {"collection": collection, "count": len(items)})
    return items


@router.get("/privacy/consents")
def list_consents(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _owner_items("consent_logs", current_user)


@router.post("/privacy/requests", status_code=status.HTTP_201_CREATED)
def create_data_subject_request(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    request_type = payload.get("request_type")
    if request_type not in {"access", "correction", "deletion", "export"}:
        raise HTTPException(status_code=422, detail="Unsupported data subject request type")
    item = store.create_module_record("data_subject_requests", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "request_type": request_type,
        "description": str(payload.get("description", "")).strip(),
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    store.add_audit_log(current_user["id"], org_id, "privacy.data_subject_request.submitted", {"record_id": item["id"], "request_type": request_type})
    return item


@router.get("/privacy/requests")
def list_data_subject_requests(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _owner_items("data_subject_requests", current_user)


@router.patch("/privacy/requests/{request_id}/decision")
def decide_data_subject_request(request_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles("admin"))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    decision = payload.get("status")
    if decision not in {"approved", "rejected", "completed"}:
        raise HTTPException(status_code=422, detail="Unsupported request decision")
    item = _record("data_subject_requests", request_id, org_id, "Data subject request")
    updated = store.update_module_record("data_subject_requests", request_id, org_id, {
        "status": decision,
        "processed_by": current_user["id"],
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "response": str(payload.get("response", "")).strip(),
    })
    store.add_audit_log(current_user["id"], org_id, "privacy.data_subject_request.processed", {"record_id": request_id, "status": decision})
    notify_user(org_id, item["user_id"], "privacy.request.updated", "Privacy request updated", f"Your data subject request is now {decision}.", "data_subject_request", request_id)
    return updated


@router.post("/privacy/retention-policies", status_code=status.HTTP_201_CREATED)
def create_retention_policy(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles("admin"))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    record_type = str(payload.get("record_type", "")).strip()
    try:
        retention_days = int(payload["retention_days"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="retention_days must be an integer") from exc
    if not record_type or retention_days < 1:
        raise HTTPException(status_code=422, detail="Record type and positive retention period are required")
    policy = store.create_module_record("data_retention_policies", {
        "org_id": org_id,
        "record_type": record_type,
        "retention_days": retention_days,
        "active": True,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    store.add_audit_log(current_user["id"], org_id, "privacy.retention_policy.created", {"record_id": policy["id"]})
    return policy


@router.get("/privacy/retention-policies")
def list_retention_policies(current_user: Dict[str, Any] = Depends(require_roles("admin"))) -> List[Dict[str, Any]]:
    return store.list_module_records("data_retention_policies", _org_id(current_user))


@router.get("/privacy/access-logs")
def list_sensitive_access_logs(current_user: Dict[str, Any] = Depends(require_roles("admin"))) -> List[Dict[str, Any]]:
    return store.list_module_records("sensitive_data_access_logs", _org_id(current_user))
