"""Validate already-normalized listings; raw adapters belong to TV1."""

import csv
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import ValidationError
from sklearn.model_selection import GroupShuffleSplit

from ml.schema import (
    FEATURES,
    MIN_DISTRICT_GROUPS,
    PUBLICATION_MAX_AGE_DAYS,
    SCHEMA_VERSION,
    SERVING_MAX_AGE_DAYS,
    ApartmentFeatures,
    DatasetCard,
    Listing,
)

_PRICE_PER_M2_RE = re.compile(r"(/\s*m2|/\s*m²|m2|m²|mét\s*vuông)", re.IGNORECASE)
_RENTAL_RE = re.compile(r"(/\s*tháng|/\s*thang|thuê|thue|trả\s*góp|tra\s*gop)", re.IGNORECASE)
_NEGOTIABLE_RE = re.compile(r"(thỏa\s*thuận|thoa\s*thuan|liên\s*hệ|lien\s*he|inbox)", re.IGNORECASE)
_TY_TRIEU_RE = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s*t[ỷy]\s*(\d+(?:[.,]\d+)?)?\s*(?:triệu|trieu|tr)?\s*$",
    re.IGNORECASE,
)
_UNIT_VALUE_RE = re.compile(
    r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*(tỷ|ty|triệu|trieu|tr|nghìn|nghin|ngàn|ngan|vnd|đ|d)?\s*$",
    re.IGNORECASE,
)
_AREA_RANGE_RE = re.compile(r"\d+\s*[-~–]\s*\d+")
_AREA_RE = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*(?:m2|m²|sqm)?\s*$", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:0|\+?84)\d{9,10}(?!\d)")

MARKET_MIN_TOTAL_GROUPS = 500
MARKET_MIN_TEST_GROUPS = 75


def _resolve_snapshot_kind(
    snapshot_kind: Literal["current", "historical"] = "current",
    card: DatasetCard | None = None,
) -> Literal["current", "historical"]:
    resolved = card.snapshot_kind if card is not None else snapshot_kind
    if resolved not in ("current", "historical"):
        raise ValueError(f"Unsupported snapshot_kind: {resolved}")
    return resolved


