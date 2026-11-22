"""TV1-07..10 lifecycle tests: refresh shift, registry exposure, pre-demo check, release card."""

import json
import subprocess
import sys
from datetime import timedelta

import pandas as pd
import pytest

from ml.data import (
    audit_registry_exposure,
    build_dataset_audit,
    build_refresh_report,
    build_release_dataset_card,
    export_unexposed_test_candidates,
    verify_pre_demo_readiness,
)
from ml.registry import initialize as init_registry
from ml.registry import record_groups
from ml.schema import DatasetCard

VALID_MAPPING = {
    "source": "Nghi quyet 1685 / mapping noi bo",
    "effective_date": "2026-09-01",
    "version": "hcm_current_v1",
    "sha256": "a" * 64,
}


def _make_card(*, data_kind: str = "real", source_verified: bool = True) -> DatasetCard:
    return DatasetCard(
        dataset_version="hcm-2026-11-22",
        data_kind=data_kind,
        license_reference=(
            "permission-verified-source-2026"
            if data_kind == "real"
            else "synthetic technical fixture"
        ),
        source_verified=source_verified,
        geography_version="hcm_current_v1",
        grouping_version="tv1-group-v1",
        district_labels={f"fixture_{i}": f"Khu vuc {i}" for i in range(3)},
    )


def test_tv1_07_refresh_report_tracks_turnover_shift_and_active_evidence(listings, now):
    refreshed_now = now + timedelta(days=7)
    refreshed = listings.copy()
    # Thay 100 nhóm cũ bằng 100 nhóm mới và dịch thời gian snapshot +7 ngày
    refreshed["published_at"] = refreshed_now - timedelta(days=20)
    refreshed["price_observed_at"] = refreshed_now - timedelta(days=1)
    refreshed["source_snapshot_at"] = refreshed_now
    refreshed["availability_evidence_id"] = "export_active_2026_11_11"
    refreshed.loc[:99, "property_group_id"] = [f"new_group_{i}" for i in range(100)]
    refreshed.loc[:99, "district_code"] = "fixture_0"
    refreshed.loc[:49, "floor_level"] = None

    report = build_refresh_report(
        previous_clean=listings,
        refreshed_clean=refreshed,
        now=refreshed_now,
        previous_version="snap-v1",
        refreshed_version="snap-v2",
    )

    assert report["status"] == "READY"
    assert report["snapshot_is_newer"] is True
    assert report["group_turnover"]["retained_groups_count"] == 500
    assert report["group_turnover"]["new_groups_count"] == 100
    assert report["group_turnover"]["dropped_groups_count"] == 100
    assert report["active_evidence"]["active_rate"] == 1.0
    assert report["active_evidence"]["evidence_ids"] == ["export_active_2026_11_11"]
    assert report["coverage"]["district_share_tvd"] > 0
    assert report["feature_shift"]["missingness_shift"]["floor_level"]["delta"] > 0
    # Không làm lộ property_group_id vào báo cáo public
    serialized = json.dumps(report, allow_nan=False)
    assert "new_group_0" not in serialized
    assert "synthetic_group_0" not in serialized


def test_tv1_07_refresh_report_flags_non_newer_and_stale_snapshot(listings, now):
    stale_now = now + timedelta(days=10)
    report = build_refresh_report(
        previous_clean=listings,
        refreshed_clean=listings,
        now=stale_now,
        previous_version="snap-v1",
        refreshed_version="snap-v1-copy",
    )
    assert report["status"] == "BLOCKED"
    assert "refreshed_snapshot_not_newer_than_previous" in report["blockers"]
    assert "stale_for_publication" in report["blockers"]


def test_tv1_08_exposure_audit_and_export_integrate_with_registry_reserve(
    tmp_path, listings
):
    registry = tmp_path / "registry"
    init_registry(registry)

    all_ids = listings["property_group_id"].astype(str).tolist()
    record_groups(
        registry,
        {"fit": all_ids[:400], "tune": all_ids[400:480], "evaluation": all_ids[480:520]},
        run_id="run-001",
        actor="TV6",
    )

    summary, unexposed = audit_registry_exposure(listings, registry)
    assert summary["ready_for_new_release_test"] is True
    assert summary["overlap_total_groups"] == 520
    assert summary["overlap_by_purpose"]["fit"] == 400
    assert summary["overlap_by_purpose"]["tune"] == 80
    assert summary["overlap_by_purpose"]["evaluation"] == 40
    assert summary["unexposed_group_count"] == 80
    assert len(unexposed) == 80

    # Không lộ ID nhóm hoặc actor ra summary
    serialized = json.dumps(summary, allow_nan=False)
    assert all_ids[0] not in serialized
    assert "TV6" not in serialized

    # Xuất CSV chỉ có 1 cột property_group_id và chạy thật qua ml.registry reserve-test
    out_csv = export_unexposed_test_candidates(unexposed, tmp_path / "new-test-groups.csv")
    csv_text = out_csv.read_text(encoding="utf-8")
    assert csv_text.splitlines()[0] == "property_group_id"
    assert "asking_price_vnd" not in csv_text

    # Không ghi đè file đã tồn tại
    with pytest.raises(FileExistsError):
        export_unexposed_test_candidates(unexposed, out_csv)

    reserved = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "ml.registry",
            "reserve-test",
            "--registry-dir",
            str(registry),
            "--groups-csv",
            str(out_csv),
            "--run-id",
            "run-002",
            "--actor",
            "TV6",
        ],
        capture_output=True,
        text=True,
    )
    assert reserved.returncode == 0, reserved.stderr

    # Sau khi reserve xong, kiểm tra lại phải còn 0 nhóm chưa lộ -> không đủ test mới
    summary_after, unexposed_after = audit_registry_exposure(listings, registry)
    assert summary_after["ready_for_new_release_test"] is False
    assert summary_after["unexposed_group_count"] == 0
    assert unexposed_after == []


