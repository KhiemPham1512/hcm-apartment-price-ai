"""Validate already-normalized listings; raw adapters belong to TV1."""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from ml.schema import FEATURES, ApartmentFeatures, Listing


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
