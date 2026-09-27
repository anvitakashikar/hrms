from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _signup_login(email, role, org_name):
    signup = client.post("/api/auth/signup", json={
        "email": email,
        "password": "StrongPass123!",
        "first_name": role.title(),
        "last_name": "Extraction",
        "role": role,
        "org_name": org_name,
    })
    assert signup.status_code == 201, signup.text
    login = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert login.status_code == 200, login.text
    return signup.json()["user"], {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_receipt_extraction_returns_editable_suggestions_without_creating_claim():
    _, headers = _signup_login("receipt-employee@example.com", "employee", "Receipt Extraction Org")
    receipt_text = b"Northstar Cafe\n2026-09-12\nTax: USD 2.50\nTotal: USD 18.75\nCoffee and lunch"
    response = client.post("/api/expenses/receipt-ocr", headers=headers, files={"file": ("receipt.txt", receipt_text, "text/plain")})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["merchant_suggestion"] == "Northstar Cafe"
    assert result["amount_suggestion"] == 18.75
    assert result["tax_suggestion"] == 2.5
    assert result["currency_suggestion"] == "USD"
    assert result["requires_employee_review"] is True
    assert client.get("/api/expenses/claims", headers=headers).json() == []


def test_resume_extraction_requires_human_confirmation_and_matches_job():
    admin, headers = _signup_login("resume-admin@example.com", "admin", "Resume Extraction Org")
    job = client.post("/api/recruitment/jobs", headers=headers, json={
        "title": "Data Analyst", "department": "Analytics", "open_positions": 1, "description": "Python SQL analytics reporting",
    })
    assert job.status_code == 201, job.text
    application = client.post("/api/recruitment/applicants", headers=headers, json={
        "job_id": job.json()["id"], "candidate_name": "Candidate Before Review", "email": "candidate@example.com",
    })
    assert application.status_code == 201

    resume = b"Jordan Candidate\njordan@example.com\n555-123-4567\n5 years experience\nPython SQL analytics\nBachelor degree"
    extracted = client.post(
        f"/api/recruitment/applicants/{application.json()['id']}/resume",
        headers=headers,
        files={"file": ("resume.txt", resume, "text/plain")},
    )
    assert extracted.status_code == 201, extracted.text
    fields = extracted.json()["extracted_fields"]
    assert fields["email_suggestion"] == "jordan@example.com"
    assert fields["experience_years"] == 5
    assert extracted.json()["review_status"] == "needs_review"

    matches = client.get(f"/api/recruitment/matching/{job.json()['id']}", headers=headers)
    assert matches.status_code == 200
    assert matches.json()[0]["decision_support_only"] is True

    confirmed = client.patch(
        f"/api/recruitment/resumes/{extracted.json()['id']}/confirm",
        headers=headers,
        json={"fields": fields},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["review_status"] == "confirmed"
    updated_application = client.get("/api/recruitment/applicants", headers=headers).json()[0]
    assert updated_application["email"] == "jordan@example.com"