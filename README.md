# ALLOCAT

ALLOCAT is a local, modular resource allocation system. The repository contains a
FastAPI backend and a React frontend. Cloud deployment is intentionally out of scope.

## Prerequisites

- Python 3.11+
- Node.js 20+
- MySQL 8+ (or SQLite for local tests)

## Local setup

1. Copy `.env.example` to `.env` and replace every development placeholder.
   Never commit real passwords or JWT secrets.
2. Create the database and seed it:

   ```sql
   SOURCE allocat.sql;
   ```

3. Start the API:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r backend\requirements.txt
   uvicorn backend.app.main:app --reload
   ```

   The API is available at `http://localhost:8000` and its OpenAPI document at
   `http://localhost:8000/docs`.

4. Start the frontend in another terminal:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Vite serves the UI at `http://localhost:5173`.

## Demo accounts

The SQL seed creates roles and a non-production administrator account only when
`ADMIN_SEED_PASSWORD` is supplied by the operator. Use a locally generated
password; do not copy passwords from chat or commit them to the repository.

## Testing

```powershell
pytest backend\tests --cov=backend\app --cov-fail-under=80
cd frontend
npm test -- --runInBand --coverage
npm run build
```

The backend uses MySQL in production and supports a SQLite URL for isolated tests.
Notifications are queued with FastAPI background tasks and logged locally; SMTP is
optional and failures are reported without blocking reservation requests.

## Project layout

- `backend/app`: modular API domains, models, services, and configuration
- `backend/tests`: API and security tests
- `frontend/src`: React pages, auth state, API client, and shared components
- `allocat.sql`: MySQL schema and safe role seed data
- `.github/workflows/ci-cd.yml`: test/build workflow and main-branch package job
