from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str
    last_name: str
    role: str = "employee"
    org_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSession(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    org_id: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSession
    next_step: str
    onboarding: Dict[str, Any]


class OrganizationRegisterRequest(BaseModel):
    name: str
    legal_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_type: Optional[str] = None
    timezone: Optional[str] = "UTC"
    currency: Optional[str] = "USD"
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    org_id: Optional[str] = None
    is_active: bool = True
