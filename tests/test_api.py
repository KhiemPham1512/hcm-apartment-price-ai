import hashlib
from datetime import timedelta

import joblib
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app import create_app
from backend.service import Manifest, load_approved
from ml.schema import ApartmentFeatures

VALID = {"area_m2": 70, "district_code": "fixture_0", "bedrooms": 2}


def test_api_is_honest_without_model():
    client = TestClient(create_app())
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 503
    assert client.get("/api/v1/metadata").json()["serving_status"] == "unavailable"
    result = client.post("/api/v1/predictions", json=VALID)
    assert result.status_code == 503
    assert result.json()["error"]["code"] == "model_unavailable"
    assert "predicted_price_vnd" not in result.json()


def test_api_and_offline_predictions_match(serving_model, now):
    client = TestClient(create_app(serving_model, lambda: now))
    result = client.post("/api/v1/predictions", json=VALID)
    assert result.status_code == 200
    data = result.json()
    offline = serving_model.predict(ApartmentFeatures(**VALID), now)
    assert data["predicted_price_vnd"] == pytest.approx(offline["predicted_price_vnd"])
    assert data["predicted_price_per_m2_vnd"] == pytest.approx(
        data["predicted_price_vnd"] / VALID["area_m2"]
    )
    assert "confidence" not in data
    assert "optional_features_missing" in data["warnings"]
    assert data["request_id"]


@pytest.mark.parametrize(
    "change",
    [
        {"area_m2": True},
        {"area_m2": "70"},
        {"area_m2": -1},
        {"bedrooms": 1.5},
        {"asking_price_vnd": 1000},
        {"model_path": "../private"},
    ],
)
def test_strict_requests_share_error_envelope(change):
    response = TestClient(create_app()).post("/api/v1/predictions", json=VALID | change)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert "input" not in response.json()["error"]["details"]


