from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user

router = APIRouter()


@router.get("/summary")
def payroll_summary(current_user: dict = Depends(get_current_user)) -> dict:
    return {
        "employee_id": current_user["id"],
        "org_id": current_user["org_id"],
        "base_salary": 60000,
        "deductions": 5000,
        "net_salary": 55000,
        "status": "computed",
    }
