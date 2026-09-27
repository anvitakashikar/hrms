from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user
from app.schemas.auth import OrganizationRegisterRequest
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_organization(
    payload: OrganizationRegisterRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    service = AuthService()
    return service.register_organization(current_user["id"], payload.model_dump())