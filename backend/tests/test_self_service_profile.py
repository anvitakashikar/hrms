from fastapi.testclient import TestClient

from app.main import app
from app.database import get_store

client = TestClient(app)


def test_self_service_profile_only_updates_allowlisted_fields():
    signup = client.post("/api/auth/signup", json={
        "email": "self-service@example.com",
        "password": "StrongPass123!",
        "first_name": "Original",
        "last_name": "Name",
        "role": "employee",
        "org_name": "Self Service Organization",
    })
    assert signup.status_code == 201
    login = client.post("/api/auth/login", json={"email": "self-service@example.com", "password": "StrongPass123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    profile = client.get("/api/self-service/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["email"] == "self-service@example.com"
    assert "base_salary" not in profile.json()

    updated = client.patch("/api/self-service/profile", headers=headers, json={
        "first_name": "Updated",
        "phone": "+1-555-0123",
        "base_salary": 1,
        "role": "admin",
    })
    assert updated.status_code == 200
    assert updated.json()["first_name"] == "Updated"
    assert updated.json()["phone"] == "+1-555-0123"
    assert updated.json()["role"] == "employee"
    assert "base_salary" not in updated.json()
    assert client.get("/api/auth/me", headers=headers).json()["first_name"] == "Updated"
    assert any(item["event"] == "employee.profile.updated" for item in get_store().audit_logs)
