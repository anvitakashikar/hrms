from datetime import date, datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.policy_service import get_applicable_policies as resolve_applicable_policies

router = APIRouter()
store = get_store()
HR_ROLES = ("admin", "hr")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


@router.post("")
def create_policy(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    process = str(payload.get("process", "")).strip().lower()
    if not name or not process:
        raise HTTPException(status_code=422, detail="Policy name and process are required")
    org_id = _org_id(current_user)
    policy = store.create_module_record("policies", {
        "org_id": org_id,
        "name": name,
        "description": str(payload.get("description", "")).strip(),
        "process": process,
        "department": payload.get("department"),
        "location": payload.get("location"),
        "employee_user_id": payload.get("employee_user_id"),
        "effective_from": payload.get("effective_from", date.today().isoformat()),
        "effective_to": payload.get("effective_to"),
        "active": bool(payload.get("active", True)),
        "version": 1,
        "created_by": current_user["id"],
    })
    store.add_audit_log(current_user["id"], org_id, "policy.created", {"record_id": policy["id"], "process": process})
    return policy


@router.get("")
def list_policies(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    policies = store.list_module_records("policies", current_user["org_id"])
    if current_user.get("role") in HR_ROLES:
        rules = store.list_module_records("policy_rules", current_user["org_id"])
        return [{**policy, "rules": [rule for rule in rules if rule.get("policy_id") == policy["id"] and rule.get("active")]} for policy in policies]
    return resolve_applicable_policies(current_user)


@router.patch("/{policy_id}")
def update_policy(
    policy_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    current = store.get_module_record("policies", policy_id, org_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    allowed = {key: payload[key] for key in (
        "name", "description", "process", "department", "location", "employee_user_id", "effective_from", "effective_to", "active"
    ) if key in payload}
    if not allowed:
        raise HTTPException(status_code=422, detail="No policy fields were provided")
    store.create_module_record("policy_versions", {
        "org_id": org_id,
        "policy_id": policy_id,
        "version": current.get("version", 1),
        "snapshot": current,
        "changed_by": current_user["id"],
        "changed_at": datetime.now(timezone.utc).isoformat(),
    })
    allowed["version"] = current.get("version", 1) + 1
    policy = store.update_module_record("policies", policy_id, org_id, allowed)
    store.add_audit_log(current_user["id"], org_id, "policy.updated", {"record_id": policy_id, "changes": allowed})
    return policy


@router.get("/{policy_id}/versions")
def list_policy_versions(policy_id: str, current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    if store.get_module_record("policies", policy_id, org_id) is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return [item for item in store.list_module_records("policy_versions", org_id) if item.get("policy_id") == policy_id]


@router.post("/{policy_id}/rules")
def create_policy_rule(
    policy_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    if store.get_module_record("policies", policy_id, org_id) is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    key = str(payload.get("key", "")).strip()
    if not key or "value" not in payload:
        raise HTTPException(status_code=422, detail="Rule key and value are required")
    rule = store.create_module_record("policy_rules", {
        "org_id": org_id,
        "policy_id": policy_id,
        "key": key,
        "operator": payload.get("operator", "equals"),
        "value": payload["value"],
        "active": bool(payload.get("active", True)),
    })
    store.add_audit_log(current_user["id"], org_id, "policy.rule.created", {"record_id": rule["id"], "policy_id": policy_id})
    return rule


@router.get("/{policy_id}/rules")
def list_policy_rules(policy_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    if store.get_module_record("policies", policy_id, org_id) is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return [item for item in store.list_module_records("policy_rules", org_id) if item.get("policy_id") == policy_id]


@router.post("/assignments")
def assign_policy(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    policy_id = payload.get("policy_id")
    if not policy_id or store.get_module_record("policies", policy_id, org_id) is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    user_id = payload.get("user_id")
    if user_id:
        user = store.get_user_by_id(user_id)
        if user is None or user.get("org_id") != org_id:
            raise HTTPException(status_code=422, detail="Assigned employee must belong to this organization")
    if not any((user_id, payload.get("department"), payload.get("location"))):
        raise HTTPException(status_code=422, detail="Assignment requires an employee, department, or location")
    assignment = store.create_module_record("policy_assignments", {
        "org_id": org_id,
        "policy_id": policy_id,
        "user_id": user_id,
        "department": payload.get("department"),
        "location": payload.get("location"),
        "active": True,
        "assigned_by": current_user["id"],
    })
    store.add_audit_log(current_user["id"], org_id, "policy.assigned", {"record_id": assignment["id"], "policy_id": policy_id})
    return assignment


def applicable_policies(current_user: Dict[str, Any]) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    today = date.today().isoformat()
    employee = store.get_employee_by_user_email(org_id, current_user["email"])
    department = employee.get("department") if employee else None
    location = employee.get("location") if employee else None
    assignments = store.list_module_records("policy_assignments", org_id)
    assigned_ids = {
        item["policy_id"] for item in assignments
        if item.get("active") and (
            item.get("user_id") == current_user["id"]
            or (item.get("department") and item["department"] == department)
            or (item.get("location") and item["location"] == location)
        )
    }
    result = []
    for policy in store.list_module_records("policies", org_id):
        if not policy.get("active") or policy.get("effective_from", "0000") > today or (policy.get("effective_to") and policy["effective_to"] < today):
            continue
        direct_match = policy.get("employee_user_id") == current_user["id"]
        scope_match = not policy.get("employee_user_id") and (not policy.get("department") or policy["department"] == department) and (not policy.get("location") or policy["location"] == location)
        if policy["id"] in assigned_ids or direct_match or scope_match:
            policy["rules"] = [rule for rule in store.list_module_records("policy_rules", org_id) if rule.get("policy_id") == policy["id"] and rule.get("active")]
            result.append(policy)
    return result


@router.get("/applicable")
def get_applicable_policies(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return resolve_applicable_policies(current_user)