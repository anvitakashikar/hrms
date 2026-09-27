from datetime import date, datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.holiday_service import get_applicable_holidays
from app.services.policy_service import get_applicable_policies

router = APIRouter()
store = get_store()
HR_ROLES = ("admin", "hr")
MANAGER_ROLES = ("admin", "hr", "manager")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _records(module: str, user: Dict[str, Any]) -> List[Dict[str, Any]]:
    org_id = _org_id(user)
    items = store.list_module_records(module, org_id)
    if user.get("role") not in MANAGER_ROLES:
        items = [item for item in items if item.get("user_id", item.get("owner_user_id", item.get("employee_user_id"))) == user["id"]]
    return items


def _answer(query: str, user: Dict[str, Any]) -> Dict[str, Any]:
    text = query.casefold()
    actions = ["Open the relevant HR module to review or change a record."]
    if "leave" in text:
        items = _records("leave_applications", user)
        approved = sum(1 for item in items if item.get("status") == "approved")
        pending = sum(1 for item in items if item.get("status") == "pending")
        if "balance" in text or "how many leaves" in text:
            summary = f"I found {approved} approved and {pending} pending leave requests. This workspace has no allocated balance configured for your leave types, so I cannot report a remaining balance."
        elif user.get("role") in HR_ROLES and ("team" in text or "employees" in text or "organization" in text):
            today = date.today().isoformat()
            on_leave = [item for item in items if item.get("status") == "approved" and item.get("start_date", "") <= today <= item.get("end_date", "")]
            summary = f"{len(on_leave)} employees have an approved leave application covering today."
        else:
            summary = f"Your leave requests: {approved} approved, {pending} awaiting review, {len(items) - approved - pending} in other states."
        return {"summary": summary, "sources": [{"module": "leave", "record_count": len(items)}], "actions": actions}

    if "attendance" in text or "late" in text or "working hours" in text:
        items = _records("attendance_records", user)
        month = date.today().strftime("%Y-%m")
        recent = [item for item in items if item.get("work_date", "").startswith(month)]
        late = sum(1 for item in recent if int(item.get("late_minutes", 0)) > 0)
        working_minutes = sum(int(item.get("working_minutes", 0)) for item in recent)
        summary = f"Attendance this month: {len(recent)} records, {late} late arrivals, {working_minutes / 60:.1f} recorded working hours."
        return {"summary": summary, "sources": [{"module": "attendance", "month": month, "record_count": len(recent)}], "actions": actions}

    if "document" in text or "missing" in text or "verification" in text:
        documents = _records("employee_documents", user)
        pending = sum(1 for item in documents if item.get("status") == "pending_verification")
        rejected = sum(1 for item in documents if item.get("status") == "rejected")
        if user.get("role") in HR_ROLES and "missing" in text:
            categories = [item for item in store.list_module_records("document_categories", _org_id(user)) if item.get("required") and item.get("active")]
            employees = [item for item in store.users.values() if item.get("org_id") == user["org_id"] and item.get("role") != "admin"]
            missing = sum(1 for employee in employees for category in categories if not any(doc.get("owner_user_id") == employee["id"] and doc.get("category_id") == category["id"] and doc.get("status") == "approved" for doc in documents))
            summary = f"There are {missing} missing required employee documents and {pending} documents awaiting verification."
        else:
            summary = f"Your documents: {pending} awaiting verification and {rejected} rejected."
        return {"summary": summary, "sources": [{"module": "documents", "record_count": len(documents)}], "actions": actions}

    if "expense" in text or "claim" in text:
        items = _records("expense_claims", user)
        pending = sum(1 for item in items if item.get("status") in {"submitted", "pending"})
        approved = sum(1 for item in items if item.get("status") == "approved")
        summary = f"Expense claims: {approved} approved and {pending} awaiting review, from {len(items)} total claims."
        return {"summary": summary, "sources": [{"module": "expenses", "record_count": len(items)}], "actions": actions}

    if "payslip" in text or "payroll" in text or "salary" in text:
        items = _records("payslips", user)
        available = [item for item in items if item.get("status") == "available"]
        available.sort(key=lambda item: item.get("period_end", ""), reverse=True)
        if available:
            latest = available[0]
            summary = f"Your latest available payslip is for {latest['period_start'][:7]} with net pay {latest['net_pay']:.2f} {latest.get('currency', '')}."
        else:
            summary = "There are no finalized payslips available for your account."
        return {"summary": summary, "sources": [{"module": "payroll", "record_count": len(available)}], "actions": ["Open Payroll to view or download an available payslip."]}

    if "onboarding" in text or "overdue" in text:
        if user.get("role") not in HR_ROLES:
            return {"summary": "Organization onboarding task data is restricted to HR and administrators.", "sources": [], "actions": []}
        tasks = store.list_module_records("onboarding_tasks", _org_id(user))
        overdue = [item for item in tasks if item.get("status") != "completed" and item.get("due_date", "") < date.today().isoformat()]
        return {"summary": f"There are {len(overdue)} overdue onboarding tasks across {len(tasks)} assigned tasks.", "sources": [{"module": "onboarding", "record_count": len(tasks)}], "actions": actions}

    return {"summary": "I could not match that question to available HR records. Try asking about your attendance, leave requests, expenses, documents, payslips, or onboarding tasks.", "sources": [], "actions": []}


