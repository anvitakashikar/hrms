from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException, status

from app.database import get_store
from app.utils.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self) -> None:
        self.store = get_store()

    def _build_onboarding_state(self, user: Dict[str, Any]) -> Dict[str, Any]:
        organization_configured = bool(self.store.get_organization_by_id(user.get("org_id")))
        onboarding = {
            "role": user.get("role", "employee"),
            "organization_configured": organization_configured,
            "employee_exists": False,
            "employee_onboarding_required": False,
            "onboarding_required": False,
            "onboarding_completed": False,
            "current_step": None,
            "next_step": "dashboard",
        }

        if user.get("role") == "admin":
            if not organization_configured:
                onboarding["onboarding_required"] = True
                onboarding["current_step"] = "organization_setup"
                onboarding["next_step"] = "organization_setup"
                return onboarding
            onboarding["onboarding_completed"] = True
            onboarding["current_step"] = "dashboard"
            onboarding["next_step"] = "dashboard"
            return onboarding

        if not user.get("org_id"):
            onboarding["onboarding_required"] = True
            onboarding["current_step"] = "organization_setup"
            onboarding["next_step"] = "organization_setup"
            return onboarding

        employee = self.store.get_employee_by_user_email(user["org_id"], user["email"])
        onboarding["employee_exists"] = bool(employee)
        if not employee:
            onboarding["onboarding_required"] = True
            onboarding["employee_onboarding_required"] = True
            onboarding["current_step"] = "personal_information"
            onboarding["next_step"] = "onboarding"
            return onboarding

        onboarding["onboarding_completed"] = True
        onboarding["current_step"] = "dashboard"
        onboarding["next_step"] = "dashboard"
        return onboarding

    def signup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.store.get_user_by_email(payload["email"])
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

        org_id = None
        org = None
        if payload.get("org_name"):
            org = self.store.create_organization(payload["org_name"])
            org_id = org["id"]

        hashed = hash_password(payload["password"])
        user = self.store.create_user(
            {
                "email": payload["email"],
                "password_hash": hashed,
                "first_name": payload["first_name"],
                "last_name": payload["last_name"],
                "role": payload.get("role", "employee"),
                "org_id": org_id,
            }
        )

        if org_id and not self.store.get_employee_by_user_email(org_id, payload["email"]):
            self.store.create_employee(
                {
                    "org_id": org_id,
                    "first_name": payload["first_name"],
                    "last_name": payload["last_name"],
                    "email": payload["email"],
                    "department": "General",
                    "designation": payload.get("role", "employee").title(),
                    "status": "active",
                }
            )

        if org:
            return {
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "first_name": user["first_name"],
                    "last_name": user["last_name"],
                    "role": user["role"],
                    "org_id": user["org_id"],
                    "is_active": user["is_active"],
                },
                "organization": {"id": org["id"], "name": org["name"]},
            }

        return {
            "user": {
                "id": user["id"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "role": user["role"],
                "org_id": user["org_id"],
                "is_active": user["is_active"],
            }
        }

    def register_organization(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        user = self.store.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.get("role") != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can register an organization")
        if user.get("org_id"):
            org = self.store.get_organization_by_id(user["org_id"])
            if org:
                return org

        organization = self.store.create_organization(payload["name"], payload)
        self.store.update_user(user_id, {"org_id": organization["id"]})
        return organization

    def login(self, email: str, password: str) -> Dict[str, Any]:
        user = self.store.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not user.get("is_active"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")
        token = create_access_token(user["id"], extra={"role": user["role"], "org_id": user.get("org_id")})
        self.store.add_audit_log(user["id"], user.get("org_id"), "login")
        onboarding = self._build_onboarding_state(user)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "role": user["role"],
                "org_id": user["org_id"],
            },
            "next_step": onboarding["next_step"],
            "onboarding": onboarding,
        }
