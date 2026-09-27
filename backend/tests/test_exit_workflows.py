from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _signup(email, role, org_name):
    response = client.post("/api/auth/signup", json={
        "email": email,
        "password": "StrongPass123!",
        "first_name": role.title(),
        "last_name": "Exit",
        "role": role,
        "org_name": org_name,
    })
    assert response.status_code == 201, response.text
    return response.json()["user"]


def _headers(email):
    response = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_exit_approval_clearances_and_final_settlement():
    org_name = "Exit Workflow Organization"
    admin = _signup("exit-admin@example.com", "admin", org_name)
    employee = _signup("exit-employee@example.com", "employee", org_name)
    admin_headers = _headers(admin["email"])
    employee_headers = _headers(employee["email"])

    asset = client.post("/api/onboarding/assets", headers=admin_headers, json={"name": "Exit laptop"})
    assert asset.status_code == 201
    assignment = client.post(f"/api/onboarding/assets/{asset.json()['id']}/assign", headers=admin_headers, json={"user_id": employee["id"]})
    assert assignment.status_code == 200

    request = client.post("/api/exit/requests", headers=employee_headers, json={"last_working_day": "2026-10-15", "reason": "Career change"})
    assert request.status_code == 201, request.text
    approved = client.patch(f"/api/exit/requests/{request.json()['id']}/decision", headers=admin_headers, json={"status": "approved"})
    assert approved.status_code == 200
    clearances = client.get("/api/exit/clearances", headers=admin_headers)
    assert len(clearances.json()) == 5

    blocked = client.post("/api/exit/settlements/preview", headers=admin_headers, json={"exit_request_id": request.json()["id"], "gratuity_amount": 500})
    assert blocked.status_code == 200
    assert blocked.json()["clearances_complete"] is False
    assert client.post("/api/exit/settlements", headers=admin_headers, json={"exit_request_id": request.json()["id"]}).status_code == 409

    asset_clearance = next(item for item in clearances.json() if item["department"] == "assets")
    blocked_asset_clearance = client.patch(f"/api/exit/clearances/{asset_clearance['id']}", headers=admin_headers, json={"status": "cleared"})
    assert blocked_asset_clearance.status_code == 409
    assert client.patch(f"/api/onboarding/assets/{asset.json()['id']}/return", headers=admin_headers).status_code == 200
    for clearance in clearances.json():
        if clearance["department"] == "assets":
            continue
        completed = client.patch(f"/api/exit/clearances/{clearance['id']}", headers=admin_headers, json={"status": "cleared", "comment": "Returned"})
        assert completed.status_code == 200
    cleared_asset = client.patch(f"/api/exit/clearances/{asset_clearance['id']}", headers=admin_headers, json={"status": "cleared"})
    assert cleared_asset.status_code == 200
    gratuity = client.post("/api/exit/gratuity", headers=admin_headers, json={"exit_request_id": request.json()["id"], "amount": 500})
    assert gratuity.status_code == 201
    settlement = client.post("/api/exit/settlements", headers=admin_headers, json={"exit_request_id": request.json()["id"], "gratuity_amount": 500, "leave_settlement": 250})
    assert settlement.status_code == 201, settlement.text
    assert settlement.json()["status"] == "finalized"
    assert settlement.json()["net_total"] >= 750
