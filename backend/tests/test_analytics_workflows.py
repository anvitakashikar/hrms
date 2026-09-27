from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_user(email, role, org):
    signup = client.post("/api/auth/signup", json={
        "email": email,
        "password": "StrongPass123!",
        "first_name": role.title(),
        "last_name": "Analytics",
        "role": role,
        "org_name": org,
    })
    assert signup.status_code == 201, signup.text
    login = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert login.status_code == 200
    return signup.json()["user"], {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_role_scoped_analytics_dashboard():
    org = "Analytics Workflow Org"
    admin, admin_headers = _create_user("analytics-admin@example.com", "admin", org)
    employee, employee_headers = _create_user("analytics-employee@example.com", "employee", org)
    expense = client.post("/api/expenses/claims", headers=employee_headers, json={
        "category": "Travel", "amount": 50, "currency": "USD", "description": "Site visit", "expense_date": "2026-09-25",
    })
    assert expense.status_code == 201

    employee_dashboard = client.get("/api/analytics/dashboard", headers=employee_headers)
    assert employee_dashboard.status_code == 200
    assert employee_dashboard.json()["expense_claims"]["pending"] == 1
    assert "headcount" not in employee_dashboard.json()

    admin_dashboard = client.get("/api/analytics/dashboard", headers=admin_headers)
    assert admin_dashboard.status_code == 200
    assert admin_dashboard.json()["headcount"] >= 2
    assert admin_dashboard.json()["expenses"]["pending"] == 1
