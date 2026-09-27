from typing import Any, Dict, Set

from app.database import get_store


def get_team_user_ids(manager: Dict[str, Any]) -> Set[str]:
    org_id = manager.get("org_id")
    if not org_id:
        return {manager["id"]}
    store = get_store()
    manager_employee = store.get_employee_by_user_email(org_id, manager["email"])
    department = manager_employee.get("department") if manager_employee else None
    if not department:
        return {manager["id"]}
    team_emails = {
        item["email"] for item in store.list_employees(org_id)
        if item.get("department") == department
    }
    team_ids = {
        user["id"] for user in store.users.values()
        if user.get("org_id") == org_id and user.get("email") in team_emails
    }
    team_ids.add(manager["id"])
    return team_ids
