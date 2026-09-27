from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.database import get_store


class EmployeeService:
    def __init__(self) -> None:
        self.store = get_store()

    def list_employees(self, org_id: str) -> List[Dict[str, Any]]:
        return self.store.list_employees(org_id)

    def create_employee(self, org_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = {"org_id": org_id, **payload}
        return self.store.create_employee(data)

    def get_employee(self, org_id: str, employee_id: str) -> Optional[Dict[str, Any]]:
        for employee in self.store.list_employees(org_id):
            if employee["id"] == employee_id:
                return employee
        return None
