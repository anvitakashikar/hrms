from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_signup_and_login_flow():
    signup = client.post(
        "/api/auth/signup",
        json={
            "email": "admin@demo.com",
            "password": "StrongPass123!",
            "first_name": "System",
            "last_name": "Admin",
            "role": "admin",
            "org_name": "Acme Corp",
        },
    )
    assert signup.status_code == 201, signup.text
    payload = signup.json()
    assert payload["user"]["email"] == "admin@demo.com"
    token = client.post(
        "/api/auth/login",
        json={"email": "admin@demo.com", "password": "StrongPass123!"},
    )
    assert token.status_code == 200, token.text
    data = token.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "admin@demo.com"


def test_org_isolation_for_employee_listing():
    org_a = client.post(
        "/api/auth/signup",
        json={
            "email": "hr@org1.com",
            "password": "StrongPass123!",
            "first_name": "HR",
            "last_name": "One",
            "role": "hr",
            "org_name": "Org One",
        },
    )
    org_b = client.post(
        "/api/auth/signup",
        json={
            "email": "hr@org2.com",
            "password": "StrongPass123!",
            "first_name": "HR",
            "last_name": "Two",
            "role": "hr",
            "org_name": "Org Two",
        },
    )
    assert org_a.status_code == 201
    assert org_b.status_code == 201

    token_a = client.post(
        "/api/auth/login",
        json={"email": "hr@org1.com", "password": "StrongPass123!"},
    ).json()
    token_b = client.post(
        "/api/auth/login",
        json={"email": "hr@org2.com", "password": "StrongPass123!"},
    ).json()

    list_a = client.get(
        "/api/employees/",
        headers={"Authorization": f"Bearer {token_a['access_token']}"},
    )
    list_b = client.get(
        "/api/employees/",
        headers={"Authorization": f"Bearer {token_b['access_token']}"},
    )
    assert list_a.status_code == 200
    assert list_b.status_code == 200
    assert list_a.json()["items"] != list_b.json()["items"]
