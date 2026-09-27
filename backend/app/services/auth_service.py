from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException, status

from app.database import get_store
from app.utils.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self) -> None:
        self.store = get_store()

    def signup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.store.get_user_by_email(payload["email"])
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

        org = self.store.create_organization(payload["org_name"])
        hashed = hash_password(payload["password"])
        user = self.store.create_user(
            {
                "email": payload["email"],
                "password_hash": hashed,
                "first_name": payload["first_name"],
                "last_name": payload["last_name"],
                "role": payload.get("role", "employee"),
                "org_id": org["id"],
            }
        )

        if not self.store.get_employee_by_user_email(org["id"], payload["email"]):
            self.store.create_employee(
                {
                    "org_id": org["id"],
                    "first_name": payload["first_name"],
                    "last_name": payload["last_name"],
                    "email": payload["email"],
                    "department": "General",
                    "designation": payload.get("role", "employee").title(),
                    "status": "active",
                }
            )

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

    def login(self, email: str, password: str) -> Dict[str, Any]:
        user = self.store.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not user.get("is_active"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")
        token = create_access_token(user["id"], extra={"role": user["role"], "org_id": user["org_id"]})
        self.store.add_audit_log(user["id"], user["org_id"], "login")
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
        }
