from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_store
from app.dependencies.auth import get_current_user
from app.services.team_service import get_team_user_ids

router = APIRouter()
store = get_store()
HR_ROLES = {"admin", "hr"}


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _for_user(collection: str, user: Dict[str, Any]) -> List[Dict[str, Any]]:
    org_id = _org_id(user)
    items = store.list_module_records(collection, org_id)
    if user.get("role") not in {"admin", "hr", "manager"}:
        items = [item for item in items if item.get("user_id", item.get("employee_user_id", item.get("owner_user_id"))) == user["id"]]
    return items


@router.get("/dashboard")
def role_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    role = current_user.get("role")
    today = date.today().isoformat()
    month = today[:7]
    if role in HR_ROLES:
        employees = store.list_employees(org_id)
        attendance = [item for item in store.list_module_records("attendance_records", org_id) if item.get("work_date", "").startswith(month)]
        leaves = store.list_module_records("leave_applications", org_id)
        expenses = store.list_module_records("expense_claims", org_id)
        payroll_runs = store.list_module_records("payroll_runs", org_id)
        jobs = store.list_module_records("job_postings", org_id)
        applications = store.list_module_records("candidate_applications", org_id)
        tasks = store.list_module_records("onboarding_tasks", org_id)
        goals = store.list_module_records("goals", org_id)
        reviews = store.list_module_records("performance_reviews", org_id)
        documents = store.list_module_records("employee_documents", org_id)
        department_counts: Dict[str, int] = {}
        location_counts: Dict[str, int] = {}
        for employee in employees:
            department = employee.get("department", "Unassigned")
            department_counts[department] = department_counts.get(department, 0) + 1
            location = employee.get("location", "Unassigned")
            location_counts[location] = location_counts.get(location, 0) + 1
        return {
            "role": role,
            "headcount": len(employees),
            "department_distribution": department_counts,
            "location_distribution": location_counts,
            "attendance": {"records_this_month": len(attendance), "late_arrivals": sum(1 for item in attendance if item.get("late_minutes", 0) > 0), "working_minutes": sum(int(item.get("working_minutes", 0)) for item in attendance)},
            "leave": {"pending": sum(1 for item in leaves if item.get("status") == "pending"), "approved": sum(1 for item in leaves if item.get("status") == "approved")},
            "expenses": {"pending": sum(1 for item in expenses if item.get("status") in {"submitted", "pending"}), "approved_amount": round(sum(float(item.get("amount", 0)) for item in expenses if item.get("status") == "approved"), 2)},
            "payroll": {"runs": len(payroll_runs), "latest_status": max(payroll_runs, key=lambda item: item.get("created_at", "")).get("status") if payroll_runs else "not_configured"},
            "recruitment": {"open_jobs": sum(1 for item in jobs if item.get("status") == "open"), "applications": len(applications)},
            "onboarding": {"pending_tasks": sum(1 for item in tasks if item.get("status") != "completed"), "overdue_tasks": sum(1 for item in tasks if item.get("status") != "completed" and item.get("due_date", "") < today)},
            "performance": {"goals": len(goals), "reviews": len(reviews), "average_rating": round(sum(item.get("rating", 0) for item in reviews) / max(len(reviews), 1), 2)},
            "documents": {"pending_verification": sum(1 for item in documents if item.get("status") == "pending_verification"), "expired": sum(1 for item in documents if item.get("expiry_date") and item["expiry_date"] < today)},
        }
    if role == "manager":
        employee_record = store.get_employee_by_user_email(org_id, current_user["email"])
        department = employee_record.get("department") if employee_record else None
        team_emails = {item["email"] for item in store.list_employees(org_id) if department and item.get("department") == department}
        team_ids = get_team_user_ids(current_user)
        attendance = [item for item in store.list_module_records("attendance_records", org_id) if item.get("user_id") in team_ids and item.get("work_date") == today]
        leaves = [item for item in store.list_module_records("leave_applications", org_id) if item.get("user_id") in team_ids]
        expenses = [item for item in store.list_module_records("expense_claims", org_id) if item.get("user_id") in team_ids]
        goals = [item for item in store.list_module_records("goals", org_id) if item.get("employee_user_id") in team_ids]
        return {
            "role": role,
            "team_size": len(team_ids),
            "department": department,
            "attendance_today": len(attendance),
            "pending_leave": sum(1 for item in leaves if item.get("status") == "pending"),
            "pending_expenses": sum(1 for item in expenses if item.get("status") in {"submitted", "pending"}),
            "team_goals": len(goals),
            "goal_progress_average": round(sum(item.get("progress", 0) for item in goals) / max(len(goals), 1), 1),
        }
    attendance = [item for item in _for_user("attendance_records", current_user) if item.get("work_date", "").startswith(month)]
    leaves = _for_user("leave_applications", current_user)
    expenses = _for_user("expense_claims", current_user)
    payslips = [item for item in _for_user("payslips", current_user) if item.get("status") == "available"]
    documents = _for_user("employee_documents", current_user)
    goals = _for_user("goals", current_user)
    notifications = _for_user("notification_logs", current_user)
    return {
        "role": "employee",
        "attendance_this_month": len(attendance),
        "working_minutes_this_month": sum(int(item.get("working_minutes", 0)) for item in attendance),
        "leave_requests": {"pending": sum(1 for item in leaves if item.get("status") == "pending"), "approved": sum(1 for item in leaves if item.get("status") == "approved")},
        "expense_claims": {"pending": sum(1 for item in expenses if item.get("status") in {"submitted", "pending"})},
        "available_payslips": len(payslips),
        "documents_pending": sum(1 for item in documents if item.get("status") in {"pending_verification", "rejected"}),
        "goals": {"count": len(goals), "average_progress": round(sum(item.get("progress", 0) for item in goals) / max(len(goals), 1), 1)},
        "unread_notifications": sum(1 for item in notifications if not item.get("read_at")),
    }
