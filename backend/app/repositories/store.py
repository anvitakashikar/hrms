from __future__ import annotations

import copy
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class InMemoryStore:
    def __init__(self) -> None:
        self.organizations: Dict[str, Dict[str, Any]] = {}
        self.users: Dict[str, Dict[str, Any]] = {}
        self.employees: Dict[str, Dict[str, Any]] = {}
        self.leave_applications: Dict[str, Dict[str, Any]] = {}
        self.expense_claims: Dict[str, Dict[str, Any]] = {}
        self.attendance_records: Dict[str, Dict[str, Any]] = {}
        self.audit_logs: List[Dict[str, Any]] = []

    def create_organization(self, org_name: str) -> Dict[str, Any]:
        for org in self.organizations.values():
            if org.get("name", "").lower() == org_name.lower():
                return copy.deepcopy(org)
        org_id = str(uuid.uuid4())
        entity = {
            "id": org_id,
            "name": org_name,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True,
        }
        self.organizations[org_id] = entity
        return copy.deepcopy(entity)

    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        user_id = str(uuid.uuid4())
        entity = {
            "id": user_id,
            "email": user_data["email"].lower(),
            "password_hash": user_data["password_hash"],
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "role": user_data["role"],
            "org_id": user_data["org_id"],
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.users[user_id] = entity
        return copy.deepcopy(entity)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        for user in self.users.values():
            if user["email"] == email.lower():
                return copy.deepcopy(user)
        return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        user = self.users.get(user_id)
        return copy.deepcopy(user) if user else None

    def list_employees(self, org_id: str) -> List[Dict[str, Any]]:
        items = [emp for emp in self.employees.values() if emp.get("org_id") == org_id]
        return [copy.deepcopy(item) for item in items]

    def create_employee(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        emp_id = str(uuid.uuid4())
        entity = {
            "id": emp_id,
            "employee_code": employee_data.get("employee_code") or f"EMP-{len(self.employees) + 1:04d}",
            "org_id": employee_data["org_id"],
            "first_name": employee_data.get("first_name", ""),
            "last_name": employee_data.get("last_name", ""),
            "email": employee_data.get("email", ""),
            "department": employee_data.get("department", "General"),
            "designation": employee_data.get("designation", "Employee"),
            "status": employee_data.get("status", "active"),
            "base_salary": employee_data.get("base_salary", 60000),
            "created_at": datetime.utcnow().isoformat(),
        }
        self.employees[emp_id] = entity
        return copy.deepcopy(entity)

    def get_employee_by_user_email(self, org_id: str, email: str) -> Optional[Dict[str, Any]]:
        for employee in self.employees.values():
            if employee.get("org_id") == org_id and employee.get("email") == email.lower():
                return copy.deepcopy(employee)
        return None

    def create_leave_application(self, data: Dict[str, Any]) -> Dict[str, Any]:
        app_id = str(uuid.uuid4())
        entity = {
            "id": app_id,
            "user_id": data["user_id"],
            "org_id": data["org_id"],
            "leave_type": data["leave_type"],
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "reason": data["reason"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }
        self.leave_applications[app_id] = entity
        return copy.deepcopy(entity)

    def get_leave_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        item = self.leave_applications.get(application_id)
        return copy.deepcopy(item) if item else None

    def update_leave_application(self, application_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        app = self.leave_applications[application_id]
        app.update(updates)
        return copy.deepcopy(app)

    def list_leave_applications(self, org_id: str) -> List[Dict[str, Any]]:
        return [copy.deepcopy(item) for item in self.leave_applications.values() if item.get("org_id") == org_id]

    def create_expense_claim(self, data: Dict[str, Any]) -> Dict[str, Any]:
        claim_id = str(uuid.uuid4())
        entity = {
            "id": claim_id,
            "user_id": data["user_id"],
            "org_id": data["org_id"],
            "category": data["category"],
            "amount": data["amount"],
            "currency": data["currency"],
            "description": data["description"],
            "expense_date": data["expense_date"],
            "status": "submitted",
            "created_at": datetime.utcnow().isoformat(),
        }
        self.expense_claims[claim_id] = entity
        return copy.deepcopy(entity)

    def list_expense_claims(self, org_id: str) -> List[Dict[str, Any]]:
        return [copy.deepcopy(item) for item in self.expense_claims.values() if item.get("org_id") == org_id]

    def add_audit_log(self, user_id: str, org_id: str, event: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        item = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "org_id": org_id,
            "event": event,
            "payload": payload or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        self.audit_logs.append(item)
        return copy.deepcopy(item)
