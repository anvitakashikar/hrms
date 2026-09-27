from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _login(email: str, password: str = "StrongPass123!"):
    resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_leave_application_and_approval_flow():
    client.post(
        "/api/auth/signup",
        json={
            "email": "manager@demo.com",
            "password": "StrongPass123!",
            "first_name": "Manager",
            "last_name": "Demo",
            "role": "manager",
            "org_name": "DemoOrg",
        },
    )
    client.post(
        "/api/auth/signup",
        json={
            "email": "employee@demo.com",
            "password": "StrongPass123!",
            "first_name": "Employee",
            "last_name": "Demo",
            "role": "employee",
            "org_name": "DemoOrg",
        },
    )

    token = _login("employee@demo.com")
    leave_resp = client.post(
        "/api/leave/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "leave_type": "Annual",
            "start_date": "2026-10-05",
            "end_date": "2026-10-07",
            "reason": "Family trip",
        },
    )
    assert leave_resp.status_code == 201, leave_resp.text
    entry = leave_resp.json()
    assert entry["status"] == "pending"

    manager_token = _login("manager@demo.com")
    approval = client.patch(
        f"/api/leave/applications/{entry['id']}/approve",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"comment": "Approved"},
    )
    assert approval.status_code == 200, approval.text
    assert approval.json()["status"] == "approved"
    notifications = client.get(
        "/api/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert notifications.status_code == 200, notifications.text
    assert any(item["event"] == "leave.approved" for item in notifications.json())


def test_expense_claim_and_payroll_snapshot():
    client.post(
        "/api/auth/signup",
        json={
            "email": "employee2@demo.com",
            "password": "StrongPass123!",
            "first_name": "Second",
            "last_name": "Employee",
            "role": "employee",
            "org_name": "DemoOrg",
        },
    )

    token = _login("employee2@demo.com")
    expense = client.post(
        "/api/expenses/claims",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "category": "Travel",
            "amount": 250.0,
            "currency": "INR",
            "description": "Client travel",
            "expense_date": "2026-09-27",
        },
    )
    assert expense.status_code == 201, expense.text
    claim = expense.json()
    assert claim["status"] == "submitted"

    payroll = client.get(
        "/api/payroll/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert payroll.status_code == 200, payroll.text
    assert "net_salary" in payroll.json()
