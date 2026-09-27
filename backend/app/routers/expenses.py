import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.notification_service import notify_reviewers, notify_user
from app.services.document_extraction import extract_text
from app.services.policy_service import get_policy_value

router = APIRouter()
store = get_store()
REVIEW_ROLES = ("admin", "hr", "manager")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


@router.post("/receipt-ocr")
async def extract_receipt_fields(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    form = await request.form()
    file = form.get("file")
    if not file or not getattr(file, "filename", None):
        raise HTTPException(status_code=422, detail="Receipt file is required")
    content = await file.read(10 * 1024 * 1024 + 1)
    if not content or len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Receipt must be non-empty and 10 MB or smaller")
    text = extract_text(content, Path(file.filename).name, file.content_type or "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    date_match = re.search(r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]20\d{2})\b", text)
    amount_matches = re.findall(r"(?:USD|INR|EUR|GBP|\$|₹|€|£)?\s*(\d{1,7}(?:[,.]\d{2})?)", text, flags=re.IGNORECASE)
    tax_match = re.search(r"(?:tax|vat|gst)\s*[:\-]?\s*(?:USD|INR|EUR|GBP|\$|₹|€|£)?\s*(\d+(?:[,.]\d{2})?)", text, flags=re.IGNORECASE)
    currency = "USD"
    for symbol, code in (("₹", "INR"), ("€", "EUR"), ("£", "GBP"), ("$", "USD")):
        if symbol in text:
            currency = code
            break
    for code in ("INR", "USD", "EUR", "GBP"):
        if re.search(r"\b" + code + r"\b", text, flags=re.IGNORECASE):
            currency = code
            break
    amount = None
    if amount_matches:
        try:
            amount = float(amount_matches[-1].replace(",", ""))
        except ValueError:
            amount = None
    category = "Travel" if any(term in text.casefold() for term in ("taxi", "uber", "fuel", "flight", "hotel")) else ("Meals" if any(term in text.casefold() for term in ("restaurant", "cafe", "meal", "food")) else "Other")
    result = {
        "merchant_suggestion": lines[0][:120] if lines else None,
        "date_suggestion": date_match.group(1) if date_match else None,
        "amount_suggestion": amount,
        "tax_suggestion": float(tax_match.group(1).replace(",", "")) if tax_match else None,
        "currency_suggestion": currency,
        "category_suggestion": category,
        "extracted_text": text[:8000],
        "requires_employee_review": True,
    }
    store.create_module_record("expense_receipt_extraction_logs", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "file_name": Path(file.filename).name,
        "fields": result,
        "confirmed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return result


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
