from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _signup(email, role, org_name, first_name="Test"):
    response = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "StrongPass123!",
            "first_name": first_name,
            "last_name": "User",
            "role": role,
            "org_name": org_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["user"]


def _token(email):
    response = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_document_review_replace_and_private_download():
    org_name = "Docs Workflow Organization"
    admin = _signup("docs-admin@example.com", "admin", org_name)
    employee = _signup("docs-employee@example.com", "employee", org_name)
    admin_headers = {"Authorization": f"Bearer {_token(admin['email'])}"}
    employee_headers = {"Authorization": f"Bearer {_token(employee['email'])}"}

    category = client.post(
        "/api/documents/categories",
        headers=admin_headers,
        json={"name": "Identity proof", "required": True},
    )
    assert category.status_code == 201, category.text

    upload = client.post(
        "/api/documents",
        headers=employee_headers,
        data={"category_id": category.json()["id"], "expiry_date": "2030-01-01"},
        files={"file": ("identity.pdf", b"first document", "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["id"]
    assert upload.json()["status"] == "pending_verification"

    assert len(client.get("/api/documents", headers=employee_headers).json()) == 1
    assert len(client.get("/api/documents", headers=admin_headers).json()) == 1
    assert client.get("/api/documents/missing", headers=admin_headers).json()

    rejected_without_reason = client.patch(
        f"/api/documents/{document_id}/verification",
        headers=admin_headers,
        json={"status": "rejected"},
    )
    assert rejected_without_reason.status_code == 422

    rejected = client.patch(
        f"/api/documents/{document_id}/verification",
        headers=admin_headers,
        json={"status": "rejected", "rejection_reason": "Image is unreadable"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    replacement = client.post(
        f"/api/documents/{document_id}/replace",
        headers=employee_headers,
        data={"expiry_date": "2031-01-01"},
        files={"file": ("identity-replacement.pdf", b"replacement document", "application/pdf")},
    )
    assert replacement.status_code == 200, replacement.text
    assert replacement.json()["status"] == "pending_verification"
    assert replacement.json()["version"] == 2

    approved = client.patch(
        f"/api/documents/{document_id}/verification",
        headers=admin_headers,
        json={"status": "approved"},
    )
    assert approved.status_code == 200
    assert client.get("/api/documents/missing", headers=admin_headers).json() == []
    download = client.get(f"/api/documents/{document_id}/download", headers=employee_headers)
    assert download.status_code == 200
    assert download.content == b"replacement document"

    other_admin = _signup("other-doc-admin@example.com", "admin", "Other Docs Organization")
    other_headers = {"Authorization": f"Bearer {_token(other_admin['email'])}"}
    assert client.get(f"/api/documents/{document_id}/download", headers=other_headers).status_code == 404


def test_attendance_shift_checkin_checkout_and_regularization():
    org_name = "Attendance Workflow Organization"
    admin = _signup("attendance-admin@example.com", "admin", org_name)
    employee = _signup("attendance-employee@example.com", "employee", org_name)
    admin_headers = {"Authorization": f"Bearer {_token(admin['email'])}"}
    employee_headers = {"Authorization": f"Bearer {_token(employee['email'])}"}

    attendance_policy = client.post(
        "/api/policies",
        headers=admin_headers,
        json={"name": "Attendance grace", "process": "attendance"},
    )
    assert attendance_policy.status_code == 200
    policy_rule = client.post(
        f"/api/policies/{attendance_policy.json()['id']}/rules",
        headers=admin_headers,
        json={"key": "grace_minutes", "value": 1440},
    )
    assert policy_rule.status_code == 200

    shift = client.post(
        "/api/attendance/shifts",
        headers=admin_headers,
        json={"name": "Standard", "start_time": "00:00", "end_time": "23:59", "grace_minutes": 5},
    )
    assert shift.status_code == 201, shift.text
    assignment = client.post(
        f"/api/attendance/shifts/{shift.json()['id']}/assignments",
        headers=admin_headers,
        json={"user_id": employee["id"]},
    )
    assert assignment.status_code == 201, assignment.text

    check_in = client.post("/api/attendance/check-in", headers=employee_headers, json={})
    assert check_in.status_code == 200, check_in.text
    assert check_in.json()["check_in_at"]
    assert check_in.json()["late_minutes"] == 0
    assert client.post("/api/attendance/check-in", headers=employee_headers, json={}).status_code == 409

    check_out = client.post("/api/attendance/check-out", headers=employee_headers, json={})
    assert check_out.status_code == 200, check_out.text
    assert check_out.json()["check_out_at"]
    assert check_out.json()["working_minutes"] >= 0
    assert len(client.get("/api/attendance/history", headers=employee_headers).json()) == 1

    request = client.post(
        "/api/attendance/regularization-requests",
        headers=employee_headers,
        json={
            "attendance_record_id": check_out.json()["id"],
            "work_date": check_out.json()["work_date"],
            "requested_check_in": datetime.now(timezone.utc).isoformat(),
            "reason": "Correct a missed punch",
        },
    )
    assert request.status_code == 201, request.text
    assert request.json()["status"] == "pending"
    assert len(client.get("/api/attendance/regularization-requests", headers=employee_headers).json()) == 1

    decision = client.patch(
        f"/api/attendance/regularization-requests/{request.json()['id']}/decision",
        headers=admin_headers,
        json={"status": "approved", "comment": "Verified"},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "approved"


def test_attendance_geofence_rejects_outside_location():
    org_name = "Geo Fence Workflow Organization"
    admin = _signup("geo-admin@example.com", "admin", org_name)
    employee = _signup("geo-employee@example.com", "employee", org_name)
    admin_headers = {"Authorization": f"Bearer {_token(admin['email'])}"}
    employee_headers = {"Authorization": f"Bearer {_token(employee['email'])}"}
    zone = client.post(
        "/api/attendance/geo-fences",
        headers=admin_headers,
        json={"name": "HQ", "latitude": 37.7749, "longitude": -122.4194, "radius_meters": 100},
    )
    assert zone.status_code == 201, zone.text

    missing_location = client.post("/api/attendance/check-in", headers=employee_headers, json={})
    assert missing_location.status_code == 422
    outside_location = client.post(
        "/api/attendance/check-in",
        headers=employee_headers,
        json={"latitude": 40.7128, "longitude": -74.0060},
    )
    assert outside_location.status_code == 403
    assert client.get("/api/attendance/location-history", headers=employee_headers).json() == []


def test_policy_assignment_and_holiday_aware_leave_days():
    org_name = "Policy Calendar Organization"
    admin = _signup("policy-admin@example.com", "admin", org_name)
    employee = _signup("policy-employee@example.com", "employee", org_name)
    admin_headers = {"Authorization": f"Bearer {_token(admin['email'])}"}
    employee_headers = {"Authorization": f"Bearer {_token(employee['email'])}"}

    policy = client.post(
        "/api/policies",
        headers=admin_headers,
        json={"name": "Standard leave policy", "process": "leave", "department": "General"},
    )
    assert policy.status_code == 200, policy.text
    rule = client.post(
        f"/api/policies/{policy.json()['id']}/rules",
        headers=admin_headers,
        json={"key": "annual_allowance", "value": 20},
    )
    assert rule.status_code == 200, rule.text
    applicable = client.get("/api/policies/applicable", headers=employee_headers)
    assert applicable.status_code == 200, applicable.text
    assert any(item["id"] == policy.json()["id"] for item in applicable.json())

    expense_policy = client.post(
        "/api/policies",
        headers=admin_headers,
        json={"name": "Expense cap", "process": "expense", "department": "General"},
    )
    assert expense_policy.status_code == 200
    expense_rule = client.post(
        f"/api/policies/{expense_policy.json()['id']}/rules",
        headers=admin_headers,
        json={"key": "maximum_claim_amount", "value": 100},
    )
    assert expense_rule.status_code == 200
    too_large_claim = client.post(
        "/api/expenses/claims",
        headers=employee_headers,
        json={"category": "Travel", "amount": 101, "currency": "USD", "description": "Trip", "expense_date": "2026-09-27"},
    )
    assert too_large_claim.status_code == 422

    calendar = client.post(
        "/api/holidays/calendars",
        headers=admin_headers,
        json={"name": "General calendar", "department": "General"},
    )
    assert calendar.status_code == 201, calendar.text
    mapping = client.post(
        f"/api/holidays/calendars/{calendar.json()['id']}/assignments",
        headers=admin_headers,
        json={"user_id": employee["id"]},
    )
    assert mapping.status_code == 201, mapping.text
    holiday = client.post(
        "/api/holidays",
        headers=admin_headers,
        json={"calendar_id": calendar.json()["id"], "name": "Org holiday", "date": "2026-10-06"},
    )
    assert holiday.status_code == 201, holiday.text
    assert client.get("/api/holidays/mine", headers=employee_headers).json()[0]["name"] == "Org holiday"

    leave = client.post(
        "/api/leave/applications",
        headers=employee_headers,
        json={"leave_type": "Annual", "start_date": "2026-10-05", "end_date": "2026-10-07", "reason": "Personal"},
    )
    assert leave.status_code == 201, leave.text
    assert leave.json()["calendar_days"] == 3
    assert leave.json()["chargeable_days"] == 2


def test_payroll_preview_approval_and_private_payslip():
    org_name = "Payroll Workflow Organization"
    admin = _signup("payroll-admin@example.com", "admin", org_name)
    employee = _signup("payroll-employee@example.com", "employee", org_name)
    admin_headers = {"Authorization": f"Bearer {_token(admin['email'])}"}
    employee_headers = {"Authorization": f"Bearer {_token(employee['email'])}"}

    employee_record = next(
        item for item in client.get("/api/employees/", headers=admin_headers).json()["items"]
        if item["email"] == employee["email"]
    )
    component = client.post(
        "/api/payroll/components",
        headers=admin_headers,
        json={"name": "Housing allowance", "kind": "earning", "calculation": "fixed", "value": 1000},
    )
    assert component.status_code == 201, component.text
    structure = client.post(
        "/api/payroll/structures",
        headers=admin_headers,
        json={"employee_id": employee_record["id"], "base_salary": 5000, "component_ids": [component.json()["id"]]},
    )
    assert structure.status_code == 201, structure.text
    pf_rule = client.post(
        "/api/payroll/deduction-rules",
        headers=admin_headers,
        json={"name": "Configured PF", "kind": "pf", "employee_rate": 12, "employer_rate": 12},
    )
    assert pf_rule.status_code == 201, pf_rule.text
    overtime_rule = client.post(
        "/api/overtime/rules",
        headers=admin_headers,
        json={"name": "Approved overtime", "rate_multiplier": 2, "standard_hours_per_day": 8},
    )
    assert overtime_rule.status_code == 201, overtime_rule.text
    overtime_request = client.post(
        "/api/overtime/requests",
        headers=employee_headers,
        json={"work_date": "2026-09-15", "minutes": 60, "reason": "Release support"},
    )
    assert overtime_request.status_code == 201, overtime_request.text
    overtime_decision = client.patch(
        f"/api/overtime/requests/{overtime_request.json()['id']}/decision",
        headers=admin_headers,
        json={"status": "approved"},
    )
    assert overtime_decision.status_code == 200, overtime_decision.text

    run = client.post(
        "/api/payroll/runs",
        headers=admin_headers,
        json={"period_start": "2026-09-01", "period_end": "2026-09-30"},
    )
    assert run.status_code == 201, run.text
    assert run.json()["status"] == "preview"
    payslip = run.json()["payslips"][0]
    assert payslip["gross_pay"] > 6000
    assert payslip["overtime_minutes"] == 60
    assert payslip["deductions"]["PF"] == round(payslip["gross_pay"] * 0.12, 2)
    assert payslip["net_pay"] == round(payslip["gross_pay"] - payslip["total_deductions"], 2)
    assert client.get("/api/payroll/runs", headers=employee_headers).status_code == 403

    approval = client.patch(f"/api/payroll/runs/{run.json()['id']}/approve", headers=admin_headers)
    assert approval.status_code == 200, approval.text
    finalized = client.patch(f"/api/payroll/runs/{run.json()['id']}/finalize", headers=admin_headers)
    assert finalized.status_code == 200, finalized.text
    employee_payslips = client.get("/api/payroll/payslips", headers=employee_headers)
    assert employee_payslips.status_code == 200
    assert len(employee_payslips.json()) == 1
    download = client.get(f"/api/payroll/payslips/{payslip['id']}/download", headers=employee_headers)
    assert download.status_code == 200
    assert f"Net pay,{payslip['net_pay']}" in download.text
    hr_summary = client.get("/api/payroll/summary", headers=admin_headers)
    assert hr_summary.status_code == 200
    assert hr_summary.json()["employee_id"] is None
    assert hr_summary.json()["gross_pay"] == run.json()["total_gross"]


def test_recruitment_requisition_candidate_interview_and_offer():
    org_name = "Recruitment Workflow Organization"
    admin = _signup("recruitment-admin@example.com", "admin", org_name)
    interviewer = _signup("recruitment-interviewer@example.com", "manager", org_name)
    admin_headers = {"Authorization": f"Bearer {_token(admin['email'])}"}
    interviewer_headers = {"Authorization": f"Bearer {_token(interviewer['email'])}"}

    requisition = client.post(
        "/api/recruitment/requisitions",
        headers=admin_headers,
        json={"title": "People Analyst", "department": "People", "openings": 1, "requirements": ["Reporting"]},
    )
    assert requisition.status_code == 201, requisition.text
    decision = client.patch(
        f"/api/recruitment/requisitions/{requisition.json()['id']}/decision",
        headers=admin_headers,
        json={"status": "approved"},
    )
    assert decision.status_code == 200

    job = client.post(
        "/api/recruitment/jobs",
        headers=admin_headers,
        json={"title": "People Analyst", "department": "People", "open_positions": 1},
    )
    assert job.status_code == 201, job.text
    application = client.post(
        "/api/recruitment/applicants",
        headers=admin_headers,
        json={"job_id": job.json()["id"], "candidate_name": "Casey Candidate", "email": "casey@example.com", "skills": ["analytics"]},
    )
    assert application.status_code == 201, application.text
    assert application.json()["candidate"]["skills"] == ["analytics"]

    interview = client.post(
        "/api/recruitment/interviews",
        headers=admin_headers,
        json={"application_id": application.json()["id"], "scheduled_at": "2026-10-10T10:00:00+00:00", "panel_user_ids": [interviewer["id"]]},
    )
    assert interview.status_code == 201, interview.text
    feedback = client.post(
        f"/api/recruitment/interviews/{interview.json()['id']}/feedback",
        headers=interviewer_headers,
        json={"rating": 5, "recommendation": "strong_yes", "notes": "Good role fit"},
    )
    assert feedback.status_code == 201, feedback.text

    offer = client.post(
        "/api/recruitment/offers",
        headers=admin_headers,
        json={"application_id": application.json()["id"], "salary": 90000, "expires_at": "2026-10-20T00:00:00+00:00"},
    )
    assert offer.status_code == 201, offer.text
    accepted = client.patch(
        f"/api/recruitment/offers/{offer.json()['id']}/decision",
        headers=admin_headers,
        json={"status": "accepted"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"


def test_onboarding_checklist_task_progress_and_asset_custody():
    org_name = "Onboarding Workflow Organization"
    admin = _signup("onboarding-admin@example.com", "admin", org_name)
    employee = _signup("onboarding-employee@example.com", "employee", org_name)
    admin_headers = {"Authorization": f"Bearer {_token(admin['email'])}"}
    employee_headers = {"Authorization": f"Bearer {_token(employee['email'])}"}

    checklist = client.post(
        "/api/onboarding/checklists",
        headers=admin_headers,
        json={"title": "Starter checklist", "tasks": [{"title": "Equipment setup", "days_from_start": 2}, {"title": "Policy review", "days_from_start": 5}]},
    )
    assert checklist.status_code == 201, checklist.text
    assigned = client.post(
        f"/api/onboarding/checklists/{checklist.json()['id']}/assign",
        headers=admin_headers,
        json={"assignee": employee["email"], "start_date": "2026-10-01"},
    )
    assert assigned.status_code == 201, assigned.text
    employee_tasks = client.get("/api/onboarding/tasks", headers=employee_headers)
    assert len(employee_tasks.json()) == 2
    completed = client.patch(
        f"/api/onboarding/tasks/{employee_tasks.json()[0]['id']}",
        headers=employee_headers,
        json={"status": "completed"},
    )
    assert completed.status_code == 200
    dashboard = client.get("/api/onboarding/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["completed_tasks"] >= 1

    asset = client.post("/api/onboarding/assets", headers=admin_headers, json={"name": "Laptop", "serial_number": "LT-101"})
    assert asset.status_code == 201, asset.text
    assignment = client.post(
        f"/api/onboarding/assets/{asset.json()['id']}/assign",
        headers=admin_headers,
        json={"user_id": employee["id"]},
    )
    assert assignment.status_code == 200, assignment.text
    acknowledged = client.patch(f"/api/onboarding/assets/{asset.json()['id']}/acknowledge", headers=employee_headers)
    assert acknowledged.status_code == 200
    returned = client.patch(f"/api/onboarding/assets/{asset.json()['id']}/return", headers=admin_headers)
    assert returned.status_code == 200
    assert returned.json()["status"] == "available"


def test_performance_goals_review_cycle_and_manager_review():
    org_name = "Performance Workflow Organization"
    admin = _signup("performance-admin@example.com", "admin", org_name)
    employee = _signup("performance-employee@example.com", "employee", org_name)
    admin_headers = {"Authorization": f"Bearer {_token(admin['email'])}"}
    employee_headers = {"Authorization": f"Bearer {_token(employee['email'])}"}

    cycle = client.post(
        "/api/performance/cycles",
        headers=admin_headers,
        json={"name": "2026 Annual Review", "start_date": "2026-10-01", "end_date": "2026-12-31"},
    )
    assert cycle.status_code == 201, cycle.text
    goal = client.post(
        "/api/performance/goals",
        headers=employee_headers,
        json={"title": "Complete training", "due_date": "2026-12-01"},
    )
    assert goal.status_code == 201, goal.text
    progress = client.patch(
        f"/api/performance/goals/{goal.json()['id']}",
        headers=employee_headers,
        json={"progress": 65},
    )
    assert progress.status_code == 200
    assert progress.json()["progress"] == 65

    self_review = client.post(
        "/api/performance/reviews",
        headers=employee_headers,
        json={"cycle_id": cycle.json()["id"], "review_type": "self", "rating": 4, "notes": "Delivered agreed goals"},
    )
    assert self_review.status_code == 201, self_review.text
    manager_review = client.post(
        "/api/performance/reviews",
        headers=admin_headers,
        json={"cycle_id": cycle.json()["id"], "review_type": "manager", "employee_email": employee["email"], "rating": 5, "notes": "Strong results"},
    )
    assert manager_review.status_code == 201, manager_review.text
    assert len(client.get("/api/performance/reviews", headers=employee_headers).json()) == 2


def test_ai_assistant_uses_scoped_records_and_configured_policies():
    org_name = "AI Workflow Organization"
    admin = _signup("ai-admin@example.com", "admin", org_name)
    employee = _signup("ai-employee@example.com", "employee", org_name)
    manager = _signup("ai-manager@example.com", "manager", org_name)
    admin_headers = {"Authorization": f"Bearer {_token(admin['email'])}"}
    employee_headers = {"Authorization": f"Bearer {_token(employee['email'])}"}
    manager_headers = {"Authorization": f"Bearer {_token(manager['email'])}"}
    expense = client.post(
        "/api/expenses/claims",
        headers=employee_headers,
        json={"category": "Travel", "amount": 85, "currency": "USD", "description": "Customer visit", "expense_date": "2026-09-20"},
    )
    assert expense.status_code == 201
    answer = client.post("/api/ai/assistant", headers=employee_headers, json={"prompt": "What is the status of my expense claims?"})
    assert answer.status_code == 200, answer.text
    assert "1 awaiting review" in answer.json()["summary"]
    assert answer.json()["sources"][0]["module"] == "expenses"
    manager_payroll = client.post("/api/ai/assistant", headers=manager_headers, json={"prompt": "Show payroll salary for my team"})
    assert "restricted" in manager_payroll.json()["summary"]

    unconfigured = client.post("/api/ai/policy-assistant", headers=employee_headers, json={"question": "What is the leave policy?"})
    assert "will not infer or invent" in unconfigured.json()["answer"]
    policy = client.post("/api/policies", headers=admin_headers, json={"name": "Annual leave", "process": "leave"})
    rule = client.post(
        f"/api/policies/{policy.json()['id']}/rules",
        headers=admin_headers,
        json={"key": "max_consecutive_days", "value": 10},
    )
    assert rule.status_code == 200
    grounded = client.post("/api/ai/policy-assistant", headers=employee_headers, json={"question": "What is the leave policy?"})
    assert grounded.status_code == 200
    assert "max_consecutive_days = 10" in grounded.json()["answer"]

    proposal = client.post("/api/ai/actions/propose", headers=admin_headers, json={"action_type": "report", "payload": {"report_type": "workforce"}})
    assert proposal.status_code == 201
    confirmed = client.post(f"/api/ai/actions/{proposal.json()['id']}/confirm", headers=admin_headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["action"]["status"] == "confirmed"


def test_targeted_announcement_publish_and_read_state():
    org_name = "Announcement Workflow Organization"
    admin = _signup("announcement-admin@example.com", "admin", org_name)
    employee = _signup("announcement-employee@example.com", "employee", org_name)
    other_employee = _signup("announcement-other@example.com", "employee", org_name)
    admin_headers = {"Authorization": f"Bearer {_token(admin['email'])}"}
    employee_headers = {"Authorization": f"Bearer {_token(employee['email'])}"}
    other_headers = {"Authorization": f"Bearer {_token(other_employee['email'])}"}

    announcement = client.post(
        "/api/announcements",
        headers=admin_headers,
        json={"title": "Office closure", "body": "The office will be closed Friday.", "audience": "employees", "target_user_ids": [employee["id"]], "publish": True},
    )
    assert announcement.status_code == 201, announcement.text
    employee_announcements = client.get("/api/announcements", headers=employee_headers)
    assert len(employee_announcements.json()) == 1
    assert employee_announcements.json()[0]["read"] is False
    assert client.get("/api/announcements", headers=other_headers).json() == []

    marked = client.patch(f"/api/announcements/{announcement.json()['id']}/read", headers=employee_headers)
    assert marked.status_code == 200
    assert client.get("/api/announcements", headers=employee_headers).json()[0]["read"] is True