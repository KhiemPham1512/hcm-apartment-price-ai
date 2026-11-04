"""Executable feature contract shared by training and HTTP."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1"
NUMERIC_FEATURES = ["area_m2", "bedrooms", "bathrooms", "floor_level"]
CATEGORICAL_FEATURES = ["district_code"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
RECENT_WINDOW_DAYS = 90
PUBLICATION_MAX_AGE_DAYS = 7
SERVING_MAX_AGE_DAYS = 14
MIN_DISTRICT_GROUPS = 20

Area = Annotated[float, Field(strict=True, ge=10, le=500, allow_inf_nan=False)]
RoomCount = Annotated[int, Field(strict=True, ge=0, le=10)]
Floor = Annotated[int, Field(strict=True, ge=0, le=100)]


class ApartmentFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area_m2: Area
    district_code: Annotated[str, Field(strict=True, min_length=1, max_length=80)]
    bedrooms: RoomCount | None = None
    bathrooms: RoomCount | None = None
    floor_level: Floor | None = None


class Listing(ApartmentFeatures):
    listing_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    property_group_id: str = Field(min_length=1)
    published_at: datetime
    price_observed_at: datetime
    source_snapshot_at: datetime
    active_at_snapshot: Literal[True]
    availability_evidence_id: str = Field(min_length=1)
    asking_price_vnd: float = Field(strict=True, gt=0, allow_inf_nan=False)
    property_type: Literal["apartment"]
    listing_type: Literal["sale"]
    area_basis: str = Field(min_length=1)

    @field_validator("published_at", "price_observed_at", "source_snapshot_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timezone is required")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def chronological(self):
        if not self.published_at <= self.price_observed_at <= self.source_snapshot_at:
            raise ValueError("published_at <= price_observed_at <= source_snapshot_at required")
        return self

    def check_current(self, now: datetime) -> None:
        if self.source_snapshot_at > now:
            raise ValueError("Future snapshot")
        if now - self.source_snapshot_at > timedelta(days=PUBLICATION_MAX_AGE_DAYS):
            raise ValueError("Snapshot is too old for publication")
        if now - self.price_observed_at > timedelta(days=PUBLICATION_MAX_AGE_DAYS):
            raise ValueError("Observed price is too old for publication")
        if self.source_snapshot_at - self.published_at > timedelta(days=RECENT_WINDOW_DAYS):
            raise ValueError("Listing exceeds recent window")


class DatasetCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version: str = Field(min_length=1)
    data_kind: Literal["real", "synthetic"]
    license_reference: str = Field(min_length=1)
    source_verified: bool = False
    geography_version: Literal["hcm_current_v1"]
    grouping_version: str = Field(min_length=1)
    district_labels: dict[str, str]
