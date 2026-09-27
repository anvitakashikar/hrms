from datetime import date, datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.notification_service import notify_reviewers, notify_user
from app.services.policy_service import get_policy_value

router = APIRouter()
store = get_store()
REVIEW_ROLES = ("admin", "hr", "manager")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


@router.post("/claims", status_code=status.HTTP_201_CREATED)
def create_expense_claim(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    try:
        amount = float(payload["amount"])
        expense_date = date.fromisoformat(payload["expense_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Amount and expense_date are required") from exc
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Expense amount must be greater than zero")
    maximum_amount = get_policy_value(current_user, "expense", "maximum_claim_amount")
    if maximum_amount is not None and amount > float(maximum_amount):
        raise HTTPException(status_code=422, detail="Expense amount exceeds the configured policy limit")
    category = str(payload.get("category", "")).strip()
    description = str(payload.get("description", "")).strip()
    currency = str(payload.get("currency", "")).strip().upper()
    if not category or not description or len(currency) != 3:
        raise HTTPException(status_code=422, detail="Category, description, and three-letter currency are required")
    item = store.create_module_record("expense_claims", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "category": category,
        "amount": amount,
        "currency": currency,
        "description": description,
        "expense_date": expense_date.isoformat(),
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    notify_reviewers(org_id, "expense.submitted", "Expense claim submitted", f"{current_user['first_name']} submitted a {currency} {amount:.2f} expense.", "expense_claim", item["id"])
    store.add_audit_log(current_user["id"], org_id, "expense.claim.submitted", {"record_id": item["id"], "amount": amount, "currency": currency})
    return item


@router.get("/claims")
def list_expense_claims(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    items = store.list_module_records("expense_claims", current_user["org_id"])
    if current_user.get("role") not in REVIEW_ROLES:
        items = [item for item in items if item.get("user_id") == current_user["id"]]
    return items


@router.patch("/claims/{claim_id}/decision")
def decide_expense_claim(
    claim_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*REVIEW_ROLES)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    decision = payload.get("status")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Status must be approved or rejected")
    comment = str(payload.get("comment", "")).strip()
    if decision == "rejected" and not comment:
        raise HTTPException(status_code=422, detail="A rejection reason is required")
    claim = store.get_module_record("expense_claims", claim_id, org_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Expense claim not found")
    if claim["status"] != "submitted":
        raise HTTPException(status_code=409, detail="Only submitted claims can be reviewed")
    updated = store.update_module_record("expense_claims", claim_id, org_id, {
        "status": decision,
        "reviewed_by": current_user["id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_comment": comment,
    })
    notify_user(org_id, claim["user_id"], f"expense.{decision}", f"Expense claim {decision}", f"Your {claim['category']} expense claim was {decision}.", "expense_claim", claim_id)
    store.add_audit_log(current_user["id"], org_id, f"expense.claim.{decision}", {"record_id": claim_id, "comment": comment})
    return updated
