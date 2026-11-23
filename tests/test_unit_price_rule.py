"""Owner decision 24/11/2026: an asking unit price outside 10-500 million VND/m2 is a data error."""

from datetime import datetime, timedelta, timezone

import pytest

from ml.data import load_current_csv, prepare_raw_listings

AREA = 100.0


def rows(listings, unit_prices):
    now = datetime.now(timezone.utc)
    frame = listings.iloc[: len(unit_prices)].assign(
        published_at=now - timedelta(days=30),
        price_observed_at=now - timedelta(days=1),
        source_snapshot_at=now,
        area_m2=AREA,
        asking_price_vnd=[AREA * u for u in unit_prices],
    )
    return now, frame.reset_index(drop=True)


def test_cleaning_quarantines_unit_prices_outside_the_bounds_and_keeps_the_bounds(listings):
    now, raw = rows(listings, [5e6, 10e6, 64e6, 500e6, 600e6, 348_571e6])
    clean, quarantine, _ = prepare_raw_listings(raw, now)
    assert sorted(clean["asking_price_vnd"] / AREA) == [10e6, 64e6, 500e6]
    assert set(quarantine["row_index"]) == {0, 4, 5}
    assert set(quarantine["reason_code"]) == {"implausible_unit_price"}


def test_loader_refuses_a_csv_that_still_contains_an_implausible_unit_price(tmp_path, listings):
    now, frame = rows(listings, [64e6, 600e6, 70e6])
    path = tmp_path / "unfiltered.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="Implausible unit price"):
        load_current_csv(path, now)


def test_loader_accepts_unit_prices_on_the_bounds(tmp_path, listings):
    now, frame = rows(listings, [10e6, 500e6, 64e6])
    path = tmp_path / "bounds.csv"
    frame.to_csv(path, index=False)
    assert len(load_current_csv(path, now)) == 3
