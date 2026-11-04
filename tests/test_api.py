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
