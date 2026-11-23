"""Identifier columns are text: numeric-looking IDs must survive CSV loading unchanged."""

from datetime import datetime, timedelta, timezone

import pytest

from ml.data import build_release_dataset_card, load_current_csv
from ml.schema import DatasetCard

NUMERIC_IDS = {
    "source_id": "0042",
    "listing_id": "00123",
    "property_group_id": "007",
    "availability_evidence_id": "000777",
    "district_code": "001",
}


def fresh(listings):
    now = datetime.now(timezone.utc)
    return now, listings.assign(
        published_at=now - timedelta(days=30),
        price_observed_at=now - timedelta(days=1),
        source_snapshot_at=now,
    )


def test_numeric_looking_ids_keep_their_leading_zeros(tmp_path, listings):
    now, frame = fresh(listings)
    frame = frame.iloc[:40].copy()
    frame["listing_id"] = [f"{NUMERIC_IDS['listing_id'][:-2]}{i:02d}" for i in range(40)]
    frame["property_group_id"] = [f"00{i:03d}" for i in range(40)]
    frame["source_id"] = NUMERIC_IDS["source_id"]
    frame["availability_evidence_id"] = NUMERIC_IDS["availability_evidence_id"]
    frame["district_code"] = NUMERIC_IDS["district_code"]
    path = tmp_path / "numeric.csv"
    frame.to_csv(path, index=False)

    loaded = load_current_csv(path, now)

    assert set(loaded["source_id"]) == {"0042"}
    assert set(loaded["district_code"]) == {"001"}
    assert set(loaded["availability_evidence_id"]) == {"000777"}
    assert set(loaded["property_group_id"]) == {f"00{i:03d}" for i in range(40)}
    assert set(loaded["listing_id"]) == {f"001{i:02d}" for i in range(40)}


def test_release_card_refuses_an_audit_without_any_go_no_go(listings):
    card = DatasetCard(
        dataset_version="v",
        data_kind="real",
        license_reference="license",
        source_verified=True,
        geography_version="hcm_current_v1",
        grouping_version="g",
        district_labels={"d": "D"},
    )
    mapping = {"source": "s", "effective_date": "2025-01-01", "version": "1", "sha256": "a" * 64}
    kwargs = dict(
        raw_sha256="1" * 64,
        clean_sha256="2" * 64,
        source_owner="owner",
        source_revision="rev",
        mapping_metadata=mapping,
        audit_method="rule",
        prepared_by="TV1",
        reviewed_by="TV6",
        area_basis="source_reported_unknown",
        exposure_summary={"ready_for_new_release_test": True, "blockers": []},
        pre_demo_check={"status": "PASS", "blockers": []},
    )
    for audit in ({}, {"go_no_go": None}, {"go_no_go": "GO"}):
        with pytest.raises(ValueError, match="GO audit"):
            build_release_dataset_card(card, audit, **kwargs)
