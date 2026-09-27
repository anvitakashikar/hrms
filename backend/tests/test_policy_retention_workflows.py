from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import get_store
from app.main import app

client = TestClient(app)


def _admin_headers(email, org_name):
    signup = client.post("/api/auth/signup", json={
        "email": email,
        "password": "StrongPass123!",
        "first_name": "Policy",
        "last_name": "Admin",
        "role": "admin",
        "org_name": org_name,
    })
    assert signup.status_code == 201, signup.text
    login = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_policy_update_keeps_version_snapshots():
    headers = _admin_headers("policy-version-admin@example.com", "Policy Version Org")
    policy = client.post("/api/policies", headers=headers, json={"name": "Travel policy", "process": "expense"})
    assert policy.status_code == 200
    updated = client.patch(f"/api/policies/{policy.json()['id']}", headers=headers, json={"name": "Updated travel policy"})
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    versions = client.get(f"/api/policies/{policy.json()['id']}/versions", headers=headers)
    assert versions.status_code == 200
    assert versions.json()[0]["snapshot"]["name"] == "Travel policy"
    assert versions.json()[0]["version"] == 1


def test_retention_preview_and_run_delete_only_expired_matching_records():
    org_name = "Retention Workflow Org"
    headers = _admin_headers("retention-admin@example.com", org_name)
    organization_id = client.get("/api/auth/me", headers=headers).json()["org_id"]
    expired = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    fresh = datetime.now(timezone.utc).isoformat()
    store = get_store()
    old_record = store.create_module_record("ai_query_logs", {"org_id": organization_id, "user_id": "old-user", "query": "old query", "created_at": expired})
    new_record = store.create_module_record("ai_query_logs", {"org_id": organization_id, "user_id": "new-user", "query": "fresh query", "created_at": fresh})

    policy = client.post("/api/privacy/retention-policies", headers=headers, json={"record_type": "ai_queries", "retention_days": 30})
    assert policy.status_code == 201, policy.text
    preview = client.get("/api/privacy/retention/preview", headers=headers)
    assert preview.status_code == 200
    assert preview.json()["total_would_delete"] == 1
    assert store.get_module_record("ai_query_logs", old_record["id"], organization_id)

    result = client.post("/api/privacy/retention/run", headers=headers)
    assert result.status_code == 200
    assert result.json()["deleted_count"] == 1
    assert store.get_module_record("ai_query_logs", old_record["id"], organization_id) is None
    assert store.get_module_record("ai_query_logs", new_record["id"], organization_id) is not None
