from typing import Any, Dict, List, Set

from app.database import get_store


def get_applicable_holidays(user: Dict[str, Any]) -> List[Dict[str, Any]]:
    org_id = user.get("org_id")
    if not org_id:
        return []
    store = get_store()
    employee = store.get_employee_by_user_email(org_id, user["email"])
    department = employee.get("department") if employee else None
    location = employee.get("location") if employee else None
    mappings = store.list_module_records("employee_holiday_calendar_mappings", org_id)
    calendar_ids: Set[str] = {
        item["calendar_id"] for item in mappings if item.get("active") and (
            item.get("user_id") == user["id"]
            or (item.get("department") and item["department"] == department)
            or (item.get("location") and item["location"] == location)
        )
    }
    calendars = store.list_module_records("holiday_calendars", org_id)
    if not calendar_ids:
        calendar_ids = {
            item["id"] for item in calendars if item.get("active")
            and (not item.get("department") or item["department"] == department)
            and (not item.get("location") or item["location"] == location)
        }
    holidays = [
        item for item in store.list_module_records("holidays", org_id)
        if item.get("calendar_id") in calendar_ids
        and (not item.get("department") or item["department"] == department)
        and (not item.get("location") or item["location"] == location)
    ]
    return sorted(holidays, key=lambda item: item["date"])


def get_applicable_holiday_dates(user: Dict[str, Any]) -> Set[str]:
    return {item["date"] for item in get_applicable_holidays(user)}
