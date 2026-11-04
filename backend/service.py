"""A trusted local artifact is required before market predictions can be served."""

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ml.schema import FEATURES, SERVING_MAX_AGE_DAYS, ApartmentFeatures


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    release_status: Literal["approved"]
    data_kind: Literal["real"]
    source_verified: Literal[True]
    schema_version: Literal["1"]
    model_id: str
    run_id: str
    dataset_version: str
    pipeline_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    features: list[str]
    data_as_of: datetime
    data_latest_at: datetime
    source_snapshot_at: datetime
    data_window_start: datetime
    data_window_end: datetime
    listing_window_start: datetime
    listing_window_end: datetime
    age_summary: dict
    area_basis: str
    supported_districts: dict[str, str]
    training_ranges: dict[str, tuple[float, float]]
    n_groups: int = Field(ge=500)
    test_n: int = Field(ge=75)
    test_rmse_vnd: float = Field(ge=0, allow_inf_nan=False)
    baseline_test_rmse_vnd: float = Field(gt=0, allow_inf_nan=False)
    test_r2: float = Field(gt=0, allow_inf_nan=False)
    invalid_output_count: Literal[0]
    reviewers: list[str] = Field(min_length=2)

    @field_validator(
        "data_as_of",
        "data_latest_at",
        "source_snapshot_at",
        "data_window_start",
        "data_window_end",
        "listing_window_start",
        "listing_window_end",
    )
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timezone required")
        return value

    @model_validator(mode="after")
    def release_evidence(self):
        if self.features != FEATURES:
            raise ValueError("Feature contract mismatch")
        if not self.data_as_of <= self.data_latest_at <= self.source_snapshot_at:
            raise ValueError("Invalid observation chronology")
        if self.data_window_start != self.data_as_of or (
            self.data_window_end != self.data_latest_at
        ):
            raise ValueError("Observation window mismatch")
        if self.test_rmse_vnd >= self.baseline_test_rmse_vnd:
            raise ValueError("Candidate did not beat baseline")
        if len(set(self.reviewers)) < 2:
            raise ValueError("Distinct operational reviewers required")
        if not self.supported_districts:
            raise ValueError("No supported districts")
        return self


class ServingError(Exception):
    def __init__(self, code: str, message: str, status: int = 503, details=None):
        self.code, self.message, self.status = code, message, status
        self.details = details or {}


@dataclass
class ServingModel:
    pipeline: object
    manifest: Manifest
    report: dict | None = None

    def require_ready(self, now: datetime):
        if self.manifest.source_snapshot_at > now:
            raise ServingError("model_unavailable", "Metadata thời gian không hợp lệ.")
        if now - self.manifest.data_as_of > timedelta(days=SERVING_MAX_AGE_DAYS):
            raise ServingError(
                "stale_model",
                "Dữ liệu của mô hình đã quá hạn cập nhật.",
                details={"data_as_of": self.manifest.data_as_of.isoformat()},
            )

    def metadata(self, now: datetime) -> dict:
        try:
            self.require_ready(now)
            status = "ready"
        except ServingError as exc:
            status = "stale" if exc.code == "stale_model" else "unavailable"
        data = self.manifest.model_dump(mode="json")
        public = {
            key: value
            for key, value in data.items()
            if key
            in {
                "schema_version",
                "model_id",
                "run_id",
                "dataset_version",
                "data_as_of",
                "data_latest_at",
                "source_snapshot_at",
                "data_window_start",
                "data_window_end",
                "listing_window_start",
                "listing_window_end",
                "age_summary",
                "area_basis",
                "training_ranges",
            }
        }
        public["supported_districts"] = [
            {"code": code, "label": label}
            for code, label in sorted(self.manifest.supported_districts.items())
        ]
        public["feature_schema"] = ApartmentFeatures.model_json_schema()
        public["serving_status"] = status
        return public

    def predict(self, features: ApartmentFeatures, now: datetime) -> dict:
        self.require_ready(now)
        if features.district_code not in self.manifest.supported_districts:
            raise ServingError("unsupported_district", "Khu vực chưa được hỗ trợ.", 422)
        row = features.model_dump()
        warnings = []
        if any(value is None for value in row.values()):
            warnings.append("optional_features_missing")
        for key, limits in self.manifest.training_ranges.items():
            value = row.get(key)
            if value is not None and not limits[0] <= value <= limits[1]:
                warnings.append("outside_training_range")
                break
        try:
            price = float(self.pipeline.predict(pd.DataFrame([row], columns=FEATURES))[0])
        except Exception as exc:
            raise ServingError("prediction_unavailable", "Không thể tạo ước tính.") from exc
        if not math.isfinite(price) or price <= 0:
            raise ServingError("prediction_unavailable", "Kết quả mô hình không hợp lệ.")
        response = self.metadata(now)
        for key in ("supported_districts", "feature_schema", "training_ranges", "serving_status"):
            response.pop(key)
        return {
            **response,
            "target": "asking_sale_price",
            "predicted_price_vnd": price,
            "predicted_price_per_m2_vnd": price / features.area_m2,
            "warnings": warnings,
        }


def load_approved(directory: Path) -> ServingModel:
    """Only for an operator-configured trusted folder, never an HTTP input path."""
    manifest = Manifest.model_validate_json(
        (directory / "manifest.json").read_text(encoding="utf-8")
    )
    pipeline_path = directory / "pipeline.joblib"
    if hashlib.sha256(pipeline_path.read_bytes()).hexdigest() != manifest.pipeline_sha256:
        raise ValueError("Artifact checksum mismatch")
    report_path = directory / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
    return ServingModel(joblib.load(pipeline_path), manifest, report)
