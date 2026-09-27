from app.services.auth_service import AuthService

service = AuthService()

accounts = [
    {
        "email": "admin@demo.com",
        "password": "StrongPass123!",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "org_name": "Acme Corp",
    },
    {
        "email": "manager@demo.com",
        "password": "StrongPass123!",
        "first_name": "Manager",
        "last_name": "User",
        "role": "manager",
        "org_name": "Acme Corp",
    },
    {
        "email": "employee@demo.com",
        "password": "StrongPass123!",
        "first_name": "Employee",
        "last_name": "User",
        "role": "employee",
        "org_name": "Acme Corp",
    },
]

for account in accounts:
    try:
        service.signup(account)
        print(f"Created {account['email']}")
    except Exception as exc:  # pragma: no cover
        print(f"Skipped {account['email']}: {exc}")
