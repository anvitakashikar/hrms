from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.database import get_store
from app.main import app

client = TestClient(app)


def _account(email, role, org):
    signup = client.post("/api/auth/signup", json={
        "email": email,
        "password": "StrongPass123!",
        "first_name": role.title(),
        "last_name": "Reminder",
        "role": role,
        "org_name": org,
    })
    assert signup.status_code == 201, signup.text
    login = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    return signup.json()["user"], {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_reminder_sweep_is_idempotent_and_role_protected():
    org = "Reminder Workflow Org"
    admin, admin_headers = _account("reminder-admin@example.com", "admin", org)
    employee, employee_headers = _account("reminder-employee@example.com", "employee", org)
    org_id = employee["org_id"]
    store = get_store()
    store.create_module_record("onboarding_tasks", {
        "org_id": org_id,
        "employee_user_id": employee["id"],
        "title": "Submit documents",
        "due_date": (date.today() - timedelta(days=2)).isoformat(),
        "status": "pending",
    })
    store.create_module_record("employee_documents", {
        "org_id": org_id,
        "owner_user_id": employee["id"],
        "category": "Passport",
        "expiry_date": (date.today() + timedelta(days=10)).isoformat(),
        "status": "approved",
    })

    assert client.post("/api/notifications/reminders/run", headers=employee_headers).status_code == 403
    first = client.post("/api/notifications/reminders/run", headers=admin_headers)
    assert first.status_code == 200, first.text
    assert first.json()["created_count"] == 2
    second = client.post("/api/notifications/reminders/run", headers=admin_headers)
    assert second.status_code == 200
    assert second.json()["created_count"] == 0
    notifications = client.get("/api/notifications", headers=employee_headers)
    assert len(notifications.json()) == 2
