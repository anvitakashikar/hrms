from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _signup(email, role, org_name):
    response = client.post("/api/auth/signup", json={
        "email": email,
        "password": "StrongPass123!",
        "first_name": role.title(),
        "last_name": "Benefits",
        "role": role,
        "org_name": org_name,
    })
    assert response.status_code == 201, response.text
    return response.json()["user"]


def _headers(email):
    response = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_statutory_tax_proof_and_insurance_workflows():
    org_name = "Benefits Workflow Organization"
    admin = _signup("benefits-admin@example.com", "admin", org_name)
    employee = _signup("benefits-employee@example.com", "employee", org_name)
    admin_headers = _headers(admin["email"])
    employee_headers = _headers(employee["email"])

    pf_config = client.post("/api/statutory/config", headers=admin_headers, json={
        "kind": "pf", "name": "Company PF", "employee_rate": 12, "employer_rate": 12, "threshold": 0, "wage_cap": 15000,
    })
    esi_config = client.post("/api/statutory/config", headers=admin_headers, json={
        "kind": "esi", "name": "Company ESI", "employee_rate": 0.75, "employer_rate": 3.25, "threshold": 21000,
    })
    assert pf_config.status_code == 201, pf_config.text
    assert esi_config.status_code == 201, esi_config.text
    payroll_rules = client.get("/api/payroll/deduction-rules", headers=admin_headers)
    assert payroll_rules.status_code == 200
    assert {item["kind"] for item in payroll_rules.json()} >= {"pf", "esi"}

    statutory = client.put("/api/statutory/me", headers=employee_headers, json={
        "pf_member_id": "PF-123", "esi_number": "ESI-456", "pan": "ABCDE1234F", "pf_eligible": True, "esi_eligible": True,
    })
    assert statutory.status_code == 200
    assert client.get("/api/statutory/me", headers=employee_headers).json()["pf_member_id"] == "PF-123"
    hr_statutory = client.get("/api/statutory/employees", headers=admin_headers)
    assert hr_statutory.status_code == 200
    assert any(item["user_id"] == employee["id"] for item in hr_statutory.json())

    declaration = client.post("/api/tax/declarations", headers=employee_headers, json={
        "tax_year": 2026, "tax_regime": "default", "declared_investment_amount": 1000, "declaration": {"section": "80C"},
    })
    assert declaration.status_code == 201, declaration.text
    proof = client.post(
        "/api/tax/proofs",
        headers=employee_headers,
        data={"declaration_id": declaration.json()["id"], "tax_year": "2026", "amount": "1000", "category": "80C"},
        files={"file": ("investment.pdf", b"proof contents", "application/pdf")},
    )
    assert proof.status_code == 201, proof.text
    verification = client.patch(
        f"/api/tax/proofs/{proof.json()['id']}/decision",
        headers=admin_headers,
        json={"status": "approved"},
    )
    assert verification.status_code == 200
    assert client.get(f"/api/tax/proofs/{proof.json()['id']}/download", headers=employee_headers).content == b"proof contents"

    policy = client.post("/api/insurance/policies", headers=admin_headers, json={
        "name": "Health cover", "insurer": "Example Mutual", "coverage_amount": 100000, "employee_premium": 100, "employer_premium": 500,
    })
    assert policy.status_code == 201, policy.text
    enrollment = client.post("/api/insurance/enrollments", headers=employee_headers, json={"policy_id": policy.json()["id"]})
    assert enrollment.status_code == 201, enrollment.text
    dependent = client.post("/api/insurance/dependents", headers=employee_headers, json={
        "enrollment_id": enrollment.json()["id"], "name": "Taylor Benefits", "relationship": "spouse",
    })
    assert dependent.status_code == 201, dependent.text
    claim = client.post("/api/insurance/claims", headers=employee_headers, json={
        "enrollment_id": enrollment.json()["id"], "amount": 250, "description": "Clinic visit",
    })
    assert claim.status_code == 201, claim.text
    claim_decision = client.patch(
        f"/api/insurance/claims/{claim.json()['id']}/decision",
        headers=admin_headers,
        json={"status": "approved"},
    )
    assert claim_decision.status_code == 200

    form16 = client.post("/api/tax/form16/generate", headers=admin_headers, json={"user_id": employee["id"], "tax_year": 2026})
    assert form16.status_code == 201, form16.text
    assert client.get(f"/api/tax/form16/{form16.json()['id']}/download", headers=employee_headers).status_code == 200


def test_pf_payroll_respects_employee_eligibility_and_wage_cap():
    org_name = "Statutory Payroll Organization"
    admin = _signup("statutory-admin@example.com", "admin", org_name)
    eligible_employee = _signup("pf-eligible@example.com", "employee", org_name)
    ineligible_employee = _signup("pf-ineligible@example.com", "employee", org_name)
    admin_headers = _headers(admin["email"])
    eligible_headers = _headers(eligible_employee["email"])

    config = client.post("/api/statutory/config", headers=admin_headers, json={
        "kind": "pf", "name": "Capped PF", "employee_rate": 10, "employer_rate": 10, "wage_cap": 4000,
    })
    assert config.status_code == 201, config.text
    client.put("/api/statutory/me", headers=eligible_headers, json={"pf_eligible": True})

    employee_items = client.get("/api/employees/", headers=admin_headers).json()["items"]
    for person in (eligible_employee, ineligible_employee):
        employee_item = next(item for item in employee_items if item["email"] == person["email"])
        structure = client.post("/api/payroll/structures", headers=admin_headers, json={"employee_id": employee_item["id"], "base_salary": 5000})
        assert structure.status_code == 201, structure.text

    run = client.post("/api/payroll/runs", headers=admin_headers, json={"period_start": "2026-09-01", "period_end": "2026-09-30"})
    assert run.status_code == 201, run.text
    slips = {item["user_id"]: item for item in run.json()["payslips"]}
    assert slips[eligible_employee["id"]]["deductions"]["PF"] == 400
    assert "PF" not in slips[ineligible_employee["id"]]["deductions"]
    pf_report = client.get("/api/payroll/statutory/pf/reports", headers=admin_headers)
    assert pf_report.status_code == 200
    assert pf_report.json()["employee_total"] == 400
