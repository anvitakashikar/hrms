from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import get_store
from app.routers.ai import router as ai_router
from app.routers.analytics import router as analytics_router
from app.routers.attendance import router as attendance_router
from app.routers.auth import router as auth_router
from app.routers.benefits import router as benefits_router
from app.routers.documents import router as documents_router
from app.routers.communications import router as communications_router
from app.routers.compliance import router as compliance_router
from app.routers.employees import router as employee_router
from app.routers.expenses import router as expense_router
from app.routers.exit_management import router as exit_router
from app.routers.holidays import router as holidays_router
from app.routers.leave import router as leave_router
from app.routers.lifecycle import router as lifecycle_router
from app.routers.onboarding import router as onboarding_router
from app.routers.overtime import router as overtime_router
from app.routers.organizations import router as organizations_router
from app.routers.notifications import router as notifications_router
from app.routers.policies import router as policies_router
from app.routers.payroll import router as payroll_router
from app.routers.performance import router as performance_router
from app.routers.recruitment import router as recruitment_router
from app.routers.self_service import router as self_service_router
from app.services.auth_service import AuthService

settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")


def seed_demo_data() -> None:
    store = get_store()
    if store.users:
        return

    service = AuthService()
    for account in [
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
    ]:
        try:
            service.signup(account)
        except HTTPException:
            pass


@app.on_event("startup")
def startup_event() -> None:
    seed_demo_data()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(organizations_router, prefix="/api/organizations", tags=["organizations"])
app.include_router(employee_router, prefix="/api/employees", tags=["employees"])
app.include_router(leave_router, prefix="/api/leave", tags=["leave"])
app.include_router(expense_router, prefix="/api/expenses", tags=["expenses"])
app.include_router(holidays_router, prefix="/api/holidays", tags=["holidays"])
app.include_router(policies_router, prefix="/api/policies", tags=["policies"])
app.include_router(payroll_router, prefix="/api/payroll", tags=["payroll"])
app.include_router(performance_router, prefix="/api/performance", tags=["performance"])
app.include_router(overtime_router, prefix="/api/overtime", tags=["overtime"])
app.include_router(lifecycle_router, prefix="/api", tags=["field-duty-letters-reports"])
app.include_router(exit_router, prefix="/api/exit", tags=["exit-management"])
app.include_router(attendance_router, prefix="/api/attendance", tags=["attendance"])
app.include_router(benefits_router, prefix="/api", tags=["benefits-tax"])
app.include_router(compliance_router, prefix="/api", tags=["compliance-privacy"])
app.include_router(onboarding_router, prefix="/api/onboarding", tags=["onboarding"])
app.include_router(recruitment_router, prefix="/api/recruitment", tags=["recruitment"])
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(communications_router, prefix="/api/announcements", tags=["announcements"])
app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])
app.include_router(ai_router, prefix="/api/ai", tags=["ai"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(self_service_router, prefix="/api/self-service", tags=["employee-self-service"])


@app.get("/api/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