@pytest.mark.parametrize("problem", ["missing", "corrupt_header", "corrupt_event", "locked"])
def test_tv1_08_exposure_audit_fails_closed_on_invalid_registry(tmp_path, listings, problem):
    registry = tmp_path / "registry"
    if problem != "missing":
        init_registry(registry)
        if problem == "corrupt_header":
            (registry / "registry.json").write_text('{"version": true}', encoding="utf-8")
        elif problem == "corrupt_event":
            (registry / "events" / "bad.json").write_text("{}", encoding="utf-8")
        elif problem == "locked":
            (registry / ".write-lock").write_text("busy", encoding="utf-8")

    with pytest.raises(ValueError):
        audit_registry_exposure(listings, registry)


def test_tv1_09_pre_demo_readiness_passes_on_valid_fresh_snapshot(listings, now):
    card = _make_card()
    result = verify_pre_demo_readiness(
        listings, card=card, now=now, mapping_metadata=VALID_MAPPING
    )
    assert result["status"] == "PASS"
    assert all(result["checks"].values())
    assert result["freshness"]["remaining_serving_days"] == 13.0


def test_tv1_09_pre_demo_readiness_catches_license_mapping_freshness_and_active_issues(
    listings, now
):
    bad_card = _make_card(data_kind="synthetic", source_verified=False)
    bad_frame = listings.copy()
    bad_frame.loc[0, "district_code"] = "unmapped_area"
    bad_frame.loc[1, "active_at_snapshot"] = False
    stale_now = now + timedelta(days=16)

    result = verify_pre_demo_readiness(
        bad_frame,
        card=bad_card,
        now=stale_now,
        mapping_metadata={**VALID_MAPPING, "sha256": "not-a-hash"},
    )
    assert result["status"] == "FAIL"
    assert "unverified_or_non_real_source" in result["blockers"]
    assert "invalid_or_incomplete_district_mapping" in result["blockers"]
    assert "inactive_or_missing_active_evidence" in result["blockers"]
    assert "stale_for_serving" in result["blockers"]


def test_tv1_10_release_dataset_card_contains_required_manifest_fields(listings, now):
    card = _make_card()
    audit = build_dataset_audit(
        raw_count=len(listings) + 5,
        clean_frame=listings,
        quarantine_frame=pd.DataFrame({"reason_code": ["non_sale_listing"] * 5}),
        exact_duplicates_removed=0,
        now=now,
    )
    pre_demo = verify_pre_demo_readiness(
        listings, card=card, now=now, mapping_metadata=VALID_MAPPING
    )
    release_card = build_release_dataset_card(
        card,
        audit,
        raw_sha256="1" * 64,
        clean_sha256="2" * 64,
        split_sha256="3" * 64,
        source_owner="Chu du lieu da xac minh",
        source_revision="rev-2026-11-22",
        mapping_metadata=VALID_MAPPING,
        audit_method="Audit mau ngau nhien + rule-based quarantine",
        prepared_by="TV1",
        reviewed_by="TV6",
        area_basis="source_reported_unknown",
        pre_demo_check=pre_demo,
    )
    serialized = json.dumps(release_card, allow_nan=False)
    assert "hcm_current_v1" in serialized
    assert release_card["signoff"]["prepared_by"] == "TV1"
    assert release_card["signoff"]["reviewed_by"] == "TV6"
    assert release_card["hashes"]["clean_sha256"] == "2" * 64

    with pytest.raises(ValueError, match="distinct"):
        build_release_dataset_card(
            card,
            audit,
            raw_sha256="1" * 64,
            clean_sha256="2" * 64,
            source_owner="Owner",
            source_revision="rev-1",
            mapping_metadata=VALID_MAPPING,
            audit_method="Audit",
            prepared_by="TV1",
            reviewed_by="TV1",
            area_basis="source_reported_unknown",
        )