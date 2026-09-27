from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _signup(email, role, org_name):
    response = client.post("/api/auth/signup", json={
        "email": email,
        "password": "StrongPass123!",
        "first_name": role.title(),
        "last_name": "Lifecycle",
        "role": role,
        "org_name": org_name,
    })
    assert response.status_code == 201, response.text
    return response.json()["user"]


def _headers(email):
    response = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_field_duty_location_is_event_scoped_and_requires_approval():
    org_name = "Duty Workflow Organization"
    admin = _signup("duty-admin@example.com", "admin", org_name)
    employee = _signup("duty-employee@example.com", "employee", org_name)
    admin_headers = _headers(admin["email"])
    employee_headers = _headers(employee["email"])

    request = client.post("/api/duty-requests", headers=employee_headers, json={
        "duty_type": "field", "start_date": "2026-09-27", "end_date": "2026-09-27", "location": "Client site", "purpose": "Installation",
    })
    assert request.status_code == 201, request.text
    denied_ping = client.post(f"/api/duty-requests/{request.json()['id']}/location-ping", headers=employee_headers, json={"latitude": 37.7, "longitude": -122.4})
    assert denied_ping.status_code == 403
    approved = client.patch(f"/api/duty-requests/{request.json()['id']}/decision", headers=admin_headers, json={"status": "approved"})
    assert approved.status_code == 200
    ping = client.post(f"/api/duty-requests/{request.json()['id']}/location-ping", headers=employee_headers, json={"latitude": 37.7, "longitude": -122.4})
    assert ping.status_code == 201, ping.text
    assert ping.json()["retention_purpose"] == "approved_field_duty"
    assert len(client.get("/api/field-duty/location-history", headers=employee_headers).json()) == 1


def test_letter_template_signature_confirmation_and_filtered_report():
    org_name = "Letters Reports Organization"
    admin = _signup("letters-admin@example.com", "admin", org_name)
    employee = _signup("letters-employee@example.com", "employee", org_name)
    admin_headers = _headers(admin["email"])
    employee_headers = _headers(employee["email"])
    employee_record = next(item for item in client.get("/api/employees/", headers=admin_headers).json()["items"] if item["email"] == employee["email"])

    template = client.post("/api/letter-templates", headers=admin_headers, json={
        "name": "Employment confirmation", "letter_type": "employment", "variables": ["employee_name"], "body": "This confirms {{employee_name}} is employed.",
    })
    assert template.status_code == 201, template.text
    issuance = client.post("/api/letters/issue", headers=admin_headers, json={
        "template_id": template.json()["id"], "employee_email": employee["email"], "values": {"employee_name": "Employee Lifecycle"},
    })
    assert issuance.status_code == 201, issuance.text
    assert "Employee Lifecycle" in issuance.json()["rendered_content"]
    assert len(client.get("/api/letters", headers=employee_headers).json()) == 1
    signature = client.post(f"/api/letters/{issuance.json()['id']}/signature-requests", headers=admin_headers, json={"signer_email": employee["email"]})
    assert signature.status_code == 201
    unconfirmed = client.patch(f"/api/signatures/{signature.json()['id']}/sign", headers=employee_headers, json={"confirmed": False})
    assert unconfirmed.status_code == 422
    signed = client.patch(f"/api/signatures/{signature.json()['id']}/sign", headers=employee_headers, json={"confirmed": True})
    assert signed.status_code == 200
    assert signed.json()["status"] == "signed"

    report = client.post("/api/reports/employees", headers=admin_headers, json={"department": employee_record["department"]})
    assert report.status_code == 200, report.text
    assert employee["email"] in report.text
