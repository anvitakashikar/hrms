import csv
import io
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, Response

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.notification_service import notify_user

router = APIRouter()
store = get_store()
HR_ROLES = ("admin", "hr")
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "private_uploads"
MAX_PROOF_BYTES = 10 * 1024 * 1024


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _owner_items(collection: str, user: Dict[str, Any], owner_field: str = "user_id") -> List[Dict[str, Any]]:
    org_id = _org_id(user)
    items = store.list_module_records(collection, org_id)
    if user.get("role") not in HR_ROLES:
        return [item for item in items if item.get(owner_field) == user["id"]]
    store.add_audit_log(user["id"], org_id, "sensitive_data.organization_access", {"collection": collection, "count": len(items)})
    return items


def _record(collection: str, record_id: str, org_id: str, label: str) -> Dict[str, Any]:
    item = store.get_module_record(collection, record_id, org_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return item


def _without_private_path(item: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in item.items() if key != "storage_path"}


@router.post("/statutory/config", status_code=status.HTTP_201_CREATED)
def create_statutory_config(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    kind = payload.get("kind")
    if kind not in {"pf", "esi"}:
        raise HTTPException(status_code=422, detail="Contribution kind must be pf or esi")
    try:
        employee_rate = float(payload["employee_rate"])
        employer_rate = float(payload["employer_rate"])
        threshold = float(payload.get("threshold", 0))
        wage_cap = float(payload["wage_cap"]) if payload.get("wage_cap") is not None else None
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Contribution rates must be numeric") from exc
    if not all(0 <= rate <= 100 for rate in (employee_rate, employer_rate)) or threshold < 0 or (wage_cap is not None and wage_cap <= 0):
        raise HTTPException(status_code=422, detail="Rates must be 0-100 and thresholds/caps must be positive")
    config = store.create_module_record("statutory_contribution_configs", {
        "org_id": org_id,
        "kind": kind,
        "name": str(payload.get("name", kind.upper())).strip(),
        "employee_rate": employee_rate,
        "employer_rate": employer_rate,
        "threshold": threshold,
        "wage_cap": wage_cap,
        "effective_from": payload.get("effective_from", date.today().isoformat()),
        "active": True,
        "created_by": current_user["id"],
    })
    store.create_module_record("deduction_rules", {
        "org_id": org_id,
        "name": config["name"],
        "kind": kind,
        "employee_rate": employee_rate,
        "employer_rate": employer_rate,
        "threshold": threshold,
        "wage_cap": wage_cap,
        "employee_eligibility_required": True,
        "active": True,
        "config_id": config["id"],
        "created_by": current_user["id"],
    })
    store.add_audit_log(current_user["id"], org_id, f"statutory.{kind}.config_created", {"record_id": config["id"]})
    return config


@router.get("/statutory/config")
def list_statutory_configs(current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> List[Dict[str, Any]]:
    return store.list_module_records("statutory_contribution_configs", _org_id(current_user))


@router.get("/statutory/me")
def get_my_statutory_info(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    info = next((item for item in store.list_module_records("employee_statutory_info", org_id) if item.get("user_id") == current_user["id"]), None)
    return info or {"user_id": current_user["id"], "pf_eligible": False, "esi_eligible": False}


@router.put("/statutory/me")
def update_my_statutory_info(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    safe_fields = ("pf_member_id", "esi_number", "pan", "pf_eligible", "esi_eligible", "declaration")
    updates = {key: payload[key] for key in safe_fields if key in payload}
    existing = next((item for item in store.list_module_records("employee_statutory_info", org_id) if item.get("user_id") == current_user["id"]), None)
    if existing:
        result = store.update_module_record("employee_statutory_info", existing["id"], org_id, updates)
    else:
        result = store.create_module_record("employee_statutory_info", {"org_id": org_id, "user_id": current_user["id"], **updates})
    store.add_audit_log(current_user["id"], org_id, "statutory.employee_info.updated", {"fields": sorted(updates.keys())})
    return result


@router.get("/statutory/employees")
def list_employee_statutory_info(current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> List[Dict[str, Any]]:
    return _owner_items("employee_statutory_info", current_user)


@router.post("/tax/declarations", status_code=status.HTTP_201_CREATED)
def submit_tax_declaration(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    try:
        tax_year = int(payload["tax_year"])
        declared_amount = float(payload.get("declared_investment_amount", 0))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="tax_year and a valid declared amount are required") from exc
    if not 2000 <= tax_year <= 2100 or declared_amount < 0:
        raise HTTPException(status_code=422, detail="Tax year or declaration amount is invalid")
    declaration = store.create_module_record("tax_declarations", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "tax_year": tax_year,
        "tax_regime": payload.get("tax_regime", "default"),
        "declared_investment_amount": declared_amount,
        "declaration": payload.get("declaration", {}),
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    for user in store.users.values():
        if user.get("org_id") == org_id and user.get("role") in HR_ROLES:
            notify_user(org_id, user["id"], "tax.declaration.submitted", "Tax declaration submitted", f"A tax declaration for {tax_year} is ready for review.", "tax_declaration", declaration["id"])
    store.add_audit_log(current_user["id"], org_id, "tax.declaration.submitted", {"record_id": declaration["id"], "tax_year": tax_year})
    return declaration


@router.get("/tax/declarations")
def list_tax_declarations(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _owner_items("tax_declarations", current_user)


@router.patch("/tax/declarations/{declaration_id}/decision")
def decide_tax_declaration(
    declaration_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    decision = payload.get("status")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Status must be approved or rejected")
    declaration = _record("tax_declarations", declaration_id, org_id, "Tax declaration")
    if declaration["status"] != "submitted":
        raise HTTPException(status_code=409, detail="Declaration has already been reviewed")
    updated = store.update_module_record("tax_declarations", declaration_id, org_id, {
        "status": decision,
        "reviewed_by": current_user["id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_comment": str(payload.get("comment", "")).strip(),
    })
    notify_user(org_id, declaration["user_id"], f"tax.declaration.{decision}", f"Tax declaration {decision}", f"Your {declaration['tax_year']} tax declaration was {decision}.", "tax_declaration", declaration_id)
    store.add_audit_log(current_user["id"], org_id, f"tax.declaration.{decision}", {"record_id": declaration_id})
    return updated


@router.post("/tax/proofs", status_code=status.HTTP_201_CREATED)
async def upload_investment_proof(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    form = await request.form()
    file = form.get("file")
    if not file or not getattr(file, "filename", None):
        raise HTTPException(status_code=422, detail="Investment proof file is required")
    extension = Path(file.filename).suffix.lower()
    if extension not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=415, detail="Proof must be PDF or image format")
    try:
        tax_year = int(form.get("tax_year", ""))
        amount = float(form.get("amount", ""))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Tax year and proof amount are required") from exc
    declaration_id = str(form.get("declaration_id", ""))
    declaration = _record("tax_declarations", declaration_id, org_id, "Tax declaration")
    if declaration.get("user_id") != current_user["id"] and current_user.get("role") not in HR_ROLES:
        raise HTTPException(status_code=404, detail="Tax declaration not found")
    if tax_year != declaration["tax_year"] or amount <= 0:
        raise HTTPException(status_code=422, detail="Proof year must match the declaration and amount must be positive")
    content = await file.read(MAX_PROOF_BYTES + 1)
    if not content or len(content) > MAX_PROOF_BYTES:
        raise HTTPException(status_code=413, detail="Proof must be non-empty and 10 MB or smaller")
    proof_id = str(uuid.uuid4())
    directory = UPLOAD_ROOT / org_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"tax-proof-{proof_id}{extension}"
    path.write_bytes(content)
    proof = store.create_module_record("investment_proofs", {
        "id": proof_id,
        "org_id": org_id,
        "user_id": declaration["user_id"],
        "declaration_id": declaration_id,
        "tax_year": tax_year,
        "category": str(form.get("category", "investment")).strip(),
        "amount": amount,
        "file_name": Path(file.filename).name,
        "content_type": file.content_type or "application/octet-stream",
        "storage_path": str(path),
        "status": "pending_verification",
    })
    store.add_audit_log(current_user["id"], org_id, "tax.investment_proof.uploaded", {"record_id": proof_id})
    return _without_private_path(proof)


@router.get("/tax/proofs")
def list_investment_proofs(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return [_without_private_path(item) for item in _owner_items("investment_proofs", current_user)]


@router.get("/tax/proofs/{proof_id}/download")
def download_investment_proof(proof_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> FileResponse:
    org_id = _org_id(current_user)
    proof = store.get_module_record("investment_proofs", proof_id, org_id)
    if proof is None or (proof["user_id"] != current_user["id"] and current_user.get("role") not in HR_ROLES):
        raise HTTPException(status_code=404, detail="Investment proof not found")
    path = Path(proof["storage_path"])
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Proof file is unavailable")
    return FileResponse(path, media_type=proof["content_type"], filename=proof["file_name"])


@router.patch("/tax/proofs/{proof_id}/decision")
def decide_investment_proof(proof_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    decision = payload.get("status")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Status must be approved or rejected")
    proof = _record("investment_proofs", proof_id, org_id, "Investment proof")
    if proof["status"] != "pending_verification":
        raise HTTPException(status_code=409, detail="Proof has already been reviewed")
    updated = store.update_module_record("investment_proofs", proof_id, org_id, {
        "status": decision,
        "review_comment": str(payload.get("comment", "")).strip(),
        "reviewed_by": current_user["id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    })
    notify_user(org_id, proof["user_id"], f"tax.proof.{decision}", f"Investment proof {decision}", f"Your {proof['category']} proof was {decision}.", "investment_proof", proof_id)
    store.add_audit_log(current_user["id"], org_id, f"tax.investment_proof.{decision}", {"record_id": proof_id})
    return _without_private_path(updated)


@router.post("/tax/form16/generate", status_code=status.HTTP_201_CREATED)
def generate_form16(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    user = store.get_user_by_email(str(payload["employee_email"])) if payload.get("employee_email") else store.get_user_by_id(str(payload.get("user_id", "")))
    try:
        tax_year = int(payload["tax_year"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="tax_year is required") from exc
    if user is None or user.get("org_id") != org_id or not 2000 <= tax_year <= 2100:
        raise HTTPException(status_code=422, detail="Employee and tax year must be valid for this organization")
    year = str(tax_year)
    slips = [item for item in store.list_module_records("payslips", org_id) if item.get("user_id") == user["id"] and item.get("period_start", "").startswith(year) and item.get("status") == "available"]
    tds = sum(float(item.get("deductions", {}).get("Tax/TDS", 0)) for item in slips)
    record = store.create_module_record("form16_documents", {
        "org_id": org_id,
        "user_id": user["id"],
        "tax_year": tax_year,
        "salary_income": round(sum(float(item.get("gross_pay", 0)) for item in slips), 2),
        "tds_total": round(tds, 2),
        "payslip_count": len(slips),
        "status": "available",
        "generated_by": current_user["id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    store.add_audit_log(current_user["id"], org_id, "tax.form16.generated", {"record_id": record["id"], "user_id": user["id"], "tax_year": tax_year})
    return record


@router.get("/tax/form16")
def list_form16(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _owner_items("form16_documents", current_user)


@router.get("/tax/form16/{form_id}/download")
def download_form16(form_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Response:
    org_id = _org_id(current_user)
    record = store.get_module_record("form16_documents", form_id, org_id)
    if record is None or (record["user_id"] != current_user["id"] and current_user.get("role") not in HR_ROLES):
        raise HTTPException(status_code=404, detail="Form 16 not found")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Tax year", "Employee", "Salary income", "TDS total"])
    user = store.get_user_by_id(record["user_id"])
    writer.writerow([record["tax_year"], user["email"] if user else "", record["salary_income"], record["tds_total"]])
    store.add_audit_log(current_user["id"], org_id, "tax.form16.accessed", {"record_id": form_id})
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=form16-{record['tax_year']}.csv"})


@router.post("/insurance/policies", status_code=status.HTTP_201_CREATED)
def create_insurance_policy(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=422, detail="Insurance policy name is required")
    try:
        coverage = float(payload.get("coverage_amount", 0))
        employee_premium = float(payload.get("employee_premium", 0))
        employer_premium = float(payload.get("employer_premium", 0))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Coverage and premium values must be numeric") from exc
    if min(coverage, employee_premium, employer_premium) < 0:
        raise HTTPException(status_code=422, detail="Insurance values cannot be negative")
    return store.create_module_record("insurance_policies", {
        "org_id": org_id,
        "name": name,
        "insurer": str(payload.get("insurer", "")).strip(),
        "coverage_amount": coverage,
        "employee_premium": employee_premium,
        "employer_premium": employer_premium,
        "coverage_type": payload.get("coverage_type", "health"),
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
        "active": True,
        "created_by": current_user["id"],
    })


@router.get("/insurance/policies")
def list_insurance_policies(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    if not current_user.get("org_id"):
        return []
    return store.list_module_records("insurance_policies", current_user["org_id"])


@router.post("/insurance/enrollments", status_code=status.HTTP_201_CREATED)
def enroll_insurance(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    policy_id = payload.get("policy_id")
    policy = _record("insurance_policies", str(policy_id or ""), org_id, "Insurance policy")
    if not policy.get("active"):
        raise HTTPException(status_code=409, detail="Insurance policy is inactive")
    employee_id = payload.get("user_id", current_user["id"])
    if employee_id != current_user["id"] and current_user.get("role") not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Employees can only enroll themselves")
    employee = store.get_user_by_id(employee_id)
    if employee is None or employee.get("org_id") != org_id:
        raise HTTPException(status_code=422, detail="Employee must belong to this organization")
    existing = [item for item in store.list_module_records("employee_insurance_enrollments", org_id) if item.get("user_id") == employee_id and item.get("policy_id") == policy_id and item.get("status") == "active"]
    if existing:
        raise HTTPException(status_code=409, detail="Employee is already enrolled in this policy")
    enrollment = store.create_module_record("employee_insurance_enrollments", {
        "org_id": org_id,
        "user_id": employee_id,
        "policy_id": policy_id,
        "coverage_amount": float(payload.get("coverage_amount", policy["coverage_amount"])),
        "status": "active",
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
    })
    store.add_audit_log(current_user["id"], org_id, "insurance.enrollment.created", {"record_id": enrollment["id"], "user_id": employee_id})
    return enrollment


@router.get("/insurance/enrollments")
def list_insurance_enrollments(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _owner_items("employee_insurance_enrollments", current_user)


@router.post("/insurance/dependents", status_code=status.HTTP_201_CREATED)
def add_insurance_dependent(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    enrollment = _record("employee_insurance_enrollments", str(payload.get("enrollment_id", "")), org_id, "Enrollment")
    if enrollment["user_id"] != current_user["id"] and current_user.get("role") not in HR_ROLES:
        raise HTTPException(status_code=404, detail="Insurance enrollment not found")
    name = str(payload.get("name", "")).strip()
    relationship = str(payload.get("relationship", "")).strip()
    if not name or not relationship:
        raise HTTPException(status_code=422, detail="Dependent name and relationship are required")
    dependent = store.create_module_record("insurance_dependents", {
        "org_id": org_id,
        "enrollment_id": enrollment["id"],
        "user_id": enrollment["user_id"],
        "name": name,
        "relationship": relationship,
        "date_of_birth": payload.get("date_of_birth"),
    })
    store.add_audit_log(current_user["id"], org_id, "insurance.dependent.created", {"record_id": dependent["id"]})
    return dependent


@router.get("/insurance/dependents")
def list_insurance_dependents(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _owner_items("insurance_dependents", current_user)


@router.post("/insurance/claims", status_code=status.HTTP_201_CREATED)
def create_insurance_claim(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    enrollment = _record("employee_insurance_enrollments", str(payload.get("enrollment_id", "")), org_id, "Enrollment")
    if enrollment["user_id"] != current_user["id"] and current_user.get("role") not in HR_ROLES:
        raise HTTPException(status_code=404, detail="Insurance enrollment not found")
    try:
        amount = float(payload["amount"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Claim amount is required") from exc
    if amount <= 0 or not str(payload.get("description", "")).strip():
        raise HTTPException(status_code=422, detail="Positive claim amount and description are required")
    claim = store.create_module_record("insurance_claims", {
        "org_id": org_id,
        "enrollment_id": enrollment["id"],
        "user_id": enrollment["user_id"],
        "amount": amount,
        "description": str(payload["description"]).strip(),
        "claim_date": payload.get("claim_date", date.today().isoformat()),
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    for user in store.users.values():
        if user.get("org_id") == org_id and user.get("role") in HR_ROLES:
            notify_user(org_id, user["id"], "insurance.claim.submitted", "Insurance claim submitted", "An insurance claim is awaiting review.", "insurance_claim", claim["id"])
    return claim


@router.get("/insurance/claims")
def list_insurance_claims(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _owner_items("insurance_claims", current_user)


@router.patch("/insurance/claims/{claim_id}/decision")
def decide_insurance_claim(claim_id: str, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    decision = payload.get("status")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Status must be approved or rejected")
    claim = _record("insurance_claims", claim_id, org_id, "Claim")
    if claim["status"] != "submitted":
        raise HTTPException(status_code=409, detail="Claim has already been reviewed")
    updated = store.update_module_record("insurance_claims", claim_id, org_id, {
        "status": decision,
        "reviewed_by": current_user["id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_comment": str(payload.get("comment", "")).strip(),
    })
    notify_user(org_id, claim["user_id"], f"insurance.claim.{decision}", f"Insurance claim {decision}", f"Your insurance claim was {decision}.", "insurance_claim", claim_id)
    store.add_audit_log(current_user["id"], org_id, f"insurance.claim.{decision}", {"record_id": claim_id})
    return updated
