# AI-Powered HRMS

This project is a working HR management system built with a FastAPI backend and a React + TypeScript frontend. It includes organization-aware authentication, employee management, leave approval, expense claims, and payroll summary flows.

## Stack

- Backend: Python, FastAPI
- Frontend: React, TypeScript, Vite
- Data layer: in-memory repository for local development
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
