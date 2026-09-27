import calendar
import csv
import io
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles

router = APIRouter()
store = get_store()
HR_ROLES = ("admin", "hr")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _period(payload: Dict[str, Any]):
    try:
        start = date.fromisoformat(payload["period_start"])
        end = date.fromisoformat(payload["period_end"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Payroll period dates must use YYYY-MM-DD") from exc
    if start > end or start.year != end.year or start.month != end.month:
        raise HTTPException(status_code=422, detail="Payroll runs must cover a valid single calendar month")
    return start, end


def _calculate_payslip(org_id: str, user_id: str, structure: Dict[str, Any], start: date, end: date) -> Dict[str, Any]:
    period_days = (end - start).days + 1
    components = {item["id"]: item for item in store.list_module_records("salary_components", org_id)}
    earnings: Dict[str, float] = {"Base salary": float(structure["base_salary"])}
    deductions: Dict[str, float] = {}
    for component_id in structure.get("component_ids", []):
        component = components.get(component_id)
        if component is None or not component.get("active"):
            continue
        value = float(component.get("value", 0))
        amount = value if component.get("calculation") == "fixed" else float(structure["base_salary"]) * value / 100
        destination = earnings if component["kind"] == "earning" else deductions
        destination[component["name"]] = round(amount, 2)

    base_daily = float(structure["base_salary"]) / period_days
    unpaid_leave_days = 0
    leave_types = {item["name"]: item for item in store.list_module_records("leave_types", org_id)}
    for leave in store.list_module_records("leave_applications", org_id):
        if leave.get("user_id") != user_id or leave.get("status") != "approved":
            continue
        if leave["start_date"] <= end.isoformat() and leave["end_date"] >= start.isoformat():
            leave_type = leave_types.get(leave["leave_type"], {"paid": True})
            if not leave_type.get("paid", True):
                unpaid_leave_days += int(leave.get("chargeable_days", leave.get("calendar_days", 0)))
    unpaid_deduction = round(base_daily * unpaid_leave_days, 2)
    if unpaid_deduction:
        deductions["Unpaid leave"] = unpaid_deduction

    attendance = [item for item in store.list_module_records("attendance_records", org_id) if item.get("user_id") == user_id and start.isoformat() <= item.get("work_date", "") <= end.isoformat()]
    overtime_minutes = sum(int(item.get("overtime_minutes", 0)) for item in attendance)
    overtime_rules = [item for item in store.list_module_records("deduction_rules", org_id) if item.get("active") and item.get("kind") == "overtime"]
    if overtime_minutes and overtime_rules:
        weekday_count = sum(1 for day_number in range(1, period_days + 1) if date(start.year, start.month, day_number).weekday() < 5)
        standard_hours = float(overtime_rules[-1].get("standard_hours_per_day", 8))
        multiplier = float(overtime_rules[-1].get("rate_multiplier", 1.5))
        overtime_amount = float(structure["base_salary"]) / max(weekday_count * standard_hours * 60, 1) * overtime_minutes * multiplier
        earnings["Overtime"] = round(overtime_amount, 2)

    gross = round(sum(earnings.values()), 2)
    rules = [item for item in store.list_module_records("deduction_rules", org_id) if item.get("active")]
    contributions: Dict[str, Dict[str, float]] = {}
    for rule in rules:
        kind = rule.get("kind")
        if kind == "deduction":
            value = float(rule.get("value", 0))
            amount = value if rule.get("calculation") == "fixed" else gross * value / 100
            if amount:
                deductions[rule.get("name", "Configured deduction")] = round(amount, 2)
            continue
        if kind not in {"pf", "esi", "tax"}:
            continue
        if gross < float(rule.get("threshold", 0)):
            continue
        employee_amount = round(gross * float(rule.get("employee_rate", 0)) / 100, 2)
        employer_amount = round(gross * float(rule.get("employer_rate", 0)) / 100, 2)
        label = {"pf": "PF", "esi": "ESI", "tax": "Tax/TDS"}[kind]
        if employee_amount:
            deductions[label] = employee_amount
        contributions[label] = {"employee": employee_amount, "employer": employer_amount}

    recurring = store.list_module_records("employee_deductions", org_id)
    for item in recurring:
        if item.get("user_id") != user_id or not item.get("active"):
            continue
        if not item.get("recurring") and item.get("effective_date") != start.isoformat():
            continue
        amount = float(item.get("amount", 0))
        if item.get("calculation") == "percent":
            amount = gross * amount / 100
        deductions[item["name"]] = round(amount, 2)

    expenses = [item for item in store.list_module_records("expense_claims", org_id) if item.get("user_id") == user_id and item.get("status") == "approved" and start.isoformat() <= item.get("expense_date", "") <= end.isoformat()]
    reimbursements = round(sum(float(item["amount"]) for item in expenses), 2)
    total_deductions = round(sum(deductions.values()), 2)
    return {
        "gross_pay": gross,
        "earnings": earnings,
        "deductions": deductions,
        "total_deductions": total_deductions,
        "reimbursements": reimbursements,
        "net_pay": round(gross - total_deductions + reimbursements, 2),
        "contributions": contributions,
        "unpaid_leave_days": unpaid_leave_days,
        "overtime_minutes": overtime_minutes,
    }


@router.post("/components", status_code=status.HTTP_201_CREATED)
def create_salary_component(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    name = str(payload.get("name", "")).strip()
    kind = payload.get("kind")
    calculation = payload.get("calculation", "fixed")
    if not name or kind not in {"earning", "deduction"} or calculation not in {"fixed", "percent"}:
        raise HTTPException(status_code=422, detail="Name, earning/deduction kind, and fixed/percent calculation are required")
    value = float(payload.get("value", 0))
    if value < 0:
        raise HTTPException(status_code=422, detail="Component value cannot be negative")
    return store.create_module_record("salary_components", {
        "org_id": org_id,
        "name": name,
        "kind": kind,
        "calculation": calculation,
        "value": value,
        "taxable": bool(payload.get("taxable", True)),
        "active": True,
        "created_by": current_user["id"],
    })


@router.get("/components")
def list_salary_components(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return store.list_module_records("salary_components", _org_id(current_user))


@router.post("/structures", status_code=status.HTTP_201_CREATED)
def create_salary_structure(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    employee_id = payload.get("employee_id")
    employee = next((item for item in store.list_employees(org_id) if item["id"] == employee_id), None)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    linked_user = store.get_user_by_email(employee["email"])
    if linked_user is None or linked_user.get("org_id") != org_id:
        raise HTTPException(status_code=422, detail="Employee must have an account in this organization")
    try:
        base_salary = float(payload["base_salary"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="A valid base salary is required") from exc
    if base_salary < 0:
        raise HTTPException(status_code=422, detail="Base salary cannot be negative")
    component_ids = payload.get("component_ids", [])
    valid_components = {item["id"] for item in store.list_module_records("salary_components", org_id)}
    if any(item not in valid_components for item in component_ids):
        raise HTTPException(status_code=422, detail="Salary components must belong to this organization")
    try:
        effective_from = date.fromisoformat(payload.get("effective_from", date.today().isoformat())).isoformat()
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="effective_from must use YYYY-MM-DD") from exc
    prior = [item for item in store.list_module_records("employee_salary_structures", org_id) if item.get("employee_id") == employee_id and not item.get("effective_to")]
    for item in prior:
        effective_to = (date.fromisoformat(effective_from) - timedelta(days=1)).isoformat()
        store.update_module_record("employee_salary_structures", item["id"], org_id, {"effective_to": effective_to})
    structure = store.create_module_record("employee_salary_structures", {
        "org_id": org_id,
        "employee_id": employee_id,
        "user_id": linked_user["id"],
        "base_salary": base_salary,
        "component_ids": component_ids,
        "effective_from": effective_from,
        "effective_to": None,
        "created_by": current_user["id"],
    })
    store.add_audit_log(current_user["id"], org_id, "payroll.salary_structure.created", {"record_id": structure["id"], "employee_id": employee_id, "base_salary": base_salary})
    return structure


@router.get("/structures")
def list_salary_structures(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    items = store.list_module_records("employee_salary_structures", _org_id(current_user))
    if current_user.get("role") not in HR_ROLES:
        items = [item for item in items if item.get("user_id") == current_user["id"]]
    return items


@router.post("/deduction-rules", status_code=status.HTTP_201_CREATED)
def create_deduction_rule(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    kind = payload.get("kind")
    if kind not in {"deduction", "pf", "esi", "tax", "overtime"}:
        raise HTTPException(status_code=422, detail="Unsupported payroll rule kind")
    record = {key: payload[key] for key in ("name", "kind", "employee_rate", "employer_rate", "threshold", "rate_multiplier", "standard_hours_per_day") if key in payload}
    record.update({"org_id": org_id, "active": True, "created_by": current_user["id"]})
    for rate_key in ("employee_rate", "employer_rate"):
        if float(record.get(rate_key, 0)) < 0 or float(record.get(rate_key, 0)) > 100:
            raise HTTPException(status_code=422, detail=f"{rate_key} must be between 0 and 100")
    return store.create_module_record("deduction_rules", record)


@router.post("/employee-deductions", status_code=status.HTTP_201_CREATED)
def assign_employee_deduction(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    user = store.get_user_by_id(payload.get("user_id", ""))
    if user is None or user.get("org_id") != org_id:
        raise HTTPException(status_code=422, detail="Employee must belong to this organization")
    name = str(payload.get("name", "")).strip()
    amount = float(payload.get("amount", 0))
    if not name or amount <= 0:
        raise HTTPException(status_code=422, detail="Deduction name and positive amount are required")
    return store.create_module_record("employee_deductions", {
        "org_id": org_id,
        "user_id": user["id"],
        "name": name,
        "amount": amount,
        "calculation": payload.get("calculation", "fixed"),
        "recurring": bool(payload.get("recurring", True)),
        "effective_date": payload.get("effective_date"),
        "active": True,
        "created_by": current_user["id"],
    })


@router.post("/runs", status_code=status.HTTP_201_CREATED)
def create_payroll_run(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    start, end = _period(payload)
    if start.day != 1 or end.day != calendar.monthrange(end.year, end.month)[1]:
        raise HTTPException(status_code=422, detail="Payroll preview must cover the full calendar month")
    if any(item.get("period_start") == start.isoformat() and item.get("period_end") == end.isoformat() for item in store.list_module_records("payroll_runs", org_id)):
        raise HTTPException(status_code=409, detail="A payroll run already exists for this period")
    structures = [item for item in store.list_module_records("employee_salary_structures", org_id) if item.get("effective_from", "") <= end.isoformat() and (not item.get("effective_to") or item["effective_to"] >= start.isoformat())]
    if not structures:
        raise HTTPException(status_code=409, detail="No active employee salary structures are configured")
    run = store.create_module_record("payroll_runs", {
        "org_id": org_id,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "status": "preview",
        "created_by": current_user["id"],
        "employee_count": len(structures),
        "total_gross": 0,
        "total_deductions": 0,
        "total_net": 0,
    })
    payslips = []
    for structure in structures:
        calculation = _calculate_payslip(org_id, structure["user_id"], structure, start, end)
        payslip = store.create_module_record("payslips", {
            "org_id": org_id,
            "payroll_run_id": run["id"],
            "user_id": structure["user_id"],
            "employee_id": structure["employee_id"],
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            **calculation,
            "status": "draft",
        })
        payslips.append(payslip)
        for label, contribution in calculation["contributions"].items():
            collection = {"PF": "pf_contribution_records", "ESI": "esi_contribution_records", "Tax/TDS": "tds_calculations"}[label]
            store.create_module_record(collection, {
                "org_id": org_id,
                "payroll_run_id": run["id"],
                "payslip_id": payslip["id"],
                "user_id": structure["user_id"],
                "employee_contribution": contribution["employee"],
                "employer_contribution": contribution["employer"],
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
            })
        for deduction_name, amount in calculation["deductions"].items():
            store.create_module_record("deduction_audit_logs", {
                "org_id": org_id,
                "payslip_id": payslip["id"],
                "user_id": structure["user_id"],
                "name": deduction_name,
                "amount": amount,
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
            })
    run = store.update_module_record("payroll_runs", run["id"], org_id, {
        "payslip_ids": [item["id"] for item in payslips],
        "total_gross": round(sum(item["gross_pay"] for item in payslips), 2),
        "total_deductions": round(sum(item["total_deductions"] for item in payslips), 2),
        "total_net": round(sum(item["net_pay"] for item in payslips), 2),
    })
    store.add_audit_log(current_user["id"], org_id, "payroll.run.previewed", {"record_id": run["id"], "payslip_count": len(payslips)})
    run["payslips"] = payslips
    return run


@router.get("/runs")
def list_payroll_runs(current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> List[Dict[str, Any]]:
    return store.list_module_records("payroll_runs", _org_id(current_user))


@router.patch("/runs/{run_id}/approve")
def approve_payroll_run(run_id: str, current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    run = store.get_module_record("payroll_runs", run_id, org_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    if run["status"] != "preview":
        raise HTTPException(status_code=409, detail="Only preview payroll runs can be approved")
    updated = store.update_module_record("payroll_runs", run_id, org_id, {"status": "approved", "approved_by": current_user["id"], "approved_at": datetime.now(timezone.utc).isoformat()})
    store.add_audit_log(current_user["id"], org_id, "payroll.run.approved", {"record_id": run_id})
    return updated


@router.patch("/runs/{run_id}/finalize")
def finalize_payroll_run(run_id: str, current_user: Dict[str, Any] = Depends(require_roles("admin"))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    run = store.get_module_record("payroll_runs", run_id, org_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    if run["status"] != "approved":
        raise HTTPException(status_code=409, detail="Payroll must be approved before finalization")
    timestamp = datetime.now(timezone.utc).isoformat()
    for payslip_id in run.get("payslip_ids", []):
        payslip = store.update_module_record("payslips", payslip_id, org_id, {"status": "available", "published_at": timestamp})
        if payslip:
            store.create_module_record("notification_logs", {
                "org_id": org_id,
                "user_id": payslip["user_id"],
                "event": "payroll.payslip.available",
                "title": "Payslip available",
                "message": f"Your payslip for {run['period_start'][:7]} is ready.",
                "entity_type": "payslip",
                "entity_id": payslip_id,
                "read_at": None,
            })
    updated = store.update_module_record("payroll_runs", run_id, org_id, {"status": "finalized", "finalized_by": current_user["id"], "finalized_at": timestamp})
    store.add_audit_log(current_user["id"], org_id, "payroll.run.finalized", {"record_id": run_id})
    return updated


@router.get("/payslips")
def list_payslips(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    items = store.list_module_records("payslips", _org_id(current_user))
    if current_user.get("role") not in HR_ROLES:
        items = [item for item in items if item.get("user_id") == current_user["id"] and item.get("status") == "available"]
    return items


@router.get("/payslips/{payslip_id}/download")
def download_payslip(payslip_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Response:
    org_id = _org_id(current_user)
    payslip = store.get_module_record("payslips", payslip_id, org_id)
    if payslip is None or (payslip.get("user_id") != current_user["id"] and current_user.get("role") not in HR_ROLES):
        raise HTTPException(status_code=404, detail="Payslip not found")
    if payslip.get("status") != "available" and current_user.get("role") not in HR_ROLES:
        raise HTTPException(status_code=404, detail="Payslip not found")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Description", "Amount"])
    writer.writerow(["Gross pay", payslip["gross_pay"]])
    for name, amount in payslip["earnings"].items():
        writer.writerow([name, amount])
    for name, amount in payslip["deductions"].items():
        writer.writerow([name, -amount])
    writer.writerow(["Reimbursements", payslip["reimbursements"]])
    writer.writerow(["Net pay", payslip["net_pay"]])
    return Response(buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=payslip-{payslip['period_start'][:7]}.csv"})


@router.get("/summary")
def payroll_summary(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    payslips = [item for item in list_payslips(current_user) if item.get("status") == "available"]
    payslips.sort(key=lambda item: item.get("period_end", ""), reverse=True)
    if payslips:
        latest = payslips[0]
        return {
            "employee_id": latest["employee_id"],
            "org_id": latest["org_id"],
            "base_salary": latest["earnings"].get("Base salary", 0),
            "deductions": latest["total_deductions"],
            "net_salary": latest["net_pay"],
            "status": "available",
            "period": latest["period_start"][:7],
        }
    return {"employee_id": current_user["id"], "org_id": current_user.get("org_id"), "base_salary": 0, "deductions": 0, "net_salary": 0, "status": "no_payslip"}
