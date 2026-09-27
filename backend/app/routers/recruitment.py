from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user, require_roles

router = APIRouter()

job_store: Dict[str, Dict[str, Any]] = {}
applicant_store: Dict[str, Dict[str, Any]] = {}


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles("admin", "hr", "manager")),
) -> Dict[str, Any]:
    job_id = f"job-{len(job_store) + 1}"
    item = {
        "id": job_id,
        "org_id": current_user["org_id"],
        "title": payload["title"],
        "department": payload["department"],
        "open_positions": payload["open_positions"],
        "status": "open",
    }
    job_store[job_id] = item
    return item


@router.get("/jobs")
def list_jobs(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return [item for item in job_store.values() if item["org_id"] == current_user["org_id"]]


@router.post("/applicants", status_code=status.HTTP_201_CREATED)
def create_applicant(
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles("admin", "hr", "manager")),
) -> Dict[str, Any]:
    job = job_store.get(payload["job_id"])
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job["org_id"] != current_user["org_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    applicant_id = f"applicant-{len(applicant_store) + 1}"
    item = {
        "id": applicant_id,
        "org_id": current_user["org_id"],
        "job_id": payload["job_id"],
        "candidate_name": payload["candidate_name"],
        "email": payload["email"],
        "status": payload.get("status", "screening"),
    }
    applicant_store[applicant_id] = item
    return item


@router.get("/applicants")
def list_applicants(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return [item for item in applicant_store.values() if item["org_id"] == current_user["org_id"]]
