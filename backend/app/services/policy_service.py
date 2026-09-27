from datetime import date
from typing import Any, Dict, List, Optional

from app.database import get_store


def get_applicable_policies(user: Dict[str, Any]) -> List[Dict[str, Any]]:
    org_id = user.get("org_id")
    if not org_id:
        return []
    store = get_store()
    employee = store.get_employee_by_user_email(org_id, user["email"])
    department = employee.get("department") if employee else None
    location = employee.get("location") if employee else None
    assignments = store.list_module_records("policy_assignments", org_id)
    assigned_ids = {
        item["policy_id"] for item in assignments if item.get("active") and (
            item.get("user_id") == user["id"]
            or (item.get("department") and item["department"] == department)
            or (item.get("location") and item["location"] == location)
        )
    }
    today = date.today().isoformat()
    rules = store.list_module_records("policy_rules", org_id)
    result = []
    for policy in store.list_module_records("policies", org_id):
        if not policy.get("active") or policy.get("effective_from", "0000") > today or (policy.get("effective_to") and policy["effective_to"] < today):
            continue
        direct_match = policy.get("employee_user_id") == user["id"]
        scope_match = not policy.get("employee_user_id") and (not policy.get("department") or policy["department"] == department) and (not policy.get("location") or policy["location"] == location)
        if policy["id"] in assigned_ids or direct_match or scope_match:
            policy["rules"] = [rule for rule in rules if rule.get("policy_id") == policy["id"] and rule.get("active")]
            policy["priority"] = 3 if direct_match else (2 if policy.get("department") else (1 if policy.get("location") else 0))
            result.append(policy)
    return sorted(result, key=lambda item: item["priority"], reverse=True)


def get_policy_value(user: Dict[str, Any], process: str, key: str, default: Optional[Any] = None) -> Optional[Any]:
    for policy in get_applicable_policies(user):
        if policy.get("process") != process:
            continue
        for rule in policy.get("rules", []):
            if rule.get("key") == key:
                return rule.get("value")
    return default
