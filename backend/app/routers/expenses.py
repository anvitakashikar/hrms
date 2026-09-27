from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user

router = APIRouter()

expense_store = {}


@router.post("/claims", status_code=status.HTTP_201_CREATED)
def create_expense_claim(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    claim_id = f"expense-{len(expense_store) + 1}"
    item = {
        "id": claim_id,
        "user_id": current_user["id"],
        "org_id": current_user["org_id"],
        "category": payload["category"],
        "amount": payload["amount"],
        "currency": payload["currency"],
        "description": payload["description"],
        "expense_date": payload["expense_date"],
        "status": "submitted",
    }
    expense_store[claim_id] = item
    return item


@router.get("/claims")
def list_expense_claims(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return [item for item in expense_store.values() if item["org_id"] == current_user["org_id"]]
