# TV4 → TV5: API handoff

## Base URL

Local: `http://127.0.0.1:8000`. OpenAPI: `/openapi.json`; Swagger: `/docs`.

## Endpoints

| Method | Path | Meaning |
|---|---|---|
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | Approved model and freshness gate |
| GET | `/api/v1/metadata` | Schema, district codes, model/data metadata, serving status |
| POST | `/api/v1/predictions` | One apartment inference |
| GET | `/api/v1/report` | Approved aggregate evaluation report |

## Request

```json
{
  "area_m2": 70,
  "district_code": "<code-from-metadata>",
  "bedrooms": 2,
  "bathrooms": 2,
  "floor_level": null
}
```

`area_m2` is a strict finite number in [10, 500]. `district_code` must be a supported code from metadata. Optional room/floor fields accept integer 0–10 (floor 0–100) or null. Unknown fields, numeric strings and booleans in numeric fields are rejected. The example district code is a placeholder, not a real supported code.

## Successful response

The response includes `request_id`, `target=asking_sale_price`, `predicted_price_vnd`, `predicted_price_per_m2_vnd`, model/run/dataset/schema identifiers, data timestamps, `area_basis`, and warning codes. It does not include confidence or accuracy. No real market model is bundled, so the current repository correctly returns 503 for prediction until TV6 supplies an approved, fresh artifact.

## Error envelope

```json
{
  "error": {
    "code": "invalid_input",
    "message": "Dữ liệu đầu vào không hợp lệ.",
    "request_id": "opaque-id",
    "details": {}
  }
}
```

| HTTP | Codes |
|---|---|
| 413 | `request_too_large` |
| 415 | `unsupported_media_type` |
| 422 | `invalid_input`, `unsupported_district` |
| 429 | `rate_limited`, `prediction_capacity_exceeded` (includes `Retry-After`) |
| 500 | `internal_error` |
| 503 | `model_unavailable`, `stale_model`, `prediction_unavailable`, `prediction_timeout` |

## Frontend integration rules

1. Fetch metadata before constructing the district selector; do not hardcode district codes.
2. If `serving_status` is `unavailable` or `stale`, show a clear unavailable state; do not display mock/cached prices as live estimates.
3. Submit exactly the schema above. Do not send price labels, paths, model filenames, URLs or PII.
4. Render VND values and timestamps as returned. Preserve `request_id` when showing an error to support troubleshooting.
5. Handle 422 as input error, 429 as retry-later (respect `Retry-After`), and 503 as unavailable/stale/timeout. Do not retry indefinitely.

## Versioning and ownership

Schema source of truth: `ml/schema.py`. Backend implementation: `backend/app.py`, `backend/service.py`. A breaking contract change requires TV4 + TV5 review and updates to OpenAPI, tests, README and this handoff in the same change.
