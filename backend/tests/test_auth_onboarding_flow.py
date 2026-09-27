from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_signup_does_not_create_org_or_employee_setup():
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "newadmin@demo.com",
            "password": "StrongPass123!",
            "first_name": "New",
            "last_name": "Admin",
            "role": "admin",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["user"]["role"] == "admin"
    assert payload["user"]["org_id"] is None
    assert "organization" not in payload


def test_admin_login_returns_onboarding_state_for_org_setup():
    response = client.post(
        "/api/auth/login",
        json={"email": "newadmin@demo.com", "password": "StrongPass123!"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["next_step"] == "organization_setup"
    assert body["onboarding"]["organization_configured"] is False


def test_admin_can_register_organization_after_login():
    token = client.post(
        "/api/auth/login",
        json={"email": "newadmin@demo.com", "password": "StrongPass123!"},
    ).json()["access_token"]

    reg = client.post(
        "/api/organizations/register",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "NewOrg",
            "legal_name": "NewOrg Legal",
            "email": "hello@neworg.com",
            "phone": "+123456789",
            "industry": "Technology",
            "company_type": "Private Limited",
            "timezone": "UTC",
            "currency": "USD",
        },
    )
    assert reg.status_code == 201, reg.text
    assert reg.json()["name"] == "NewOrg"

    login_after = client.post(
        "/api/auth/login",
        json={"email": "newadmin@demo.com", "password": "StrongPass123!"},
    )
    assert login_after.status_code == 200, login_after.text
    assert login_after.json()["next_step"] == "dashboard"
