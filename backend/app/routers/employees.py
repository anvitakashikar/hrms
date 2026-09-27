from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import get_current_user, require_roles
from app.services.employee_service import EmployeeService

router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
def list_employees(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    employees = EmployeeService().list_employees(current_user["org_id"])
    start = (page - 1) * page_size
    end = start + page_size
    return {"items": employees[start:end], "page": page, "page_size": page_size, "total": len(employees)}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: dict,
    current_user: dict = Depends(require_roles("admin", "hr")),
):
    employee = EmployeeService().create_employee(current_user["org_id"], payload)
    return employee


@router.get("/{employee_id}")
def get_employee(employee_id: str, current_user: dict = Depends(get_current_user)):
    employee = EmployeeService().get_employee(current_user["org_id"], employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee
