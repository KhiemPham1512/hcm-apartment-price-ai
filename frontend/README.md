# Frontend — TV5

React + TypeScript + Vite client for the existing FastAPI contract. This folder is owned by TV5; it does not modify backend, ML, shared schema, root CI, or team documentation.

## Run locally (PowerShell)

From the repository root:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite development proxy forwards `/api` and `/health` to `http://127.0.0.1:8000`. Start the backend separately using the root README. To use another API origin, set `VITE_API_BASE_URL` in `.env` (for example `http://127.0.0.1:8000`).

## Build and browser tests

```powershell
npm run build
npx playwright install chromium
npm run test:e2e
```

Playwright fixtures are synthetic and explicitly test-only. They are never used as a fallback in the running application. Tests cover valid request payload, API-driven field labels/required flags/numeric bounds, unavailable model, stale metadata, API 422/503, report metrics and report failures, mobile layout, and network failure after a successful prediction. The committed screenshot/report are historical evidence only; rerun the commands above before claiming a current pass.

## Contract behavior

- Loads `GET /api/v1/metadata` first and builds the supported-area dropdown from `supported_districts`.
- Builds the supported numeric form fields from `feature_schema.properties`, uses the API title/description/required list and numeric bounds when present, and keeps the district selector sourced from `supported_districts`.
- Optional numeric fields left blank are sent as JSON `null`; integer fields use integer input steps.
- Calls `POST /api/v1/predictions` only when `serving_status` is `ready`.
- Renders the API's total price, price per m², data dates, source snapshot, area basis, schema/dataset/model identifiers and warnings without recalculating model metrics.
- `GET /api/v1/report` is optional and its response is rendered as returned by the API.
- 422, 503, stale and network failures are shown as messages. No cached/mock price is shown after a failure.

No prediction is available until the backend has a valid approved and fresh model. This is expected for the supplied repository snapshot.
