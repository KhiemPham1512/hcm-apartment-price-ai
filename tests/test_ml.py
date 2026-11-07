import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from ml.data import (
    assign_property_group_id,
    feature_frame,
    load_current_csv,
    parse_asking_price_vnd,
    prepare_raw_listings,
    representatives,
    split_groups,
)
from ml.evaluate import evaluate
from ml.models import make_model
from ml.schema import FEATURES, ApartmentFeatures
from ml.train import fit_candidates, metrics


def test_group_split_is_disjoint_reproducible_and_deduplicated(listings):
    duplicate = listings.iloc[[0]].assign(listing_id="different-ad-same-property")
    frame = pd.concat([listings, duplicate], ignore_index=True)
    first, second = split_groups(frame), split_groups(frame.sample(frac=1, random_state=7))
    groups = {name: set(part.property_group_id) for name, part in first.items()}
    assert not groups["train"] & groups["test"]
    assert not groups["train"] & groups["validation"]
    assert not groups["validation"] & groups["test"]
    assert sum(map(len, first.values())) == 600
    assert {name: set(part.property_group_id) for name, part in second.items()} == groups


def test_representative_selection_does_not_depend_on_target(listings):
    first = representatives(listings)
    changed = listings.assign(asking_price_vnd=listings.asking_price_vnd[::-1].to_numpy())
    assert first.listing_id.tolist() == representatives(changed).listing_id.tolist()


def test_feature_selection_excludes_target_and_identifiers(listings):
    x = feature_frame(listings)
    assert x.columns.tolist() == FEATURES
    assert "asking_price_vnd" not in x
    assert "property_group_id" not in x


@pytest.mark.parametrize("kind", ["baseline", "linear", "polynomial", "tree"])
def test_required_models_fit_and_allow_unknown_categories(listings, kind):
    splits = split_groups(listings)
    train, test = splits["train"], splits["test"]
    model = make_model(kind).fit(feature_frame(train), train.asking_price_vnd)
    inputs = feature_frame(test).assign(district_code="never-seen-before")
    assert np.isfinite(model.predict(inputs)).all()


def test_imputer_learns_only_training_data(listings):
    splits = split_groups(listings)
    train = splits["train"]
    model = make_model("linear").fit(feature_frame(train), train.asking_price_vnd)
    statistics = (
        model.named_steps["preprocess"].named_transformers_["numeric"]["impute"].statistics_.copy()
    )
    model.predict(feature_frame(splits["test"]).assign(area_m2=499))
    np.testing.assert_array_equal(
        statistics,
        model.named_steps["preprocess"].named_transformers_["numeric"]["impute"].statistics_,
    )
    assert statistics[0] == pytest.approx(train.area_m2.median())


def test_final_evaluation_preserves_validation_selected_winner(listings):
    splits = split_groups(listings)
    bundle = fit_candidates(splits["train"], splits["validation"])
    bundle["dataset_card"] = {"data_kind": "synthetic"}
    selected = bundle["winner"]
    report = evaluate(bundle, splits["test"].assign(asking_price_vnd=1.0))
    assert report["winner_selected_by_validation"] == selected
    assert set(report["test"]) == {"baseline", "linear", "polynomial", "tree"}
    assert report["release_status"] == "candidate"
    assert report["data_kind"] == "synthetic"


def test_metric_units_and_constant_target_handling():
    result = metrics([100, 200], [110, 190])
    assert result["rmse_vnd"] == 10
    assert result["mae_vnd"] == 10
    assert metrics([100, 100], [110, 110])["r2"] is None
    with pytest.raises(ValueError, match="Non-finite"):
        metrics([100], [float("nan")])


def test_normalized_csv_rejects_stale_and_mixed_area_basis(tmp_path, listings, now):
    path = tmp_path / "data.csv"
    listings.to_csv(path, index=False)
    assert len(load_current_csv(path, now)) == len(listings)
    listings.loc[0, "area_basis"] = "different_measurement"
    listings.to_csv(path, index=False)
    with pytest.raises(ValueError, match="Mixed area"):
        load_current_csv(path, now)


@pytest.mark.parametrize("value", [True, "70", -1, 501, float("nan"), float("inf")])
def test_area_strictness(value):
    with pytest.raises(ValidationError):
        ApartmentFeatures(area_m2=value, district_code="fixture_0")


