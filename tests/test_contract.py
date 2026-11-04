"""Guard the feature contract shared by ML, metadata and HTTP consumers."""

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from ml.schema import FEATURES, SCHEMA_VERSION, ApartmentFeatures


@pytest.mark.parametrize("with_model", [False, True])
def test_metadata_and_openapi_share_ml_feature_contract(with_model, serving_model, now):
    client = TestClient(create_app(serving_model if with_model else None, lambda: now))
    metadata = client.get("/api/v1/metadata").json()
    schema = ApartmentFeatures.model_json_schema()
    assert metadata["schema_version"] == SCHEMA_VERSION
    assert metadata["feature_schema"] == schema
    assert set(schema["properties"]) == set(FEATURES)

    document = client.get("/openapi.json").json()
    request = document["paths"]["/api/v1/predictions"]["post"]["requestBody"]
    reference = request["content"]["application/json"]["schema"]["$ref"]
    http_schema = document["components"]["schemas"][reference.rsplit("/", 1)[-1]]
    # OpenAPI omits null defaults; compare validation constraints, keeping
    # metadata's full schema (including defaults) checked above.
    expected = schema | {
        "properties": {
            name: {key: value for key, value in field.items() if (key, value) != ("default", None)}
            for name, field in schema["properties"].items()
        }
    }
    assert http_schema == expected
