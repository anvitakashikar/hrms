from typing import Any, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.dependencies.auth import get_current_user


router = APIRouter(
    tags=["Profile"],
)


class ProfileUpdate(BaseModel):
    employee_id: Optional[str] = None
    first_name: Optional[str]= None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    joining_date: Optional[str] = None
    address: Optional[str] = None

def serialize_profile(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(user.get("_id")) if user.get("_id") else None,
        "employee_id": user.get("employee_id"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "role": user.get("role"),
        "department": user.get("department"),
        "designation": user.get("designation"),
        "joining_date": user.get("joining_date"),
        "address": user.get("address"),
    }


@router.get("")
async def get_profile(
    current_user: dict = Depends(get_current_user),
):
    db = get_db()

    user_id = current_user.get("_id")

    user = await db.users.find_one({"_id": user_id})

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User profile not found.",
        )

    return serialize_profile(user)


@router.patch("")
async def update_profile(
    payload: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()

    user_id = current_user.get("_id")

    user = await db.users.find_one({"_id": user_id})

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User profile not found.",
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    await db.users.update_one(
        {"_id": user_id},
        {"$set": update_data},
    )

    updated_user = await db.users.find_one(
        {"_id": user_id}
    )

    return serialize_profile(updated_user)