from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _signup(email, role, org_name):
    response = client.post("/api/auth/signup", json={
        "email": email,
        "password": "StrongPass123!",
        "first_name": role.title(),
        "last_name": "Privacy",
        "role": role,
        "org_name": org_name,
    })
    assert response.status_code == 201, response.text
    return response.json()["user"]


def _headers(email):
    response = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_posh_case_access_is_restricted_and_audited():
    org_name = "Restricted Compliance Organization"
    admin = _signup("posh-admin@example.com", "admin", org_name)
    employee = _signup("posh-employee@example.com", "employee", org_name)
    committee = _signup("posh-committee@example.com", "hr", org_name)
    outsider = _signup("posh-outsider@example.com", "employee", org_name)
    admin_headers = _headers(admin["email"])
    employee_headers = _headers(employee["email"])
    committee_headers = _headers(committee["email"])
    outsider_headers = _headers(outsider["email"])

    denied = client.get("/api/posh/complaints", headers=committee_headers)
    assert denied.status_code == 403
    committee_member = client.post("/api/posh/committee", headers=admin_headers, json={"user_id": committee["id"], "committee_role": "member"})
    assert committee_member.status_code == 201, committee_member.text

    complaint = client.post("/api/posh/complaints", headers=employee_headers, json={
        "incident_date": "2026-09-10", "description": "Confidential report", "respondent_name": "Restricted Person",
    })
    assert complaint.status_code == 201, complaint.text
    assert "description" not in complaint.json()
    assert len(client.get("/api/posh/complaints", headers=committee_headers).json()) == 1
    assert client.get("/api/posh/complaints", headers=outsider_headers).status_code == 403

    status_update = client.patch(
        f"/api/posh/complaints/{complaint.json()['id']}/status",
        headers=committee_headers,
        json={"status": "under_review", "note": "Assigned to committee"},
    )
    assert status_update.status_code == 200, status_update.text
    timeline = client.get(f"/api/posh/complaints/{complaint.json()['id']}/timeline", headers=committee_headers)
    assert timeline.status_code == 200
    assert timeline.json()[0]["status"] == "under_review"
    logs = client.get("/api/privacy/access-logs", headers=admin_headers)
    assert logs.status_code == 200
    assert any(item["record_type"] == "posh_complaint" for item in logs.json())


def test_employee_privacy_requests_and_admin_retention_controls():
    org_name = "Privacy Requests Organization"
    admin = _signup("privacy-admin@example.com", "admin", org_name)
    employee = _signup("privacy-employee@example.com", "employee", org_name)
    admin_headers = _headers(admin["email"])
    employee_headers = _headers(employee["email"])

    consent = client.post("/api/privacy/consents", headers=employee_headers, json={"purpose": "benefits_processing", "granted": True, "policy_version": "v2"})
    assert consent.status_code == 201
    assert len(client.get("/api/privacy/consents", headers=employee_headers).json()) == 1

    request = client.post("/api/privacy/requests", headers=employee_headers, json={"request_type": "export", "description": "Provide a copy of my records"})
    assert request.status_code == 201
    assert len(client.get("/api/privacy/requests", headers=admin_headers).json()) == 1
    decision = client.patch(f"/api/privacy/requests/{request.json()['id']}/decision", headers=admin_headers, json={"status": "completed", "response": "Export prepared"})
    assert decision.status_code == 200
    assert client.get("/api/privacy/requests", headers=employee_headers).json()[0]["status"] == "completed"

    retention = client.post("/api/privacy/retention-policies", headers=admin_headers, json={"record_type": "attendance", "retention_days": 365})
    assert retention.status_code == 201
    assert client.get("/api/privacy/retention-policies", headers=employee_headers).status_code == 403
    assert len(client.get("/api/privacy/retention-policies", headers=admin_headers).json()) == 1