@router.post("/assistant")
def ai_assistant(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    query = str(payload.get("prompt", "")).strip()
    if not query:
        raise HTTPException(status_code=422, detail="A question is required")
    result = _answer(query, current_user)
    result["prompt"] = query
    result["organization_id"] = current_user.get("org_id")
    if current_user.get("org_id"):
        store.create_module_record("ai_query_logs", {
            "org_id": current_user["org_id"],
            "user_id": current_user["id"],
            "query": query,
            "source_modules": [item["module"] for item in result["sources"]],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return result


@router.post("/policy-assistant")
def policy_assistant(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=422, detail="A policy question is required")
    text = question.casefold()
    process = next((name for name in ("leave", "attendance", "expense", "overtime", "payroll") if name in text), None)
    policies = [item for item in get_applicable_policies(current_user) if not process or item.get("process") == process]
    grounded = [{"policy": item["name"], "process": item["process"], "description": item.get("description", ""), "rules": [{"key": rule["key"], "value": rule["value"]} for rule in item.get("rules", [])]} for item in policies]
    if not grounded:
        answer = "No active configured policy matched your question. I will not infer or invent a rule. Contact HR for clarification."
    else:
        answer = "Configured policy information: " + "; ".join(
            f"{item['policy']}: " + (", ".join(f"{rule['key']} = {rule['value']}" for rule in item["rules"]) or item["description"] or "No detailed rules are configured")
            for item in grounded
        )
    return {"answer": answer, "sources": grounded}


@router.post("/search")
def natural_language_search(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    query = str(payload.get("query", "")).strip().casefold()
    if not query:
        raise HTTPException(status_code=422, detail="A search query is required")
    if "employee" in query and current_user.get("role") not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Organization-wide employee search is restricted to HR and administrators")
    org_id = _org_id(current_user)
    if "overdue" in query and "task" in query:
        if current_user.get("role") not in HR_ROLES:
            raise HTTPException(status_code=403, detail="Organization onboarding search is restricted to HR and administrators")
        items = [item for item in store.list_module_records("onboarding_tasks", org_id) if item.get("status") != "completed" and item.get("due_date", "") < date.today().isoformat()]
        return {"count": len(items), "results": items, "source": "onboarding_tasks"}
    if "regularization" in query or "regularisation" in query:
        if current_user.get("role") not in MANAGER_ROLES:
            items = [item for item in store.list_module_records("attendance_regularization_requests", org_id) if item.get("user_id") == current_user["id"]]
        else:
            items = store.list_module_records("attendance_regularization_requests", org_id)
        pending = [item for item in items if item.get("status") == "pending"]
        return {"count": len(pending), "results": pending, "source": "attendance_regularization_requests"}
    if "document" in query:
        items = store.list_module_records("employee_documents", org_id)
        if current_user.get("role") not in HR_ROLES:
            items = [item for item in items if item.get("owner_user_id") == current_user["id"]]
        if "pending" in query:
            items = [item for item in items if item.get("status") == "pending_verification"]
        return {"count": len(items), "results": [{key: value for key, value in item.items() if key != "storage_path"} for item in items], "source": "employee_documents"}
    if "department" in query and current_user.get("role") in HR_ROLES:
        employees = store.list_employees(org_id)
        departments: Dict[str, int] = {}
        for employee in employees:
            department = employee.get("department", "Unassigned")
            departments[department] = departments.get(department, 0) + 1
        return {"count": len(employees), "results": departments, "source": "employees"}
    raise HTTPException(status_code=422, detail="Search supports pending documents, overdue tasks, regularization requests, and HR department summaries")


@router.post("/attendance-anomalies")
def attendance_anomalies(current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    records = store.list_module_records("attendance_records", org_id)
    month = date.today().strftime("%Y-%m")
    records = [item for item in records if item.get("work_date", "").startswith(month)]
    by_user: Dict[str, List[Dict[str, Any]]] = {}
    for item in records:
        by_user.setdefault(item["user_id"], []).append(item)
    insights = []
    for user_id, items in by_user.items():
        late_count = sum(1 for item in items if int(item.get("late_minutes", 0)) > 0)
        regularizations = [item for item in store.list_module_records("attendance_regularization_requests", org_id) if item.get("user_id") == user_id and item.get("work_date", "").startswith(month)]
        unusual_hours = [item for item in items if item.get("working_minutes", 0) > 720]
        if late_count >= 3:
            insights.append({"user_id": user_id, "type": "repeated_late_arrivals", "count": late_count, "description": "Repeated late arrivals detected; review context before taking action."})
        if len(regularizations) >= 3:
            insights.append({"user_id": user_id, "type": "repeated_regularization", "count": len(regularizations), "description": "Repeated attendance corrections detected; review for data quality."})
        if unusual_hours:
            insights.append({"user_id": user_id, "type": "unusual_working_hours", "count": len(unusual_hours), "description": "Long working-hour records detected; verify attendance data."})
    return {"period": month, "insights": insights, "automated_actions": []}


@router.post("/insights")
def create_insight_report(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    report_type = payload.get("report_type")
    modules = {
        "workforce": "employees",
        "attendance": "attendance_records",
        "leave": "leave_applications",
        "expenses": "expense_claims",
        "recruitment": "candidate_applications",
        "onboarding": "onboarding_tasks",
        "performance": "performance_reviews",
    }
    if report_type not in modules:
        raise HTTPException(status_code=422, detail="Unsupported insight report type")
    if report_type == "workforce":
        records = store.list_employees(org_id)
    else:
        records = store.list_module_records(modules[report_type], org_id)
    report = store.create_module_record("ai_insight_reports", {
        "org_id": org_id,
        "report_type": report_type,
        "generated_by": current_user["id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "summary": f"{report_type.title()} report generated from {len(records)} organization records.",
    })
    store.add_audit_log(current_user["id"], org_id, "ai.insight_report.generated", {"record_id": report["id"], "report_type": report_type})
    return report


@router.post("/actions/propose", status_code=status.HTTP_201_CREATED)
def propose_action(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    action_type = payload.get("action_type")
    if action_type not in {"report", "leave_request", "announcement"}:
        raise HTTPException(status_code=422, detail="Unsupported AI action proposal")
    if action_type == "announcement" and current_user.get("role") not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR/Admin may prepare organization announcements")
    action = store.create_module_record("ai_action_audit_logs", {
        "org_id": _org_id(current_user),
        "user_id": current_user["id"],
        "action_type": action_type,
        "payload": payload.get("payload", {}),
        "status": "awaiting_confirmation",
        "proposed_at": datetime.now(timezone.utc).isoformat(),
    })
    return action


@router.post("/actions/{action_id}/confirm")
def confirm_action(action_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    action = store.get_module_record("ai_action_audit_logs", action_id, org_id)
    if action is None or action.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="Action proposal not found")
    if action["status"] != "awaiting_confirmation":
        raise HTTPException(status_code=409, detail="Action proposal has already been processed")
    if action["action_type"] == "announcement":
        raise HTTPException(status_code=409, detail="Announcement execution must use the authorized announcements workflow")
    result = None
    if action["action_type"] == "report":
        if current_user.get("role") not in HR_ROLES:
            raise HTTPException(status_code=403, detail="Only HR/Admin may generate organization reports")
        result = create_insight_report({"report_type": action["payload"].get("report_type", "workforce")}, current_user)
    updated = store.update_module_record("ai_action_audit_logs", action_id, org_id, {
        "status": "confirmed",
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "result_id": result.get("id") if result else None,
    })
    store.add_audit_log(current_user["id"], org_id, "ai.action.confirmed", {"record_id": action_id, "action_type": action["action_type"]})
    return {"action": updated, "result": result}
