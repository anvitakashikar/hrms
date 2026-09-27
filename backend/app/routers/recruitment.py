from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles

router = APIRouter()
store = get_store()
RECRUITERS = ("admin", "hr", "manager")
HR_ROLES = ("admin", "hr")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _record(module: str, record_id: str, org_id: str, label: str) -> Dict[str, Any]:
    record = store.get_module_record(module, record_id, org_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return record


@router.post("/requisitions", status_code=status.HTTP_201_CREATED)
def create_requisition(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    title = str(payload.get("title", "")).strip()
    try:
        openings = int(payload.get("openings", 1))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Openings must be a positive integer") from exc
    if not title or openings < 1:
        raise HTTPException(status_code=422, detail="Title and a positive number of openings are required")
    item = store.create_module_record("job_requisitions", {
        "org_id": org_id,
        "title": title,
        "department": str(payload.get("department", "General")).strip(),
        "designation": str(payload.get("designation", title)).strip(),
        "openings": openings,
        "requirements": payload.get("requirements", []),
        "justification": str(payload.get("justification", "")).strip(),
        "status": "pending_approval",
        "requested_by": current_user["id"],
    })
    store.add_audit_log(current_user["id"], org_id, "recruitment.requisition.created", {"record_id": item["id"]})
    return item


@router.get("/requisitions")
def list_requisitions(current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> List[Dict[str, Any]]:
    return store.list_module_records("job_requisitions", _org_id(current_user))


@router.patch("/requisitions/{requisition_id}/decision")
def decide_requisition(
    requisition_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    decision = payload.get("status")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Status must be approved or rejected")
    requisition = _record("job_requisitions", requisition_id, org_id, "Requisition")
    if requisition["status"] != "pending_approval":
        raise HTTPException(status_code=409, detail="Requisition has already been reviewed")
    updated = store.update_module_record("job_requisitions", requisition_id, org_id, {
        "status": decision,
        "reviewed_by": current_user["id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "comment": str(payload.get("comment", "")).strip(),
    })
    store.add_audit_log(current_user["id"], org_id, f"recruitment.requisition.{decision}", {"record_id": requisition_id})
    return updated


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    title = str(payload.get("title", "")).strip()
    department = str(payload.get("department", "")).strip()
    try:
        openings = int(payload.get("open_positions", 1))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="open_positions must be a positive integer") from exc
    if not title or not department or openings < 1:
        raise HTTPException(status_code=422, detail="Title, department, and positive opening count are required")
    item = store.create_module_record("job_postings", {
        "org_id": org_id,
        "title": title,
        "department": department,
        "open_positions": openings,
        "description": str(payload.get("description", "")).strip(),
        "location": payload.get("location"),
        "employment_type": payload.get("employment_type", "full_time"),
        "status": "open",
        "created_by": current_user["id"],
    })
    store.add_audit_log(current_user["id"], org_id, "recruitment.job_posting.created", {"record_id": item["id"]})
    return item


@router.get("/jobs")
def list_jobs(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    return store.list_module_records("job_postings", current_user["org_id"])


@router.patch("/jobs/{job_id}")
def update_job(job_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    allowed = {key: payload[key] for key in ("title", "department", "open_positions", "description", "location", "employment_type", "status") if key in payload}
    if "status" in allowed and allowed["status"] not in {"open", "closed", "draft"}:
        raise HTTPException(status_code=422, detail="Job status must be open, closed, or draft")
    job = store.update_module_record("job_postings", job_id, org_id, allowed)
    if job is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    store.add_audit_log(current_user["id"], org_id, "recruitment.job_posting.updated", {"record_id": job_id, "changes": allowed})
    return job


@router.post("/applicants", status_code=status.HTTP_201_CREATED)
def create_applicant(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    job = _record("job_postings", payload.get("job_id", ""), org_id, "Job")
    if job["status"] != "open":
        raise HTTPException(status_code=409, detail="Applications are closed for this job")
    name = str(payload.get("candidate_name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    if not name or "@" not in email:
        raise HTTPException(status_code=422, detail="Candidate name and valid email are required")
    candidate = store.create_module_record("candidates", {
        "org_id": org_id,
        "candidate_name": name,
        "email": email,
        "phone": payload.get("phone"),
        "skills": payload.get("skills", []),
        "qualifications": payload.get("qualifications", []),
        "experience_years": payload.get("experience_years"),
    })
    application = store.create_module_record("candidate_applications", {
        "org_id": org_id,
        "candidate_id": candidate["id"],
        "job_id": job["id"],
        "candidate_name": name,
        "email": email,
        "status": payload.get("status", "applied"),
        "source": payload.get("source"),
    })
    application["candidate"] = candidate
    store.add_audit_log(current_user["id"], org_id, "recruitment.candidate.applied", {"record_id": application["id"], "job_id": job["id"]})
    return application


@router.get("/applicants")
def list_applicants(current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> List[Dict[str, Any]]:
    return store.list_module_records("candidate_applications", _org_id(current_user))


@router.patch("/applicants/{application_id}")
def update_applicant(application_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    allowed = {key: payload[key] for key in ("status", "assigned_to", "notes") if key in payload}
    applicant = store.update_module_record("candidate_applications", application_id, org_id, allowed)
    if applicant is None:
        raise HTTPException(status_code=404, detail="Candidate application not found")
    store.add_audit_log(current_user["id"], org_id, "recruitment.candidate.updated", {"record_id": application_id, "changes": allowed})
    return applicant


@router.post("/interviews", status_code=status.HTTP_201_CREATED)
def schedule_interview(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    application = _record("candidate_applications", payload.get("application_id", ""), org_id, "Candidate application")
    try:
        scheduled_at = datetime.fromisoformat(str(payload["scheduled_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="scheduled_at must be an ISO-8601 timestamp") from exc
    panel = payload.get("panel_user_ids", [])
    if any((store.get_user_by_id(user_id) or {}).get("org_id") != org_id for user_id in panel):
        raise HTTPException(status_code=422, detail="Interview panel members must belong to this organization")
    interview = store.create_module_record("interview_schedules", {
        "org_id": org_id,
        "application_id": application["id"],
        "candidate_id": application["candidate_id"],
        "scheduled_at": scheduled_at.isoformat(),
        "duration_minutes": max(15, int(payload.get("duration_minutes", 60))),
        "interview_type": payload.get("interview_type", "video"),
        "panel_user_ids": panel,
        "meeting_location": payload.get("meeting_location"),
        "status": "scheduled",
        "created_by": current_user["id"],
    })
    store.add_audit_log(current_user["id"], org_id, "recruitment.interview.scheduled", {"record_id": interview["id"]})
    return interview


@router.get("/interviews")
def list_interviews(current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> List[Dict[str, Any]]:
    return store.list_module_records("interview_schedules", _org_id(current_user))


@router.post("/interviews/{interview_id}/feedback", status_code=status.HTTP_201_CREATED)
def add_interview_feedback(interview_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    interview = _record("interview_schedules", interview_id, org_id, "Interview")
    if current_user.get("role") not in HR_ROLES and current_user["id"] not in interview.get("panel_user_ids", []):
        raise HTTPException(status_code=403, detail="Only assigned panel members can submit interview feedback")
    feedback = store.create_module_record("interview_feedback", {
        "org_id": org_id,
        "interview_id": interview_id,
        "candidate_id": interview["candidate_id"],
        "reviewer_user_id": current_user["id"],
        "rating": max(1, min(5, int(payload.get("rating", 3)))),
        "recommendation": payload.get("recommendation", "undecided"),
        "notes": str(payload.get("notes", "")).strip(),
    })
    return feedback


@router.get("/interviews/{interview_id}/feedback")
def list_interview_feedback(interview_id: str, current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    _record("interview_schedules", interview_id, org_id, "Interview")
    return [item for item in store.list_module_records("interview_feedback", org_id) if item.get("interview_id") == interview_id]


@router.post("/offers", status_code=status.HTTP_201_CREATED)
def create_offer(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    application = _record("candidate_applications", payload.get("application_id", ""), org_id, "Candidate application")
    try:
        salary = float(payload["salary"])
        expires = datetime.fromisoformat(str(payload["expires_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Valid salary and ISO-8601 expiry are required") from exc
    if salary < 0:
        raise HTTPException(status_code=422, detail="Offer salary cannot be negative")
    offer = store.create_module_record("job_offers", {
        "org_id": org_id,
        "application_id": application["id"],
        "candidate_id": application["candidate_id"],
        "salary": salary,
        "currency": payload.get("currency", "USD"),
        "designation": payload.get("designation", ""),
        "start_date": payload.get("start_date"),
        "expires_at": expires.isoformat(),
        "status": "offered",
        "created_by": current_user["id"],
    })
    store.update_module_record("candidate_applications", application["id"], org_id, {"status": "offer"})
    store.add_audit_log(current_user["id"], org_id, "recruitment.offer.created", {"record_id": offer["id"]})
    return offer


@router.get("/offers")
def list_offers(current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> List[Dict[str, Any]]:
    return store.list_module_records("job_offers", _org_id(current_user))


@router.patch("/offers/{offer_id}/decision")
def decide_offer(offer_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*RECRUITERS))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    decision = payload.get("status")
    if decision not in {"accepted", "declined", "withdrawn"}:
        raise HTTPException(status_code=422, detail="Unsupported offer decision")
    offer = _record("job_offers", offer_id, org_id, "Offer")
    if offer["status"] != "offered":
        raise HTTPException(status_code=409, detail="Offer has already been decided")
    updated = store.update_module_record("job_offers", offer_id, org_id, {"status": decision, "decided_at": datetime.now(timezone.utc).isoformat()})
    store.add_audit_log(current_user["id"], org_id, f"recruitment.offer.{decision}", {"record_id": offer_id})
    return updated