def _is_missing(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return value is None
    if isinstance(value, float) and np.isnan(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return bool(pd.isna(value))


def _contains_phone_pii(text: str) -> bool:
    compact = re.sub(r"[\s.\-]", "", text)
    return bool(_PHONE_RE.search(compact))


def parse_asking_price_vnd(raw_price: Any) -> tuple[float | None, str | None]:
    """Parse raw sale price into total VND; quarantine rental, /m2, or ambiguous text."""
    if isinstance(raw_price, bool):
        return None, "invalid_asking_price"
    if isinstance(raw_price, (int, float, np.number)):
        val = float(raw_price)
        if not np.isfinite(val) or val <= 0:
            return None, "invalid_asking_price"
        return val, None
    if _is_missing(raw_price):
        return None, "ambiguous_or_negotiable_price"

    text = str(raw_price).strip()
    if _RENTAL_RE.search(text):
        return None, "rental_or_installment_price"
    if _PRICE_PER_M2_RE.search(text):
        return None, "unconverted_price_per_m2"
    if _NEGOTIABLE_RE.search(text):
        return None, "ambiguous_or_negotiable_price"

    ty_trieu = _TY_TRIEU_RE.match(text)
    if ty_trieu:
        ty = float(ty_trieu.group(1).replace(",", "."))
        trieu = float((ty_trieu.group(2) or "0").replace(",", "."))
        total = ty * 1_000_000_000.0 + trieu * 1_000_000.0
        return (total, None) if total > 0 else (None, "invalid_asking_price")

    match = _UNIT_VALUE_RE.match(text)
    if not match:
        return None, "ambiguous_or_negotiable_price"

    number = float(match.group(1).replace(",", "."))
    if not np.isfinite(number) or number <= 0:
        return None, "invalid_asking_price"

    unit = (match.group(2) or "vnd").lower()
    multipliers = {
        "tỷ": 1_000_000_000.0,
        "ty": 1_000_000_000.0,
        "triệu": 1_000_000.0,
        "trieu": 1_000_000.0,
        "tr": 1_000_000.0,
        "nghìn": 1_000.0,
        "nghin": 1_000.0,
        "ngàn": 1_000.0,
        "ngan": 1_000.0,
        "vnd": 1.0,
        "đ": 1.0,
        "d": 1.0,
    }
    return number * multipliers[unit], None


def parse_area_m2(raw_area: Any) -> tuple[float | None, str | None]:
    """Parse apartment area in m2 and enforce hard bounds [10, 500] without clipping."""
    if isinstance(raw_area, bool) or _is_missing(raw_area):
        return None, "ambiguous_area"
    if isinstance(raw_area, (int, float, np.number)):
        val = float(raw_area)
    else:
        text = str(raw_area).strip()
        if _AREA_RANGE_RE.search(text):
            return None, "ambiguous_area"
        match = _AREA_RE.match(text)
        if not match:
            return None, "ambiguous_area"
        val = float(match.group(1).replace(",", "."))

    if not np.isfinite(val):
        return None, "ambiguous_area"
    if val < 10.0 or val > 500.0:
        return None, "area_out_of_bounds"
    return val, None


def _parse_optional_int(value: Any, minimum: int, maximum: int) -> tuple[int | None, bool]:
    if _is_missing(value):
        return None, True
    if isinstance(value, bool):
        return None, False
    if isinstance(value, (int, np.integer)):
        iv = int(value)
    elif isinstance(value, (float, np.floating)):
        if not np.isfinite(value) or not float(value).is_integer():
            return None, False
        iv = int(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not re.fullmatch(r"[+-]?\d+", stripped):
            return None, False
        iv = int(stripped)
    else:
        return None, False
    if iv < minimum or iv > maximum:
        return None, False
    return iv, True


def _parse_utc_datetime(value: Any) -> datetime | None:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc)
    return None


def assign_property_group_id(frame: pd.DataFrame) -> pd.Series:
    """Assign deterministic group IDs without target price or area+district-only merges."""
    group_ids: list[str] = []
    for record in frame.to_dict("records"):
        existing = record.get("property_group_id")
        if not _is_missing(existing):
            group_ids.append(str(existing).strip())
            continue

        district = str(record.get("district_code") or "").strip().lower()
        project = str(record.get("project_name_normalized") or "").strip().lower()
        area = float(record["area_m2"])
        beds = record.get("bedrooms")
        baths = record.get("bathrooms")
        floor = record.get("floor_level")

        has_project = bool(project)
        has_structure = not (_is_missing(beds) and _is_missing(baths) and _is_missing(floor))
        if has_project and has_structure:
            key = (
                f"apt|{district}|{project}|{area:.1f}|"
                f"{'na' if _is_missing(beds) else int(beds)}|"
                f"{'na' if _is_missing(baths) else int(baths)}|"
                f"{'na' if _is_missing(floor) else int(floor)}"
            )
        else:
            source_id = str(record.get("source_id") or "").strip()
            listing_id = str(record.get("listing_id") or "").strip()
            key = f"singleton|{source_id}|{listing_id}"

        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
        group_ids.append(f"grp_{digest}")
    return pd.Series(group_ids, index=frame.index, dtype="object")


def prepare_raw_listings(
    raw_frame: pd.DataFrame,
    now: datetime,
    district_mapping: dict[str, str] | None = None,
    expected_area_basis: str | None = None,
    *,
    snapshot_kind: Literal["current", "historical"] = "current",
    card: DatasetCard | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Normalize raw records into contract-compliant listings and a quarantine table."""
    resolved_kind = _resolve_snapshot_kind(snapshot_kind, card)
    clean_candidates: list[dict[str, Any]] = []
    quarantine_rows: list[dict[str, Any]] = []

    for idx, record in enumerate(raw_frame.to_dict("records")):
        row_copy = dict(record)
        row_copy["_raw_row_index"] = idx

        prop_type = str(record.get("property_type") or "").strip().lower()
        if prop_type != "apartment":
            quarantine_rows.append({**row_copy, "reason_code": "unsupported_property_type"})
            continue

        list_type = str(record.get("listing_type") or "").strip().lower()
        if list_type != "sale":
            quarantine_rows.append({**row_copy, "reason_code": "non_sale_listing"})
            continue

        active = record.get("active_at_snapshot")
        evidence_raw = record.get("availability_evidence_id")
        if active is not True or _is_missing(evidence_raw):
            quarantine_rows.append({**row_copy, "reason_code": "missing_active_evidence"})
            continue

        listing_id_raw = record.get("listing_id")
        source_id_raw = record.get("source_id")
        if _is_missing(listing_id_raw) or _is_missing(source_id_raw):
            quarantine_rows.append({**row_copy, "reason_code": "invalid_identifier_or_pii"})
            continue

        listing_id = str(listing_id_raw).strip()
        source_id = str(source_id_raw).strip()
        evidence_id = str(evidence_raw).strip()
        if _contains_phone_pii(listing_id) or _contains_phone_pii(evidence_id):
            quarantine_rows.append({**row_copy, "reason_code": "invalid_identifier_or_pii"})
            continue

        raw_district = str(record.get("district_code") or "").strip()
        if not raw_district:
            quarantine_rows.append({**row_copy, "reason_code": "unsupported_district"})
            continue
        if district_mapping is not None:
            if raw_district not in district_mapping:
                quarantine_rows.append({**row_copy, "reason_code": "unsupported_district"})
                continue
            district_code = district_mapping[raw_district]
        else:
            district_code = raw_district

        area_m2, area_reason = parse_area_m2(record.get("area_m2"))
        if area_reason is not None or area_m2 is None:
            quarantine_rows.append({**row_copy, "reason_code": area_reason})
            continue

        price_vnd, price_reason = parse_asking_price_vnd(record.get("asking_price_vnd"))
        if price_reason is not None or price_vnd is None:
            quarantine_rows.append({**row_copy, "reason_code": price_reason})
            continue

        bedrooms, ok_bed = _parse_optional_int(record.get("bedrooms"), 0, 10)
        bathrooms, ok_bath = _parse_optional_int(record.get("bathrooms"), 0, 10)
        floor_level, ok_floor = _parse_optional_int(record.get("floor_level"), 0, 100)
        if not (ok_bed and ok_bath and ok_floor):
            quarantine_rows.append({**row_copy, "reason_code": "invalid_optional_feature"})
            continue

        area_basis_raw = record.get("area_basis")
        if _is_missing(area_basis_raw):
            quarantine_rows.append({**row_copy, "reason_code": "inconsistent_area_basis"})
            continue
        area_basis = str(area_basis_raw).strip()
        if expected_area_basis is not None and area_basis != expected_area_basis:
            quarantine_rows.append({**row_copy, "reason_code": "inconsistent_area_basis"})
            continue

        pub_at = _parse_utc_datetime(record.get("published_at"))
        obs_at = _parse_utc_datetime(record.get("price_observed_at"))
        snap_at = _parse_utc_datetime(record.get("source_snapshot_at"))
        if pub_at is None or obs_at is None or snap_at is None:
            quarantine_rows.append({**row_copy, "reason_code": "invalid_timestamp"})
            continue
        if not (pub_at <= obs_at <= snap_at):
            quarantine_rows.append({**row_copy, "reason_code": "invalid_timestamp_order"})
            continue

        project_norm = (
            None
            if _is_missing(record.get("project_name_normalized"))
            else str(record.get("project_name_normalized")).strip()
        )
        existing_group = (
            None
            if _is_missing(record.get("property_group_id"))
            else str(record.get("property_group_id")).strip()
        )

        candidate = {
            "area_m2": area_m2,
            "district_code": district_code,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "floor_level": floor_level,
            "listing_id": listing_id,
            "source_id": source_id,
            "property_group_id": existing_group or "pending_group",
            "published_at": pub_at,
            "price_observed_at": obs_at,
            "source_snapshot_at": snap_at,
            "active_at_snapshot": True,
            "availability_evidence_id": evidence_id,
            "asking_price_vnd": price_vnd,
            "property_type": "apartment",
            "listing_type": "sale",
            "area_basis": area_basis,
        }
        try:
            validated = Listing.model_validate(candidate)
            if resolved_kind == "current":
                validated.check_current(now)
            elif validated.source_snapshot_at > now:
                raise ValueError("Future snapshot")
        except (ValidationError, ValueError) as exc:
            msg = str(exc)
            if "Future snapshot" in msg:
                reason = "future_timestamp"
            elif "too old for publication" in msg:
                reason = "stale_for_publication"
            elif "exceeds recent window" in msg:
                reason = "exceeds_recent_window"
            else:
                reason = "schema_validation_failed"
            quarantine_rows.append({**row_copy, "reason_code": reason})
            continue

        dumped = validated.model_dump()
        dumped["property_group_id"] = existing_group
        dumped["project_name_normalized"] = project_norm
        clean_candidates.append(dumped)

    quarantine_df = pd.DataFrame(quarantine_rows)
    if not clean_candidates:
        empty_clean = pd.DataFrame(columns=list(Listing.model_fields.keys()))
        audit = build_dataset_audit(
            raw_count=len(raw_frame),
            clean_frame=empty_clean,
            quarantine_frame=quarantine_df,
            exact_duplicates_removed=0,
            now=now,
        )
        return empty_clean, quarantine_df, audit

    clean_df = pd.DataFrame(clean_candidates)
    if clean_df["area_basis"].nunique() > 1:
        dominant_basis = expected_area_basis or str(clean_df["area_basis"].mode().iloc[0])
        mismatch_mask = clean_df["area_basis"] != dominant_basis
        if mismatch_mask.any():
            mismatched = clean_df.loc[mismatch_mask].copy()
            mismatched["reason_code"] = "inconsistent_area_basis"
            quarantine_df = pd.concat([quarantine_df, mismatched], ignore_index=True)
            clean_df = clean_df.loc[~mismatch_mask].reset_index(drop=True)

    before_dedup = len(clean_df)
    clean_df = (
        clean_df.sort_values(
            ["price_observed_at", "published_at", "source_snapshot_at"],
            ascending=[False, False, False],
            kind="stable",
        )
        .drop_duplicates(["source_id", "listing_id"], keep="first")
        .reset_index(drop=True)
    )
    exact_duplicates_removed = before_dedup - len(clean_df)

    clean_df["property_group_id"] = assign_property_group_id(clean_df)
    audit = build_dataset_audit(
        raw_count=len(raw_frame),
        clean_frame=clean_df,
        quarantine_frame=quarantine_df,
        exact_duplicates_removed=exact_duplicates_removed,
        now=now,
    )

    contract_columns = list(Listing.model_fields.keys())
    return clean_df.loc[:, contract_columns].copy(), quarantine_df, audit


def build_dataset_audit(
    raw_count: int,
    clean_frame: pd.DataFrame,
    quarantine_frame: pd.DataFrame,
    exact_duplicates_removed: int,
    now: datetime,
) -> dict[str, Any]:
    """Generate TV1 audit report, freshness windows, and GO/NO-GO gate evaluation."""
    reason_counts: dict[str, int] = {}
    if not quarantine_frame.empty and "reason_code" in quarantine_frame.columns:
        reason_counts = {
            str(k): int(v) for k, v in quarantine_frame["reason_code"].value_counts().items()
        }

    if clean_frame.empty:
        return {
            "schema_version": SCHEMA_VERSION,
            "raw_row_count": raw_count,
            "clean_row_count": 0,
            "quarantine_row_count": len(quarantine_frame),
            "exact_duplicates_removed": exact_duplicates_removed,
            "n_groups": 0,
            "quarantine_reasons": reason_counts,
            "missingness": {},
            "supported_districts": [],
            "go_no_go": {
                "status": "NO-GO",
                "reasons": ["no_clean_rows"],
            },
        }

    rep_frame = representatives(clean_frame)
    n_groups = int(rep_frame["property_group_id"].nunique())

    missingness = {
        col: float(clean_frame[col].isna().mean())
        for col in ("bedrooms", "bathrooms", "floor_level")
        if col in clean_frame.columns
    }

    test_groups = 0
    supported_districts: list[str] = []
    if n_groups >= 20:
        splits = split_groups(clean_frame)
        test_groups = int(splits["test"]["property_group_id"].nunique())
        train_counts = splits["train"].groupby("district_code")["property_group_id"].nunique()
        supported_districts = sorted(
            str(code) for code, count in train_counts.items() if int(count) >= MIN_DISTRICT_GROUPS
        )

    obs_series = pd.to_datetime(clean_frame["price_observed_at"], utc=True)
    pub_series = pd.to_datetime(clean_frame["published_at"], utc=True)
    snap_series = pd.to_datetime(clean_frame["source_snapshot_at"], utc=True)

    listing_ages = (snap_series - pub_series).dt.total_seconds() / 86400.0
    price_ages = (now - obs_series).dt.total_seconds() / 86400.0

    blockers: list[str] = []
    if n_groups < MARKET_MIN_TOTAL_GROUPS:
        blockers.append(f"insufficient_total_groups:{n_groups}<{MARKET_MIN_TOTAL_GROUPS}")
    if test_groups < MARKET_MIN_TEST_GROUPS:
        blockers.append(f"insufficient_test_groups:{test_groups}<{MARKET_MIN_TEST_GROUPS}")
    if not supported_districts:
        blockers.append("no_district_meets_min_train_groups")

    return {
        "schema_version": SCHEMA_VERSION,
        "raw_row_count": raw_count,
        "clean_row_count": len(clean_frame),
        "quarantine_row_count": len(quarantine_frame),
        "exact_duplicates_removed": exact_duplicates_removed,
        "n_groups": n_groups,
        "test_groups": test_groups,
        "quarantine_reasons": reason_counts,
        "missingness": missingness,
        "supported_districts": supported_districts,
        "data_as_of": obs_series.min().isoformat(),
        "data_latest_at": obs_series.max().isoformat(),
        "source_snapshot_at": snap_series.max().isoformat(),
        "data_window_start": obs_series.min().isoformat(),
        "data_window_end": obs_series.max().isoformat(),
        "listing_window_start": pub_series.min().isoformat(),
        "listing_window_end": pub_series.max().isoformat(),
        "age_summary": {
            "median_listing_age_days": round(float(listing_ages.median()), 2),
            "median_price_age_days": round(float(price_ages.median()), 2),
            "computed_at": now.isoformat(),
        },
        "go_no_go": {
            "status": "GO" if not blockers else "NO-GO",
            "reasons": blockers,
        },
    }


def load_current_csv(
    path: Path,
    now: datetime,
    *,
    snapshot_kind: Literal["current", "historical"] = "current",
    card: DatasetCard | None = None,
) -> pd.DataFrame:
    resolved_kind = _resolve_snapshot_kind(snapshot_kind, card)
    frame = pd.read_csv(path)
    rows = []
    for record in frame.to_dict("records"):
        record = _clean_listing_record(record)
        listing = Listing.model_validate(record)
        if resolved_kind == "current":
            listing.check_current(now)
        elif listing.source_snapshot_at > now:
            raise ValueError("Future snapshot")
        rows.append(listing.model_dump())
    if not rows:
        raise ValueError("Dataset is empty")
    result = pd.DataFrame(rows)
    if result.duplicated(["source_id", "listing_id"]).any():
        raise ValueError("Duplicate source/listing IDs require upstream resolution")
    if result["area_basis"].nunique() != 1:
        raise ValueError("Mixed area basis")
    return result


def representatives(frame: pd.DataFrame) -> pd.DataFrame:
    """Select without using price; stable tie break does not depend on input order."""
    if frame["property_group_id"].isna().any():
        raise ValueError("Missing group IDs")
    return (
        frame.sort_values(
            ["price_observed_at", "published_at", "source_id", "listing_id"],
            ascending=[False, False, True, True],
            kind="stable",
        )
        .drop_duplicates("property_group_id", keep="first")
        .reset_index(drop=True)
    )


def split_groups(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    frame = representatives(frame)
    if frame["property_group_id"].nunique() < 20:
        raise ValueError("At least 20 groups required for a technical split")
    first = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=42)
    dev_idx, test_idx = next(first.split(frame, groups=frame["property_group_id"]))
    dev = frame.iloc[dev_idx]
    second = GroupShuffleSplit(n_splits=1, test_size=15 / 85, random_state=42)
    train_idx, val_idx = next(second.split(dev, groups=dev["property_group_id"]))
    return {
        "train": dev.iloc[train_idx].copy(),
        "validation": dev.iloc[val_idx].copy(),
        "test": frame.iloc[test_idx].copy(),
    }


def feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Strictly select contract features, including when input contains the target."""
    result = frame.loc[:, FEATURES].copy()
    for record in result.to_dict("records"):
        clean = {
            key: None if isinstance(value, float) and np.isnan(value) else value
            for key, value in record.items()
        }
        for key in ("bedrooms", "bathrooms", "floor_level"):
            value = clean.get(key)
            if isinstance(value, float) and np.isfinite(value) and value.is_integer():
                clean[key] = int(value)
        ApartmentFeatures.model_validate(clean)
    return result


_REGISTRY_PURPOSES = frozenset({"fit", "tune", "label_analysis", "evaluation", "test_reserved"})
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def _is_true_bool(value: Any) -> bool:
    return isinstance(value, (bool, np.bool_)) and bool(value)


def _clean_listing_record(record: dict[str, Any]) -> dict[str, Any]:
    clean = {
        key: None if isinstance(value, float) and np.isnan(value) else value
        for key, value in record.items()
    }
    for key in ("bedrooms", "bathrooms", "floor_level"):
        value = clean.get(key)
        if isinstance(value, float) and np.isfinite(value) and value.is_integer():
            clean[key] = int(value)
    return clean


def _project_concentration(rep_frame: pd.DataFrame, top_n: int = 5) -> dict[str, Any]:
    if "project_name_normalized" not in rep_frame.columns:
        return {"available": False, "missing_rate": None, "top_projects": []}
    total = len(rep_frame)
    series = rep_frame["project_name_normalized"]
    missing = sum(_is_missing(v) for v in series)
    present = [str(v).strip() for v in series if not _is_missing(v)]
    counts = pd.Series(present, dtype="object").value_counts().head(top_n)
    top_projects = [
        {
            "project_name_normalized": str(name),
            "groups": int(count),
            "share": round(int(count) / total, 4),
        }
        for name, count in counts.items()
    ]
    return {
        "available": True,
        "missing_rate": round(missing / total, 4) if total else 0.0,
        "top_projects": top_projects,
    }


def _district_coverage(frame: pd.DataFrame) -> tuple[int, list[str], list[str]]:
    rep = representatives(frame)
    all_districts = sorted(rep["district_code"].astype(str).unique().tolist())
    n_groups = int(rep["property_group_id"].nunique())
    if n_groups < 20:
        return 0, [], all_districts
    splits = split_groups(frame)
    test_groups = int(splits["test"]["property_group_id"].nunique())
    train_counts = splits["train"].groupby("district_code")["property_group_id"].nunique()
    supported = sorted(
        str(code) for code, count in train_counts.items() if int(count) >= MIN_DISTRICT_GROUPS
    )
    underrepresented = sorted(set(all_districts) - set(supported))
    return test_groups, supported, underrepresented


def build_refresh_report(
    previous_clean: pd.DataFrame,
    refreshed_clean: pd.DataFrame,
    now: datetime,
    previous_version: str,
    refreshed_version: str,
) -> dict[str, Any]:
    """TV1-07: Compare previous and refreshed snapshots for shift, coverage, and active evidence."""
    if previous_clean.empty or refreshed_clean.empty:
        raise ValueError("Both previous and refreshed snapshots must be non-empty")
    if not previous_version.strip() or not refreshed_version.strip():
        raise ValueError("Snapshot versions must not be blank")

    prev_rep = representatives(previous_clean)
    new_rep = representatives(refreshed_clean)

    prev_groups = set(prev_rep["property_group_id"].astype(str))
    new_groups = set(new_rep["property_group_id"].astype(str))
    retained = len(prev_groups & new_groups)
    added = len(new_groups - prev_groups)
    dropped = len(prev_groups - new_groups)

    prev_snap = pd.to_datetime(previous_clean["source_snapshot_at"], utc=True)
    new_snap = pd.to_datetime(refreshed_clean["source_snapshot_at"], utc=True)
    new_obs = pd.to_datetime(refreshed_clean["price_observed_at"], utc=True)
    new_pub = pd.to_datetime(refreshed_clean["published_at"], utc=True)
    snapshot_is_newer = bool(new_snap.max() > prev_snap.max())

    prev_dist = prev_rep["district_code"].astype(str).value_counts().to_dict()
    new_dist = new_rep["district_code"].astype(str).value_counts().to_dict()
    all_districts = sorted(set(prev_dist) | set(new_dist))
    district_shift: dict[str, dict[str, Any]] = {}
    tvd = 0.0
    for code in all_districts:
        p_cnt = int(prev_dist.get(code, 0))
        n_cnt = int(new_dist.get(code, 0))
        p_share = p_cnt / len(prev_rep)
        n_share = n_cnt / len(new_rep)
        tvd += abs(n_share - p_share)
        district_shift[code] = {
            "previous_groups": p_cnt,
            "refreshed_groups": n_cnt,
            "delta_groups": n_cnt - p_cnt,
            "previous_share": round(p_share, 4),
            "refreshed_share": round(n_share, 4),
            "delta_share": round(n_share - p_share, 4),
        }

    test_groups, supported_districts, underrepresented_districts = _district_coverage(
        refreshed_clean
    )

    prev_area_med = float(prev_rep["area_m2"].median())
    new_area_med = float(new_rep["area_m2"].median())
    prev_price_med = float(prev_rep["asking_price_vnd"].median())
    new_price_med = float(new_rep["asking_price_vnd"].median())

    missingness_shift: dict[str, dict[str, float]] = {}
    for col in ("bedrooms", "bathrooms", "floor_level"):
        if col in previous_clean.columns and col in refreshed_clean.columns:
            p_miss = float(previous_clean[col].isna().mean())
            n_miss = float(refreshed_clean[col].isna().mean())
            missingness_shift[col] = {
                "previous": round(p_miss, 4),
                "refreshed": round(n_miss, 4),
                "delta": round(n_miss - p_miss, 4),
            }

    active_count = sum(_is_true_bool(v) for v in refreshed_clean["active_at_snapshot"])
    evidence_vals = [
        str(v).strip()
        for v in refreshed_clean["availability_evidence_id"]
        if not _is_missing(v) and not _contains_phone_pii(str(v))
    ]
    evidence_ids = sorted(set(evidence_vals))
    active_rate = round(active_count / len(refreshed_clean), 4)
    evidence_rate = round(len(evidence_vals) / len(refreshed_clean), 4)

    listing_ages = (new_snap - new_pub).dt.total_seconds() / 86400.0
    price_ages = (now - new_obs).dt.total_seconds() / 86400.0

    blockers: list[str] = []
    if not snapshot_is_newer:
        blockers.append("refreshed_snapshot_not_newer_than_previous")
    if active_rate < 1.0 or evidence_rate < 1.0:
        blockers.append("incomplete_active_evidence")
    if (
        new_snap.max() > now
        or now - new_snap.max() > timedelta(days=PUBLICATION_MAX_AGE_DAYS)
        or now - new_obs.min() > timedelta(days=PUBLICATION_MAX_AGE_DAYS)
    ):
        blockers.append("stale_for_publication")
    if len(new_groups) < MARKET_MIN_TOTAL_GROUPS:
        blockers.append(f"insufficient_total_groups:{len(new_groups)}<{MARKET_MIN_TOTAL_GROUPS}")
    if test_groups < MARKET_MIN_TEST_GROUPS:
        blockers.append(f"insufficient_test_groups:{test_groups}<{MARKET_MIN_TEST_GROUPS}")
    if not supported_districts:
        blockers.append("no_district_meets_min_train_groups")

    return {
        "schema_version": SCHEMA_VERSION,
        "previous_version": previous_version.strip(),
        "refreshed_version": refreshed_version.strip(),
        "snapshot_is_newer": snapshot_is_newer,
        "previous_source_snapshot_at": prev_snap.max().isoformat(),
        "source_snapshot_at": new_snap.max().isoformat(),
        "data_as_of": new_obs.min().isoformat(),
        "data_latest_at": new_obs.max().isoformat(),
        "data_window_start": new_obs.min().isoformat(),
        "data_window_end": new_obs.max().isoformat(),
        "listing_window_start": new_pub.min().isoformat(),
        "listing_window_end": new_pub.max().isoformat(),
        "age_summary": {
            "median_listing_age_days": round(float(listing_ages.median()), 2),
            "median_price_age_days": round(float(price_ages.median()), 2),
            "computed_at": now.isoformat(),
        },
        "active_evidence": {
            "total_rows": len(refreshed_clean),
            "active_row_count": active_count,
            "active_rate": active_rate,
            "evidence_present_count": len(evidence_vals),
            "evidence_coverage_rate": evidence_rate,
            "unique_evidence_count": len(evidence_ids),
            "evidence_ids": evidence_ids,
        },
        "group_turnover": {
            "previous_n_groups": len(prev_groups),
            "refreshed_n_groups": len(new_groups),
            "retained_groups_count": retained,
            "new_groups_count": added,
            "dropped_groups_count": dropped,
            "retention_rate": round(retained / len(prev_groups), 4),
            "new_group_rate": round(added / len(new_groups), 4),
        },
        "coverage": {
            "n_groups": len(new_groups),
            "test_groups": test_groups,
            "supported_districts": supported_districts,
            "underrepresented_districts": underrepresented_districts,
            "new_districts": sorted(set(new_dist) - set(prev_dist)),
            "dropped_districts": sorted(set(prev_dist) - set(new_dist)),
            "district_share_tvd": round(0.5 * tvd, 4),
            "district_shift": district_shift,
            "project_concentration": _project_concentration(new_rep),
        },
        "feature_shift": {
            "area_m2": {
                "previous_median": round(prev_area_med, 2),
                "refreshed_median": round(new_area_med, 2),
                "delta_median": round(new_area_med - prev_area_med, 2),
                "pct_change_median": round((new_area_med - prev_area_med) / prev_area_med, 4),
            },
            "asking_price_vnd": {
                "previous_median": round(prev_price_med, 2),
                "refreshed_median": round(new_price_med, 2),
                "pct_change_median": round((new_price_med - prev_price_med) / prev_price_med, 4),
            },
            "missingness_shift": missingness_shift,
        },
        "status": "READY" if not blockers else "BLOCKED",
        "blockers": blockers,
    }


def _read_registry_events(registry_dir: Path) -> list[dict[str, Any]]:
    """Read private exposure registry read-only; fail closed if missing, corrupt, or locked."""
    if not registry_dir.exists() or not registry_dir.is_dir():
        raise ValueError("Registry directory is missing")
    if (registry_dir / ".write-lock").exists():
        raise ValueError("Registry is locked by another writer")
    header_path = registry_dir / "registry.json"
    events_dir = registry_dir / "events"
    if not header_path.is_file() or not events_dir.is_dir():
        raise ValueError("Incomplete registry structure")
    header = json.loads(header_path.read_text(encoding="utf-8"))
    if header != {"version": 1} or type(header.get("version")) is not int:
        raise ValueError("Invalid registry version")

    required_keys = {"version", "run_id", "actor", "purpose", "recorded_at", "groups"}
    now_utc = datetime.now(timezone.utc)
    events: list[dict[str, Any]] = []
    for path in sorted(events_dir.iterdir()):
        if not path.is_file():
            raise ValueError("Invalid entry in registry events directory")
        event = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(event, dict) or set(event) != required_keys:
            raise ValueError("Invalid registry event")
        groups = event["groups"]
        valid_groups = (
            isinstance(groups, list)
            and bool(groups)
            and all(isinstance(g, str) and g.strip() and g == g.strip() for g in groups)
            and len(set(groups)) == len(groups)
        )
        if (
            type(event["version"]) is not int
            or event["version"] != 1
            or event["purpose"] not in _REGISTRY_PURPOSES
            or not all(isinstance(event[k], str) and event[k].strip() for k in ("actor", "run_id"))
            or not valid_groups
        ):
            raise ValueError("Invalid registry event")
        stamp = datetime.fromisoformat(event["recorded_at"])
        if stamp.tzinfo is None or stamp.utcoffset() is None or stamp > now_utc:
            raise ValueError("Invalid registry timestamp")
        events.append(event)
    return events


def audit_registry_exposure(
    clean_frame: pd.DataFrame,
    registry_dir: Path,
    min_new_test_groups: int = MARKET_MIN_TEST_GROUPS,
) -> tuple[dict[str, Any], list[str]]:
    """TV1-08: Cross-check snapshot groups against private registry without leaking IDs."""
    if clean_frame.empty:
        raise ValueError("Snapshot is empty")
    events = _read_registry_events(registry_dir)
    rep = representatives(clean_frame)
    snapshot_groups = set(rep["property_group_id"].astype(str))

    by_purpose: dict[str, set[str]] = {purpose: set() for purpose in sorted(_REGISTRY_PURPOSES)}
    all_exposed: set[str] = set()
    runs: set[str] = set()
    for event in events:
        runs.add(event["run_id"])
        event_groups = set(event["groups"])
        by_purpose[event["purpose"]].update(event_groups)
        all_exposed.update(event_groups)

    overlap_total = len(snapshot_groups & all_exposed)
    overlap_by_purpose = {
        purpose: len(snapshot_groups & groups) for purpose, groups in by_purpose.items()
    }
    unexposed = sorted(snapshot_groups - all_exposed)

    blockers: list[str] = []
    if len(unexposed) < min_new_test_groups:
        blockers.append(
            f"insufficient_unexposed_test_groups:{len(unexposed)}<{min_new_test_groups}"
        )

    summary = {
        "snapshot_n_groups": len(snapshot_groups),
        "registry_event_count": len(events),
        "registry_runs": sorted(runs),
        "registry_total_unique_groups": len(all_exposed),
        "overlap_total_groups": overlap_total,
        "overlap_by_purpose": overlap_by_purpose,
        "unexposed_group_count": len(unexposed),
        "min_new_test_groups": min_new_test_groups,
        "ready_for_new_release_test": not blockers,
        "blockers": blockers,
    }
    return summary, unexposed


def export_unexposed_test_candidates(
    unexposed_group_ids: list[str],
    output_csv: Path,
) -> Path:
    """Write a label-free CSV with only property_group_id for TV6 reserve-test."""
    if not unexposed_group_ids:
        raise ValueError("No unexposed group IDs to export")
    cleaned = [str(g).strip() for g in unexposed_group_ids]
    if any(not g for g in cleaned) or len(set(cleaned)) != len(cleaned):
        raise ValueError("Group IDs must be non-blank and unique")
    with output_csv.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["property_group_id"])
        for group_id in sorted(cleaned):
            writer.writerow([group_id])
    return output_csv


def _validate_mapping_metadata(mapping_metadata: dict[str, Any]) -> bool:
    required = ("source", "effective_date", "version", "sha256")
    if not all(
        isinstance(mapping_metadata.get(k), str) and mapping_metadata[k].strip() for k in required
    ):
        return False
    return bool(_SHA256_RE.fullmatch(mapping_metadata["sha256"].strip()))


def verify_pre_demo_readiness(
    clean_frame: pd.DataFrame,
    card: DatasetCard,
    now: datetime,
    mapping_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """TV1-09: Re-verify license, mapping, freshness, and active listings near demo."""
    if clean_frame.empty:
        return {
            "status": "FAIL",
            "checked_at": now.isoformat(),
            "checks": {
                "license_and_source_verified": False,
                "mapping_valid": False,
                "freshness_valid": False,
                "active_listings_verified": False,
                "coverage_and_thresholds_met": False,
            },
            "blockers": ["empty_dataset"],
        }

    blockers: list[str] = []

    license_ok = (
        card.data_kind == "real"
        and card.source_verified is True
        and bool(card.license_reference.strip())
        and "synthetic" not in card.license_reference.lower()
    )
    if not license_ok:
        blockers.append("unverified_or_non_real_source")

    if card.snapshot_kind != "current":
        blockers.append("historical_snapshot_not_servable")

    districts = set(clean_frame["district_code"].astype(str))
    labels_valid = bool(card.district_labels) and all(
        isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip()
        for k, v in card.district_labels.items()
    )
    mapping_meta_ok = (
        True if mapping_metadata is None else _validate_mapping_metadata(mapping_metadata)
    )
    mapping_ok = (
        card.geography_version == "hcm_current_v1"
        and districts.issubset(card.district_labels)
        and labels_valid
        and mapping_meta_ok
    )
    if not mapping_ok:
        blockers.append("invalid_or_incomplete_district_mapping")

    active_count = sum(_is_true_bool(v) for v in clean_frame["active_at_snapshot"])
    valid_evidence = sum(
        not _is_missing(v) and not _contains_phone_pii(str(v))
        for v in clean_frame["availability_evidence_id"]
    )
    active_ok = active_count == len(clean_frame) and valid_evidence == len(clean_frame)
    if not active_ok:
        blockers.append("inactive_or_missing_active_evidence")

    freshness_ok = True
    for record in clean_frame.to_dict("records"):
        try:
            listing = Listing.model_validate(_clean_listing_record(record))
            listing.check_current(now)
        except (ValidationError, ValueError):
            freshness_ok = False
            break

    obs_series = pd.to_datetime(clean_frame["price_observed_at"], utc=True)
    snap_series = pd.to_datetime(clean_frame["source_snapshot_at"], utc=True)
    oldest_price_age_days = round((now - obs_series.min()).total_seconds() / 86400.0, 2)
    remaining_serving_days = round(SERVING_MAX_AGE_DAYS - oldest_price_age_days, 2)
    if oldest_price_age_days > SERVING_MAX_AGE_DAYS:
        freshness_ok = False
        blockers.append("stale_for_serving")
    elif not freshness_ok:
        blockers.append("stale_or_invalid_timestamps_for_publication")

    area_basis_consistent = clean_frame["area_basis"].nunique() == 1
    rep = representatives(clean_frame)
    n_groups = int(rep["property_group_id"].nunique())
    test_groups, supported_districts, underrepresented_districts = _district_coverage(clean_frame)
    coverage_ok = (
        area_basis_consistent
        and n_groups >= MARKET_MIN_TOTAL_GROUPS
        and test_groups >= MARKET_MIN_TEST_GROUPS
        and bool(supported_districts)
    )
    if not area_basis_consistent:
        blockers.append("mixed_area_basis")
    if n_groups < MARKET_MIN_TOTAL_GROUPS:
        blockers.append(f"insufficient_total_groups:{n_groups}<{MARKET_MIN_TOTAL_GROUPS}")
    if test_groups < MARKET_MIN_TEST_GROUPS:
        blockers.append(f"insufficient_test_groups:{test_groups}<{MARKET_MIN_TEST_GROUPS}")
    if not supported_districts:
        blockers.append("no_district_meets_min_train_groups")

    unique_evidence = {
        str(v).strip() for v in clean_frame["availability_evidence_id"] if not _is_missing(v)
    }

    return {
        "status": "PASS" if not blockers else "FAIL",
        "checked_at": now.isoformat(),
        "checks": {
            "license_and_source_verified": license_ok,
            "mapping_valid": mapping_ok,
            "freshness_valid": freshness_ok,
            "active_listings_verified": active_ok,
            "coverage_and_thresholds_met": coverage_ok,
        },
        "blockers": blockers,
        "freshness": {
            "data_as_of": obs_series.min().isoformat(),
            "data_latest_at": obs_series.max().isoformat(),
            "source_snapshot_at": snap_series.max().isoformat(),
            "oldest_price_age_days": oldest_price_age_days,
            "remaining_serving_days": remaining_serving_days,
            "publication_max_age_days": PUBLICATION_MAX_AGE_DAYS,
            "serving_max_age_days": SERVING_MAX_AGE_DAYS,
        },
        "active_summary": {
            "active_count": active_count,
            "total_rows": len(clean_frame),
            "unique_evidence_count": len(unique_evidence),
        },
        "coverage": {
            "n_groups": n_groups,
            "test_groups": test_groups,
            "supported_districts": supported_districts,
            "underrepresented_districts": underrepresented_districts,
            "area_basis": str(clean_frame["area_basis"].iloc[0]),
        },
    }


def build_release_dataset_card(
    card: DatasetCard,
    audit: dict[str, Any],
    *,
    raw_sha256: str,
    clean_sha256: str,
    source_owner: str,
    source_revision: str,
    mapping_metadata: dict[str, Any],
    audit_method: str,
    prepared_by: str,
    reviewed_by: str,
    area_basis: str,
    split_sha256: str | None = None,
    refresh_summary: dict[str, Any] | None = None,
    exposure_summary: dict[str, Any] | None = None,
    pre_demo_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """TV1-10: Assemble final release dataset card/manifest matching README data contract."""
    for label, digest in (("raw_sha256", raw_sha256), ("clean_sha256", clean_sha256)):
        if not _SHA256_RE.fullmatch(digest):
            raise ValueError(f"Invalid {label}")
    if split_sha256 is not None and not _SHA256_RE.fullmatch(split_sha256):
        raise ValueError("Invalid split_sha256")
    for label, value in (
        ("source_owner", source_owner),
        ("source_revision", source_revision),
        ("audit_method", audit_method),
        ("prepared_by", prepared_by),
        ("reviewed_by", reviewed_by),
        ("area_basis", area_basis),
    ):
        if not value.strip():
            raise ValueError(f"{label} must not be blank")
    if prepared_by.strip().lower() == reviewed_by.strip().lower():
        raise ValueError("Reviewer must be distinct from preparer")
    if not _validate_mapping_metadata(mapping_metadata):
        raise ValueError("Invalid mapping metadata")

    return {
        "schema_version": SCHEMA_VERSION,
        "timezone": "UTC",
        "display_timezone": "Asia/Ho_Chi_Minh",
        "cli_dataset_card": card.model_dump(),
        "source": {
            "owner": source_owner.strip(),
            "revision": source_revision.strip(),
            "license_reference": card.license_reference,
            "source_verified": card.source_verified,
        },
        "mapping": {
            "geography_version": card.geography_version,
            "source": mapping_metadata["source"].strip(),
            "effective_date": mapping_metadata["effective_date"].strip(),
            "version": mapping_metadata["version"].strip(),
            "sha256": mapping_metadata["sha256"].strip(),
        },
        "area_basis": area_basis.strip(),
        "hashes": {
            "raw_sha256": raw_sha256,
            "clean_sha256": clean_sha256,
            "split_sha256": split_sha256,
        },
        "audit": audit,
        "audit_method": audit_method.strip(),
        "refresh_summary": refresh_summary,
        "exposure_summary": exposure_summary,
        "pre_demo_check": pre_demo_check,
        "signoff": {
            "prepared_by": prepared_by.strip(),
            "reviewed_by": reviewed_by.strip(),
            "go_no_go": audit.get("go_no_go"),
        },
    }
