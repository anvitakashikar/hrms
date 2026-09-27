from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.schemas.auth import LoginRequest, LoginResponse, SignupRequest, UserOut
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/signup", response_model=dict, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest) -> dict:
    service = AuthService()
    return service.signup(payload.model_dump())


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> dict:
    service = AuthService()
    return service.login(payload.email, payload.password)


@router.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(get_current_user)) -> dict:
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "first_name": current_user["first_name"],
        "last_name": current_user["last_name"],
        "role": current_user["role"],
        "org_id": current_user["org_id"],
        "is_active": current_user.get("is_active", True),
    }
