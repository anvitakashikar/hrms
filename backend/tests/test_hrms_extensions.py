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


def test_extended_hrms_lifecycle_modules():
    client.post(
        "/api/auth/signup",
        json={
            "email": "admin2@demo.com",
            "password": "StrongPass123!",
            "first_name": "Admin",
            "last_name": "Two",
            "role": "admin",
            "org_name": "ExtendedOrg",
        },
    )

    token = _login("admin2@demo.com")

    attendance = client.post(
        "/api/attendance/check-in",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert attendance.status_code == 200, attendance.text

    summary = client.get(
        "/api/attendance/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["checked_in"] >= 1

    onboarding = client.post(
        "/api/onboarding/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Laptop setup",
            "assignee": "employee@demo.com",
            "due_date": "2026-10-01",
            "status": "pending",
        },
    )
    assert onboarding.status_code == 201, onboarding.text
    tasks = client.get(
        "/api/onboarding/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert tasks.status_code == 200, tasks.text
    assert len(tasks.json()) >= 1

    job = client.post(
        "/api/recruitment/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Frontend Engineer",
            "department": "Product",
            "open_positions": 2,
        },
    )
    assert job.status_code == 201, job.text

    applicant = client.post(
        "/api/recruitment/applicants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_id": job.json()["id"],
            "candidate_name": "Alice Example",
            "email": "alice@example.com",
            "status": "screening",
        },
    )
    assert applicant.status_code == 201, applicant.text

    jobs = client.get(
        "/api/recruitment/jobs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert jobs.status_code == 200, jobs.text
    assert len(jobs.json()) >= 1

    document = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Offer Letter.pdf",
            "category": "HR",
            "owner": "employee@demo.com",
        },
    )
    assert document.status_code == 201, document.text
    docs = client.get(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert docs.status_code == 200, docs.text
    assert len(docs.json()) >= 1

    response = client.post(
        "/api/ai/assistant",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Summarize the pending HR actions for this week."},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "summary" in payload
    assert "actions" in payload
