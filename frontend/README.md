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

Playwright fixtures are synthetic and explicitly test-only. They are never used as a fallback in the running application. Tests cover valid request payload, unavailable model, stale metadata and an API 422 response.

## Contract behavior

- Loads `GET /api/v1/metadata` first and builds the supported-area dropdown from `supported_districts`.
- Uses `feature_schema` numeric bounds when present; optional fields left blank are sent as JSON `null`.
- Calls `POST /api/v1/predictions` only when `serving_status` is `ready`.
- Renders the API's total price, price per m², data date, area basis, dataset/model identifiers and warnings without recalculating model metrics.
- `GET /api/v1/report` is optional and its response is rendered as returned by the API.
- 422, 503, stale and network failures are shown as messages. No cached/mock price is shown after a failure.

No prediction is available until the backend has a valid approved and fresh model. This is expected for the supplied repository snapshot.
