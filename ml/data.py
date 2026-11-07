"""Validate already-normalized listings; raw adapters belong to TV1."""

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import ValidationError
from sklearn.model_selection import GroupShuffleSplit

from ml.schema import (
    FEATURES,
    MIN_DISTRICT_GROUPS,
    SCHEMA_VERSION,
    ApartmentFeatures,
    Listing,
)

_PRICE_PER_M2_RE = re.compile(r"(/\s*m2|/\s*m²|m2|m²|mét\s*vuông)", re.IGNORECASE)
_RENTAL_RE = re.compile(
    r"(/\s*tháng|/\s*thang|thuê|thue|trả\s*góp|tra\s*gop)", re.IGNORECASE
)
_NEGOTIABLE_RE = re.compile(
    r"(thỏa\s*thuận|thoa\s*thuan|liên\s*hệ|lien\s*he|inbox)", re.IGNORECASE
)
_TY_TRIEU_RE = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s*t[ỷy]\s*(\d+(?:[.,]\d+)?)?\s*(?:triệu|trieu|tr)?\s*$",
    re.IGNORECASE,
)
_UNIT_VALUE_RE = re.compile(
    r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*(tỷ|ty|triệu|trieu|tr|nghìn|nghin|ngàn|ngan|vnd|đ|d)?\s*$",
    re.IGNORECASE,
)
_AREA_RANGE_RE = re.compile(r"\d+\s*[-~–]\s*\d+")
_AREA_RE = re.compile(
    r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*(?:m2|m²|sqm)?\s*$", re.IGNORECASE
)
_PHONE_RE = re.compile(r"(?<!\d)(?:0|\+?84)\d{9,10}(?!\d)")

MARKET_MIN_TOTAL_GROUPS = 500
MARKET_MIN_TEST_GROUPS = 75


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


def _parse_optional_int(
    value: Any, minimum: int, maximum: int
) -> tuple[int | None, bool]:
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
        has_structure = not (
            _is_missing(beds) and _is_missing(baths) and _is_missing(floor)
        )
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
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Normalize raw records into contract-compliant listings and a quarantine table."""
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
            validated.check_current(now)
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
        empty_clean = pd.DataFrame(columns= list(Listing.model_fields.keys()))
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
        dominant_basis = (
            expected_area_basis or str(clean_df["area_basis"].mode().iloc[0])
        )
        mismatch_mask = clean_df["area_basis"] != dominant_basis
        if mismatch_mask.any():
            mismatched = clean_df.loc[mismatch_mask].copy()
            mismatched["reason_code"] = "inconsistent_area_basis"
            quarantine_df = pd.concat(
                [quarantine_df, mismatched], ignore_index=True
            )
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
            str(k): int(v)
            for k, v in quarantine_frame["reason_code"].value_counts().items()
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
        train_counts = splits["train"].groupby("district_code")[
            "property_group_id"
        ].nunique()
        supported_districts = sorted(
            str(code)
            for code, count in train_counts.items()
            if int(count) >= MIN_DISTRICT_GROUPS
        )

    obs_series = pd.to_datetime(clean_frame["price_observed_at"], utc=True)
    pub_series = pd.to_datetime(clean_frame["published_at"], utc=True)
    snap_series = pd.to_datetime(clean_frame["source_snapshot_at"], utc=True)

    listing_ages = (snap_series - pub_series).dt.total_seconds() / 86400.0
    price_ages = (now - obs_series).dt.total_seconds() / 86400.0

    blockers: list[str] = []
    if n_groups < MARKET_MIN_TOTAL_GROUPS:
        blockers.append(
            f"insufficient_total_groups:{n_groups}<{MARKET_MIN_TOTAL_GROUPS}"
        )
    if test_groups < MARKET_MIN_TEST_GROUPS:
        blockers.append(
            f"insufficient_test_groups:{test_groups}<{MARKET_MIN_TEST_GROUPS}"
        )
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


def load_current_csv(path: Path, now: datetime) -> pd.DataFrame:
    frame = pd.read_csv(path)
    rows = []
    for record in frame.to_dict("records"):
        record = {
            key: None if isinstance(value, float) and np.isnan(value) else value
            for key, value in record.items()
        }
        for key in ("bedrooms", "bathrooms", "floor_level"):
            value = record.get(key)
            if isinstance(value, float) and np.isfinite(value) and value.is_integer():
                record[key] = int(value)
        listing = Listing.model_validate(record)
        listing.check_current(now)
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