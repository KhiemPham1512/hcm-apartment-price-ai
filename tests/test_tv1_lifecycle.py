"""TV1-07..10 lifecycle tests: refresh shift, registry exposure, pre-demo check, release card."""

import json
import subprocess
import sys
from datetime import timedelta

import pandas as pd
import pytest
from pydantic import ValidationError

from ml.data import (
    audit_registry_exposure,
    build_dataset_audit,
    build_refresh_report,
    build_release_dataset_card,
    export_unexposed_test_candidates,
    load_current_csv,
    prepare_raw_listings,
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
    assert report["active_evidence"]["unique_evidence_count"] == 1
    assert "evidence_ids" not in report["active_evidence"]
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


def test_tv1_10_release_dataset_card_contains_required_manifest_fields(
    tmp_path, listings, now
):
    card = _make_card()
    registry = tmp_path / "registry"
    init_registry(registry)
    exposure_summary, _ = audit_registry_exposure(listings, registry)
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
        exposure_summary=exposure_summary,
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

def test_historical_loader_bypasses_7d_90d_freshness_but_keeps_chronology_quarantine_and_grouping(
    tmp_path, listings, now
):
    hist_card = DatasetCard(
        dataset_version="tinix-historical-test",
        data_kind="real",
        snapshot_kind="historical",
        license_reference="CC BY-NC 4.0",
        source_verified=True,
        geography_version="hcm_current_v1",
        grouping_version="tv1-group-v1",
        district_labels={f"fixture_{i}": f"Khu vuc {i}" for i in range(3)},
    )

    old = listings.iloc[:12].copy()
    old["property_group_id"] = None
    old["project_name_normalized"] = "project_alpha"
    old["published_at"] = now - timedelta(days=300)
    old["price_observed_at"] = now - timedelta(days=120)
    old["source_snapshot_at"] = now - timedelta(days=60)
    old["floor_level"] = None

    # 2 dòng cùng căn để kiểm tra grouping vẫn hoạt động
    old.loc[1, ["district_code", "area_m2", "bedrooms", "bathrooms"]] = old.loc[
        0, ["district_code", "area_m2", "bedrooms", "bathrooms"]
    ]
    # Dòng vi phạm quarantine (tin thuê)
    old.loc[2, "listing_type"] = "rent"
    # Dòng vi phạm chronology (price_observed_at < published_at)
    old.loc[3, "price_observed_at"] = now - timedelta(days=350)
    # Dòng vi phạm tương lai (source_snapshot_at > now)
    old.loc[4, "source_snapshot_at"] = now + timedelta(days=1)

    # Ở chế độ current, toàn bộ đều bị loại vì quá hạn 7 ngày / 90 ngày
    clean_cur, _, _ = prepare_raw_listings(old, now=now, snapshot_kind="current")
    assert clean_cur.empty

    # Ở chế độ historical, giữ lại 9 dòng hợp lệ, cách ly đúng 3 dòng lỗi và gộp nhóm 0 & 1
    clean_hist, quarantine_hist, _ = prepare_raw_listings(old, now=now, card=hist_card)
    assert len(clean_hist) == 9
    assert len(quarantine_hist) == 3
    assert set(quarantine_hist["reason_code"]) == {
        "non_sale_listing",
        "invalid_timestamp_order",
        "future_timestamp",
    }
    groups_by_id = clean_hist.set_index("listing_id")["property_group_id"]
    assert groups_by_id["synthetic_listing_0"] == groups_by_id["synthetic_listing_1"]

    csv_path = tmp_path / "historical.csv"
    clean_hist.to_csv(csv_path, index=False)

    # load_current_csv ở chế độ current phải từ chối, còn historical phải nạp thành công
    with pytest.raises(ValueError, match="too old for publication"):
        load_current_csv(csv_path, now=now)

    reloaded = load_current_csv(csv_path, now=now, card=hist_card)
    assert len(reloaded) == 9
    assert reloaded["floor_level"].isna().all()

    # Chronology lỗi trong CSV vẫn bị từ chối ở chế độ historical
    bad_csv = tmp_path / "historical_bad_chrono.csv"
    bad_df = clean_hist.copy()
    bad_df.loc[0, "price_observed_at"] = now - timedelta(days=400)
    bad_df.to_csv(bad_csv, index=False)
    with pytest.raises(ValidationError, match="published_at <= price_observed_at"):
        load_current_csv(bad_csv, now=now, card=hist_card)

def test_tv1_10_release_dataset_card_rejects_non_go_historical_or_missing_gates(
    tmp_path, listings, now
):
    card = _make_card()
    registry = tmp_path / "registry"
    init_registry(registry)
    exposure_summary, _ = audit_registry_exposure(listings, registry)
    audit = build_dataset_audit(
        raw_count=len(listings),
        clean_frame=listings,
        quarantine_frame=pd.DataFrame(columns=["row_index", "reason_code"]),
        exact_duplicates_removed=0,
        now=now,
    )
    pre_demo = verify_pre_demo_readiness(
        listings, card=card, now=now, mapping_metadata=VALID_MAPPING
    )
    valid_kwargs = {
        "raw_sha256": "1" * 64,
        "clean_sha256": "2" * 64,
        "source_owner": "Chu du lieu da xac minh",
        "source_revision": "rev-2026-11-22",
        "mapping_metadata": VALID_MAPPING,
        "audit_method": "Rule-based quarantine",
        "prepared_by": "TV1",
        "reviewed_by": "TV6",
        "area_basis": "source_reported_unknown",
        "exposure_summary": exposure_summary,
        "pre_demo_check": pre_demo,
    }

    # 1. Audit kh?ng ph?i GO
    nogo_audit = {**audit, "go_no_go": {"status": "NO-GO", "reasons": ["insufficient_groups"]}}
    with pytest.raises(ValueError, match="GO audit"):
        build_release_dataset_card(card, nogo_audit, **valid_kwargs)

    # 2. snapshot_kind kh?ng ph?i current
    hist_card = card.model_copy(update={"snapshot_kind": "historical"})
    with pytest.raises(ValueError, match="snapshot_kind='current'"):
        build_release_dataset_card(hist_card, audit, **valid_kwargs)

    # 3. Thi?u ho?c kh?ng ??t exposure_summary
    with pytest.raises(ValueError, match="exposure_summary"):
        build_release_dataset_card(
            card, audit, **{**valid_kwargs, "exposure_summary": None}
        )
    with pytest.raises(ValueError, match="exposure_summary"):
        build_release_dataset_card(
            card,
            audit,
            **{**valid_kwargs, "exposure_summary": {"ready_for_new_release_test": False}},
        )

    # 4. Thi?u ho?c kh?ng ??t pre_demo_check PASS
    with pytest.raises(ValueError, match="pre_demo_check"):
        build_release_dataset_card(
            card, audit, **{**valid_kwargs, "pre_demo_check": None}
        )
    with pytest.raises(ValueError, match="pre_demo_check"):
        build_release_dataset_card(
            card, audit, **{**valid_kwargs, "pre_demo_check": {"status": "FAIL"}}
        )
