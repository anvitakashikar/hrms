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
        self.module_records: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def create_organization(self, org_name: str, org_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        org_name = org_name or (org_data or {}).get("name")
        if not org_name:
            raise ValueError("Organization name is required")
        for org in self.organizations.values():
            if org.get("name", "").lower() == org_name.lower():
                return copy.deepcopy(org)
        data = org_data or {}
        org_id = str(uuid.uuid4())
        entity = {
            "id": org_id,
            "name": org_name,
            "legal_name": data.get("legal_name") or org_name,
            "email": data.get("email"),
            "phone": data.get("phone"),
            "website": data.get("website"),
            "industry": data.get("industry"),
            "company_type": data.get("company_type"),
            "timezone": data.get("timezone") or "UTC",
            "currency": data.get("currency") or "USD",
            "address": data.get("address"),
            "city": data.get("city"),
            "state": data.get("state"),
            "country": data.get("country"),
            "postal_code": data.get("postal_code"),
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
            "org_id": user_data.get("org_id"),
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

    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        user = self.users.get(user_id)
        if user is None:
            raise KeyError(f"User {user_id} not found")
        user.update(updates)
        return copy.deepcopy(user)

    def get_organization_by_id(self, org_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not org_id:
            return None
        org = self.organizations.get(org_id)
        return copy.deepcopy(org) if org else None

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

    def create_module_record(self, module: str, data: Dict[str, Any]) -> Dict[str, Any]:
        records = self.module_records.setdefault(module, {})
        item = copy.deepcopy(data)
        item.setdefault("id", str(uuid.uuid4()))
        item.setdefault("created_at", datetime.utcnow().isoformat())
        records[item["id"]] = item
        return copy.deepcopy(item)

    def list_module_records(self, module: str, org_id: str) -> List[Dict[str, Any]]:
        records = self.module_records.get(module, {})
        return [copy.deepcopy(item) for item in records.values() if item.get("org_id") == org_id]

    def get_module_record(self, module: str, record_id: str, org_id: str) -> Optional[Dict[str, Any]]:
        item = self.module_records.get(module, {}).get(record_id)
        if item is None or item.get("org_id") != org_id:
            return None
        return copy.deepcopy(item)

    def update_module_record(self, module: str, record_id: str, org_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        records = self.module_records.get(module, {})
        item = records.get(record_id)
        if item is None or item.get("org_id") != org_id:
            return None
        item.update(copy.deepcopy(updates))
        item["updated_at"] = datetime.utcnow().isoformat()
        return copy.deepcopy(item)

    def delete_module_record(self, module: str, record_id: str, org_id: str) -> bool:
        records = self.module_records.get(module, {})
        item = records.get(record_id)
        if item is None or item.get("org_id") != org_id:
            return False
        del records[record_id]
        return True
