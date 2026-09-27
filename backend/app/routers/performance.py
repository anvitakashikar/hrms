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


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


@router.post("/goals", status_code=status.HTTP_201_CREATED)
def create_goal(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    title = str(payload.get("title", "")).strip()
    assignee_id = payload.get("employee_user_id") or current_user["id"]
    assignee = store.get_user_by_email(payload["employee_email"]) if payload.get("employee_email") else store.get_user_by_id(assignee_id)
    if assignee:
        assignee_id = assignee["id"]
    if not title or assignee is None or assignee.get("org_id") != org_id:
        raise HTTPException(status_code=422, detail="Goal title and employee in this organization are required")
    if assignee_id != current_user["id"] and current_user.get("role") not in REVIEW_ROLES:
        raise HTTPException(status_code=403, detail="Employees can only create goals for themselves")
    try:
        due_date = date.fromisoformat(payload["due_date"]).isoformat()
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="due_date must use YYYY-MM-DD") from exc
    goal = store.create_module_record("goals", {
        "org_id": org_id,
        "employee_user_id": assignee_id,
        "title": title,
        "description": str(payload.get("description", "")).strip(),
        "due_date": due_date,
        "progress": 0,
        "status": "not_started",
        "created_by": current_user["id"],
    })
    if assignee_id != current_user["id"]:
        notify_user(org_id, assignee_id, "performance.goal.assigned", "Goal assigned", f"A new goal was assigned: {title}.", "goal", goal["id"])
    store.add_audit_log(current_user["id"], org_id, "performance.goal.created", {"record_id": goal["id"], "employee_user_id": assignee_id})
    return goal


@router.get("/goals")
def list_goals(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    goals = store.list_module_records("goals", current_user["org_id"])
    if current_user.get("role") not in REVIEW_ROLES:
        goals = [item for item in goals if item.get("employee_user_id") == current_user["id"]]
    return goals


@router.patch("/goals/{goal_id}")
def update_goal(goal_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    goal = store.get_module_record("goals", goal_id, org_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal["employee_user_id"] != current_user["id"] and current_user.get("role") not in REVIEW_ROLES:
        raise HTTPException(status_code=403, detail="Goal belongs to another employee")
    try:
        progress = int(payload.get("progress", goal["progress"]))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Progress must be an integer") from exc
    if not 0 <= progress <= 100:
        raise HTTPException(status_code=422, detail="Progress must be between 0 and 100")
    status_value = payload.get("status", "completed" if progress == 100 else ("in_progress" if progress else "not_started"))
    if status_value not in {"not_started", "in_progress", "completed", "cancelled"}:
        raise HTTPException(status_code=422, detail="Unsupported goal status")
    updated = store.update_module_record("goals", goal_id, org_id, {"progress": progress, "status": status_value, "updated_by": current_user["id"]})
    store.add_audit_log(current_user["id"], org_id, "performance.goal.updated", {"record_id": goal_id, "progress": progress})
    return updated


@router.post("/cycles", status_code=status.HTTP_201_CREATED)
def create_review_cycle(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    name = str(payload.get("name", "")).strip()
    try:
        start_date = date.fromisoformat(payload["start_date"]).isoformat()
        end_date = date.fromisoformat(payload["end_date"]).isoformat()
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Review dates must use YYYY-MM-DD") from exc
    if not name or end_date < start_date:
        raise HTTPException(status_code=422, detail="Cycle name and valid date range are required")
    cycle = store.create_module_record("performance_review_cycles", {
        "org_id": org_id,
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
        "status": "active",
        "created_by": current_user["id"],
    })
    store.add_audit_log(current_user["id"], org_id, "performance.review_cycle.created", {"record_id": cycle["id"]})
    return cycle


@router.get("/cycles")
def list_review_cycles(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    return store.list_module_records("performance_review_cycles", current_user["org_id"])


@router.post("/reviews", status_code=status.HTTP_201_CREATED)
def create_review(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    employee_user_id = payload.get("employee_user_id", current_user["id"])
    employee = store.get_user_by_email(payload["employee_email"]) if payload.get("employee_email") else store.get_user_by_id(employee_user_id)
    if employee:
        employee_user_id = employee["id"]
    if employee is None or employee.get("org_id") != org_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    review_type = payload.get("review_type", "self")
    if review_type not in {"self", "manager"}:
        raise HTTPException(status_code=422, detail="Review type must be self or manager")
    if review_type == "self" and employee_user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Employees may only submit their own self-review")
    if review_type == "manager" and current_user.get("role") not in REVIEW_ROLES:
        raise HTTPException(status_code=403, detail="Manager or HR permissions are required")
    cycle_id = payload.get("cycle_id")
    cycle = store.get_module_record("performance_review_cycles", cycle_id or "", org_id)
    if cycle is None:
        raise HTTPException(status_code=422, detail="A review cycle in this organization is required")
    try:
        rating = int(payload["rating"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Rating must be an integer from 1 to 5") from exc
    if not 1 <= rating <= 5:
        raise HTTPException(status_code=422, detail="Rating must be between 1 and 5")
    notes = str(payload.get("notes", "")).strip()
    review = store.create_module_record("performance_reviews", {
        "org_id": org_id,
        "cycle_id": cycle_id,
        "employee_user_id": employee_user_id,
        "employee_email": employee["email"],
        "reviewer_user_id": current_user["id"],
        "review_type": review_type,
        "rating": rating,
        "notes": notes,
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    store.create_module_record("performance_ratings", {
        "org_id": org_id,
        "cycle_id": cycle_id,
        "employee_user_id": employee_user_id,
        "review_id": review["id"],
        "rating": rating,
        "review_type": review_type,
    })
    if review_type == "manager":
        store.create_module_record("performance_feedback", {
            "org_id": org_id,
            "review_id": review["id"],
            "employee_user_id": employee_user_id,
            "reviewer_user_id": current_user["id"],
            "feedback": notes,
        })
    store.add_audit_log(current_user["id"], org_id, "performance.review.submitted", {"record_id": review["id"], "review_type": review_type})
    return review


@router.get("/reviews")
def list_reviews(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    reviews = store.list_module_records("performance_reviews", current_user["org_id"])
    if current_user.get("role") not in REVIEW_ROLES:
        reviews = [item for item in reviews if item.get("employee_user_id") == current_user["id"]]
    return reviews