def test_unknown_district_rejected_even_if_encoder_can_predict(serving_model, now):
    client = TestClient(create_app(serving_model, lambda: now))
    response = client.post("/api/v1/predictions", json=VALID | {"district_code": "unknown"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_district"


def test_freshness_boundary_and_stale_metadata(serving_model):
    boundary = serving_model.manifest.data_as_of + timedelta(days=14)
    ready = TestClient(create_app(serving_model, lambda: boundary))
    assert ready.get("/health/ready").status_code == 200
    stale = TestClient(create_app(serving_model, lambda: boundary + timedelta(seconds=1)))
    assert stale.get("/health/ready").status_code == 503
    assert stale.get("/api/v1/metadata").json()["serving_status"] == "stale"
    response = stale.post("/api/v1/predictions", json=VALID)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "stale_model"


def test_body_limit_and_media_type():
    client = TestClient(create_app())
    assert client.post("/api/v1/predictions", content="x").status_code == 415
    response = client.post(
        "/api/v1/predictions",
        content='{"x":"' + "x" * 17000 + '"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413


@pytest.mark.parametrize("price", [-1, float("nan"), float("inf")])
def test_bad_model_output_never_becomes_price(serving_model, now, price):
    class BadPipeline:
        def predict(self, frame):
            return [price]

    serving_model.pipeline = BadPipeline()
    response = TestClient(create_app(serving_model, lambda: now)).post(
        "/api/v1/predictions", json=VALID
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "prediction_unavailable"


def test_loader_rejects_synthetic_and_tampered_artifacts(tmp_path, serving_model):
    data = serving_model.manifest.model_dump(mode="json")
    with pytest.raises(ValidationError):
        Manifest.model_validate(data | {"data_kind": "synthetic"})
    joblib.dump(serving_model.pipeline, tmp_path / "pipeline.joblib")
    (tmp_path / "manifest.json").write_text(
        serving_model.manifest.model_dump_json(), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="checksum"):
        load_approved(tmp_path)
    data["pipeline_sha256"] = hashlib.sha256(
        (tmp_path / "pipeline.joblib").read_bytes()
    ).hexdigest()
    (tmp_path / "manifest.json").write_text(Manifest(**data).model_dump_json(), encoding="utf-8")
    loaded = load_approved(tmp_path)
    assert loaded.manifest.model_id == serving_model.manifest.model_id


def test_no_public_management_endpoints():
    client = TestClient(create_app())
    for path in ("/upload", "/api/v1/retrain", "/api/v1/models", "/data/raw", "/artifacts"):
        assert client.get(path).status_code == 404


def test_rate_limit_returns_retry_after(serving_model, now):
    client = TestClient(
        create_app(serving_model, lambda: now, rate_limit_capacity=2, rate_limit_per_minute=30)
    )
    assert client.post("/api/v1/predictions", json=VALID).status_code == 200
    assert client.post("/api/v1/predictions", json=VALID).status_code == 200
    limited = client.post("/api/v1/predictions", json=VALID)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert int(limited.headers["retry-after"]) >= 1
    assert limited.json()["error"]["request_id"]


def test_prediction_capacity_returns_429(serving_model, now):
    client = TestClient(create_app(serving_model, lambda: now, max_concurrent_predictions=0))
    response = client.post("/api/v1/predictions", json=VALID)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "prediction_capacity_exceeded"


def test_cors_does_not_allow_unknown_origin(serving_model, now):
    client = TestClient(create_app(serving_model, lambda: now))
    response = client.options(
        "/api/v1/predictions",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_wildcard_cors_is_rejected(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ValueError, match="Wildcard"):
        create_app()


def test_report_is_read_only_and_served_when_attached(serving_model, now):
    serving_model.report = {"run_id": "approved-run", "models": []}
    client = TestClient(create_app(serving_model, lambda: now))
    response = client.get("/api/v1/report")
    assert response.status_code == 200
    assert response.json()["run_id"] == "approved-run"


def test_openapi_exposes_expected_routes():
    schema = TestClient(create_app()).get("/openapi.json").json()
    paths = schema["paths"]
    assert set(paths) >= {
        "/health/live",
        "/health/ready",
        "/api/v1/metadata",
        "/api/v1/predictions",
        "/api/v1/report",
    }


def test_forwarded_for_is_trusted_only_from_declared_proxy(serving_model, now, monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/24")
    app = create_app(serving_model, lambda: now, rate_limit_capacity=1, rate_limit_per_minute=1)

    def post(peer, forwarded):
        client = TestClient(app, client=(peer, 5000))
        return client.post(
            "/api/v1/predictions", json=VALID, headers={"X-Forwarded-For": forwarded}
        ).status_code

    # An untrusted peer cannot dodge its bucket by spoofing the header.
    assert post("203.0.113.9", "198.51.100.1") == 200
    assert post("203.0.113.9", "198.51.100.2") == 429
    # A declared proxy: the forwarded client decides the bucket.
    assert post("10.0.0.5", "198.51.100.3") == 200
    assert post("10.0.0.5", "198.51.100.4") == 200
    assert post("10.0.0.5", "198.51.100.3") == 429


def test_invalid_proxy_cidr_is_rejected(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "not-a-cidr")
    with pytest.raises(ValueError):
        create_app()


def test_over_budget_prediction_returns_503_without_a_price(serving_model, now):
    client = TestClient(create_app(serving_model, lambda: now, prediction_timeout_seconds=0))
    response = client.post("/api/v1/predictions", json=VALID)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "prediction_timeout"
    assert "predicted_price_vnd" not in response.json()


def test_configured_cors_origin_is_allowed(serving_model, now, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://demo.example, http://localhost:5173")
    client = TestClient(create_app(serving_model, lambda: now))
    headers = {"Access-Control-Request-Method": "POST"}
    allowed = client.options(
        "/api/v1/predictions", headers={"Origin": "https://demo.example", **headers}
    )
    assert allowed.headers["access-control-allow-origin"] == "https://demo.example"
    other = client.options(
        "/api/v1/predictions", headers={"Origin": "https://other.example", **headers}
    )
    assert "access-control-allow-origin" not in other.headers


def test_current_manifest_defaults_to_current_snapshot_and_ready(serving_model, now):
    assert serving_model.manifest.snapshot_kind == "current"
    meta = TestClient(create_app(serving_model, lambda: now)).get("/api/v1/metadata").json()
    assert meta["serving_status"] == "ready"
    assert meta["snapshot_kind"] == "current"
