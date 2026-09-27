# AI-Powered HRMS

This project is an HR management system built with a FastAPI backend and a React + TypeScript frontend. Implemented workflows include organization-aware authentication, employee records, documents, attendance/location, leave, expenses/receipt extraction, payroll/statutory contributions, recruitment/resume extraction, onboarding/assets, performance, policies, holidays, announcements, notifications, compliance/privacy, exit processing, and HR assistance.

## Stack

- Backend: Python, FastAPI
- Frontend: React, TypeScript, Vite
- Data layer: SQLite-backed repository with organization-scoped records
- File storage: private local uploads under `backend/private_uploads/`
- Auth: JWT bearer tokens with org-scoped access

## Project structure

- backend/: FastAPI app and tests
- frontend/: React dashboard and client UI

## Run backend

```bash
cd backend
python -m venv .venv
python -m pip install -r requirements.txt
set PYTHONPATH=.
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

By default, records persist in `backend/data/hrms.sqlite3`. Set `HRMS_DB_PATH` to choose another SQLite database path. Tests use an isolated in-memory database. Uploaded employee documents are stored separately under `backend/private_uploads/` and are served only through authenticated download routes.

PDF, DOCX, and text extraction use the declared Python dependencies. Image OCR additionally requires a Tesseract executable on the host; set `HRMS_TESSERACT_CMD` if it is not available on `PATH`.

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

## Demo login

Use the seeded demo flow from the UI or call the auth endpoints:

- Email: admin@demo.com
- Password: StrongPass123!

## API overview

- /api/auth/signup
- /api/auth/login
- /api/auth/me
- /api/employees/
- /api/leave/applications
- /api/expenses/claims
- /api/payroll/summary
- /api/documents
- /api/attendance
- /api/holidays
- /api/policies
- /api/recruitment
- /api/onboarding
- /api/performance
- /api/announcements
- /api/notifications
- /api/ai
- /api/analytics
- /api/overtime
- /api/statutory
- /api/tax
- /api/insurance
- /api/posh
- /api/privacy
- /api/duty-requests
- /api/letters
- /api/signatures
- /api/reports
- /api/exit
- /api/self-service
- /api/health

## Validation

The project is validated with `pytest` and a frontend production build.

```bash
cd backend
set PYTHONPATH=.
python -m pytest -q

cd ../frontend
npm run build
```
