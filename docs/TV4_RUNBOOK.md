# TV4 Backend/Serving — local runbook

## Scope and truthful serving status

The API is read-only. It does not expose upload, training, retraining, filesystem browsing,
raw-data access, artifact download, or model selection routes. Without a TV6-approved and
fresh artifact, `/health/ready` and prediction/report requests return HTTP 503. Do not create
or substitute a synthetic artifact to make the demo appear ready.

## Environment

- Python 3.12
- Install: `python -m venv .venv` then activate it, followed by
  `python -m pip install -e '.[dev]'`
- Optional environment variables:
  - `MODEL_DIR`: operator-controlled directory containing `manifest.json`,
    `pipeline.joblib`, and optional `report.json`.
  - `CORS_ORIGINS`: comma-separated exact browser origins; default is the two local Vite
    origins. Wildcard `*` is rejected.
  - `TRUSTED_PROXY_CIDRS`: comma-separated CIDRs of reverse proxies. Forwarded client IP
    headers are ignored unless the direct peer is in this list.

## Start and verify

```bash
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

OpenAPI: `http://127.0.0.1:8000/openapi.json`; Swagger: `http://127.0.0.1:8000/docs`.

```bash
curl -i http://127.0.0.1:8000/health/live
curl -i http://127.0.0.1:8000/health/ready
curl -i http://127.0.0.1:8000/api/v1/metadata
```

Expected with no approved artifact: liveness 200, readiness 503, metadata 200 with
`serving_status=unavailable`, predictions 503. Never interpret this as a failed API install.

## API contract

- `GET /health/live`: process liveness.
- `GET /health/ready`: approved model and freshness gate.
- `GET /api/v1/metadata`: schema and supported districts; remains available when stale.
- `POST /api/v1/predictions`: one strict JSON apartment record.
- `GET /api/v1/report`: approved aggregate evaluation report.

Example request (district code must be copied from metadata):

```json
{
  "area_m2": 70,
  "district_code": "<code-from-metadata>",
  "bedrooms": 2,
  "bathrooms": 2,
  "floor_level": null
}
```

All errors use `error.code`, `error.message`, `error.request_id`, and `error.details`.
`422` means invalid input/unsupported district; `429` means rate/capacity limit and may
include `Retry-After`; `503` means unavailable/stale/timeout. The client must not show mock
or cached prices as live estimates after an error.

## Security and operational limits

- JSON body max 16 KiB; one prediction per request.
- In-process token bucket: 5-request burst, refills at 30 requests/minute per client IP.
- In-process concurrent inference slots: 4 by default; excess returns 429.
- Prediction execution budget is 5 seconds by default. The API detects an over-budget
  synchronous inference after it returns and responds 503; Python threads cannot be safely
  force-killed. For a hard wall-clock kill in public deployment, run inference in a separately
  supervised worker/process with an external deadline. Do not claim hard cancellation here.
- Rate limiting and concurrency are per process, not shared across multiple workers/replicas.
  Put a trusted reverse proxy/API gateway in front of a public multi-worker deployment and
  configure `TRUSTED_PROXY_CIDRS` narrowly.
- CORS is an origin policy, not authentication. Public deployment requires HTTPS.
- Logs never include request bodies or raw feature values. Do not log seller PII or secrets.
- Joblib can execute code while loading. Only load artifacts from an operator-controlled,
  reviewed directory. SHA-256 detects tampering against the manifest but does not make an
  untrusted pickle safe.

## Tests

```bash
python -m pytest tests/test_api.py -q
python -m pytest -q
ruff check backend tests
```

## Release and rollback

TV6 owns approval. TV4 may smoke-test only the artifact supplied by TV6. Keep the previous
approved artifact directory immutable and retain its manifest/hash. Roll back by changing the
operator-controlled `MODEL_DIR` to a previously approved artifact that still passes the
freshness gate, then restart and verify readiness, metadata, and a controlled smoke prediction.
If no previously approved fresh artifact exists, leave predictions unavailable. No production
artifact or rollback is claimed by this runbook.
