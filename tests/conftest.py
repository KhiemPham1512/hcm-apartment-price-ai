"""Synthetic data for technical tests only; no market accuracy claims."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from backend.service import Manifest, ServingModel
from ml.data import feature_frame, split_groups
from ml.models import make_model
from ml.schema import FEATURES


@pytest.fixture
def now():
    return datetime(2026, 11, 4, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def listings(now):
    rng = np.random.default_rng(42)
    n = 600
    area = rng.uniform(30, 150, n)
    return pd.DataFrame(
        {
            "area_m2": area,
            "district_code": [f"fixture_{i % 3}" for i in range(n)],
            "bedrooms": rng.integers(0, 5, n),
            "bathrooms": rng.integers(1, 4, n),
            "floor_level": rng.integers(1, 31, n),
            "asking_price_vnd": 1_000_000_000 + area * 20_000_000,
            "listing_id": [f"synthetic_listing_{i}" for i in range(n)],
            "source_id": "synthetic_test_source",
            "property_group_id": [f"synthetic_group_{i}" for i in range(n)],
            "published_at": now - timedelta(days=30),
            "price_observed_at": now - timedelta(days=1),
            "source_snapshot_at": now,
            "active_at_snapshot": True,
            "availability_evidence_id": "synthetic_fixture_not_market_evidence",
            "property_type": "apartment",
            "listing_type": "sale",
            "area_basis": "source_reported_unknown",
        }
    )


@pytest.fixture
def serving_model(listings, now):
    """Inject a test-only manifest; never write an approved market artifact."""
    train = split_groups(listings)["train"]
    model = make_model("linear").fit(feature_frame(train), train["asking_price_vnd"])
    observed = now - timedelta(days=1)
    manifest = Manifest(
        release_status="approved",
        data_kind="real",
        source_verified=True,
        schema_version="1",
        model_id="injected-test-only",
        run_id="test-only",
        dataset_version="synthetic-fixture-injected-not-released",
        pipeline_sha256="0" * 64,
        features=FEATURES,
        data_as_of=observed,
        data_latest_at=observed,
        source_snapshot_at=now,
        data_window_start=observed,
        data_window_end=observed,
        listing_window_start=now - timedelta(days=30),
        listing_window_end=now - timedelta(days=30),
        age_summary={
            "median_listing_age_days": 30,
            "median_price_age_days": 1,
            "computed_at": now.isoformat(),
        },
        area_basis="source_reported_unknown",
        supported_districts={f"fixture_{i}": f"Fixture {i}" for i in range(3)},
        training_ranges={"area_m2": (30, 150)},
        n_groups=600,
        test_n=90,
        test_rmse_vnd=1,
        baseline_test_rmse_vnd=2,
        test_r2=0.5,
        invalid_output_count=0,
        reviewers=["test-role-a", "test-role-b"],
    )
    return ServingModel(model, manifest)