def test_cli_handoff_preserves_frozen_holdout(tmp_path, listings):
    now = datetime.now(timezone.utc)
    data = listings.assign(
        published_at=now - timedelta(days=30),
        price_observed_at=now - timedelta(days=1),
        source_snapshot_at=now,
    )
    data.to_csv(tmp_path / "input.csv", index=False)
    card = {
        "dataset_version": "synthetic-integration-test",
        "data_kind": "synthetic",
        "geography_version": "hcm_current_v1",
        "license_reference": "synthetic test fixture",
        "source_verified": False,
        "grouping_version": "fixture-v1",
        "district_labels": {f"fixture_{i}": f"Fixture {i}" for i in range(3)},
    }
    card_path = tmp_path / "card.json"
    card_path.write_text(json.dumps(card), encoding="utf-8")
    run = tmp_path / "run"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "ml.train",
            "--csv",
            str(tmp_path / "input.csv"),
            "--dataset-card",
            str(card_path),
            "--output",
            str(run),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert not (run / "evaluation.json").exists()
    winner = json.loads((run / "selection.json").read_text())["winner"]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "ml.freeze",
            "--run-dir",
            str(run),
            "--reviewer",
            "synthetic-integration-reviewer",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    command = [sys.executable, "-m", "ml.evaluate", "--run-dir", str(run)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    report = json.loads((run / "evaluation.json").read_text())
    assert report["winner_selected_by_validation"] == winner
    assert report["release_status"] == "candidate"
    assert report["data_kind"] == "synthetic"
    assert subprocess.run(command, capture_output=True).returncode != 0
    (run / "evaluation.json").unlink()
    with (run / "holdout.csv").open("a") as handle:
        handle.write("\n")
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Frozen holdout" in result.stderr

@pytest.mark.parametrize(
    ("raw_price", "expected_vnd", "expected_reason"),
    [
        ("3,2 tỷ", 3_200_000_000.0, None),
        ("3.2 tỷ", 3_200_000_000.0, None),
        ("3 tỷ 250 triệu", 3_250_000_000.0, None),
        ("2850 triệu", 2_850_000_000.0, None),
        ("55 triệu/m2", None, "unconverted_price_per_m2"),
        ("60 tr/m²", None, "unconverted_price_per_m2"),
        ("15 triệu/tháng", None, "rental_or_installment_price"),
        ("Cho thuê 12 triệu", None, "rental_or_installment_price"),
        ("Giá thỏa thuận", None, "ambiguous_or_negotiable_price"),
        (-100, None, "invalid_asking_price"),
    ],
)
def test_tv1_price_parser_handles_units_and_quarantine_reasons(
    raw_price, expected_vnd, expected_reason
):
    val, reason = parse_asking_price_vnd(raw_price)
    assert val == expected_vnd
    assert reason == expected_reason


def test_tv1_group_assignment_ignores_price_and_avoids_area_district_only_merge(
    listings,
):
    raw = listings.iloc[:4].copy()
    raw["property_group_id"] = None
    raw["project_name_normalized"] = [
        "vin_grand_park",
        "vin_grand_park",
        None,
        None,
    ]
    raw["district_code"] = "thu_duc"
    raw["area_m2"] = 70.0
    raw["bedrooms"] = [2, 2, None, None]
    raw["bathrooms"] = [2, 2, None, None]
    raw["floor_level"] = [12, 12, None, None]

    groups_a = assign_property_group_id(raw)

    groups_b = assign_property_group_id(
        raw.assign(
            asking_price_vnd=[1e9, 9e9, 2e9, 8e9]
        )
    )

    assert groups_a.tolist() == groups_b.tolist()
    assert groups_a.iloc[0] == groups_a.iloc[1]
    assert groups_a.iloc[2] != groups_a.iloc[3]


def test_tv1_prepare_raw_listings_quarantines_invalid_rows_and_loads_cleanly(
    tmp_path, listings, now
):
    raw = listings.copy()
    raw["property_group_id"] = None
    raw["asking_price_vnd"] = "3,2 tỷ"

    raw.loc[0, "asking_price_vnd"] = "55 triệu/m2"
    raw.loc[1, "listing_type"] = "rent"
    raw.loc[2, "area_m2"] = 9.5
    raw.loc[3, "active_at_snapshot"] = False
    raw.loc[4, "listing_id"] = "lien_he_0901234567"
    raw.loc[5, "bathrooms"] = None

    dup = raw.iloc[[10]].copy()
    dup["price_observed_at"] = now - timedelta(days=3)

    raw_with_dup = pd.concat(
        [raw, dup],
        ignore_index=True,
    )

    clean_df, quarantine_df, audit = prepare_raw_listings(
        raw_with_dup,
        now=now,
    )

    assert len(quarantine_df) == 5

    assert set(quarantine_df["reason_code"]) == {
        "unconverted_price_per_m2",
        "non_sale_listing",
        "area_out_of_bounds",
        "missing_active_evidence",
        "invalid_identifier_or_pii",
    }

    assert audit["exact_duplicates_removed"] == 1

    assert pd.isna(
        clean_df.loc[
            clean_df["listing_id"] == "synthetic_listing_5",
            "bathrooms",
        ]
    ).all()

    assert audit["go_no_go"]["status"] == "GO"

    out_csv = tmp_path / "clean.csv"
    clean_df.to_csv(out_csv, index=False)

    reloaded = load_current_csv(
        out_csv,
        now=now,
    )

    assert len(reloaded) == len(clean_df)