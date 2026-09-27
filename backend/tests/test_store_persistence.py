from app.repositories.store import InMemoryStore


def test_store_records_survive_store_reinitialization(tmp_path):
    database_path = str(tmp_path / "hrms.sqlite3")
    first_store = InMemoryStore(database_path)
    organization = first_store.create_organization("Persistent Organization")
    user = first_store.create_user({
        "email": "persist@example.com",
        "password_hash": "hashed-password",
        "first_name": "Persistent",
        "last_name": "User",
        "role": "employee",
        "org_id": organization["id"],
    })
    employee = first_store.create_employee({
        "org_id": organization["id"],
        "email": user["email"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
    })
    record = first_store.create_module_record("document_categories", {
        "org_id": organization["id"],
        "name": "Identity proof",
        "required": True,
    })
    first_store.add_audit_log(user["id"], organization["id"], "test.persisted", {"record_id": record["id"]})

    restored_store = InMemoryStore(database_path)

    assert restored_store.get_organization_by_id(organization["id"]) == organization
    assert restored_store.get_user_by_email(user["email"]) == user
    assert restored_store.get_employee_by_user_email(organization["id"], user["email"]) == employee
    assert restored_store.get_module_record("document_categories", record["id"], organization["id"]) == record
    assert restored_store.audit_logs[0]["event"] == "test.persisted"
