"""Geography selection must be explicit for current-snapshot datasets."""

import pytest
from pydantic import ValidationError

from ml.schema import DatasetCard

CARD = {
    "dataset_version": "synthetic-current-scope-test",
    "data_kind": "synthetic",
    "license_reference": "synthetic technical fixture",
    "grouping_version": "fixture-v1",
    "district_labels": {"fixture_area": "Synthetic area"},
}


def test_dataset_card_accepts_explicit_current_geography():
    card = DatasetCard(**CARD, geography_version="hcm_current_v1")
    assert card.geography_version == "hcm_current_v1"


def test_dataset_card_does_not_silently_choose_a_geography():
    with pytest.raises(ValidationError):
        DatasetCard(**CARD)


def test_dataset_card_rejects_the_retired_geography():
    with pytest.raises(ValidationError):
        DatasetCard(**CARD, geography_version="hcm_pre2025_v1")
