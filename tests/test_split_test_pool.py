"""split_groups(test_pool=...): a release test may only come from never-exposed groups."""

import pytest

from ml.data import audit_registry_exposure, split_groups
from ml.registry import initialize, record_groups


def ids(part):
    return set(part["property_group_id"])


def test_without_a_pool_the_split_is_unchanged(listings):
    assert ids(split_groups(listings)["test"]) == ids(split_groups(listings, None)["test"])


def test_test_groups_come_only_from_the_pool_and_splits_stay_disjoint(listings):
    pool = {f"synthetic_group_{i}" for i in range(0, 600, 2)}  # every second group
    parts = split_groups(listings, test_pool=pool)
    assert ids(parts["test"]) <= pool
    assert not ids(parts["train"]) & ids(parts["validation"])
    assert not ids(parts["test"]) & (ids(parts["train"]) | ids(parts["validation"]))
    assert len(ids(parts["train"]) | ids(parts["validation"]) | ids(parts["test"])) == 600


def test_pool_keeps_the_default_test_size_and_is_deterministic(listings):
    everything = set(listings["property_group_id"])
    default_size = len(split_groups(listings)["test"])
    pool = {f"synthetic_group_{i}" for i in range(0, 600, 3)}
    first = split_groups(listings, test_pool=pool)
    again = split_groups(listings, test_pool=list(reversed(sorted(pool))))
    assert len(first["test"]) == default_size
    assert len(split_groups(listings, test_pool=everything)["test"]) == default_size
    assert ids(first["test"]) == ids(again["test"])  # pool order does not matter


def test_too_small_a_pool_is_refused_instead_of_shrinking_the_test_set(listings):
    needed = len(split_groups(listings)["test"])
    pool = {f"synthetic_group_{i}" for i in range(needed - 1)}
    with pytest.raises(ValueError, match="test pool"):
        split_groups(listings, test_pool=pool)


def test_pool_ids_missing_from_the_snapshot_do_not_count(listings):
    needed = len(split_groups(listings)["test"])
    pool = {f"synthetic_group_{i}" for i in range(needed - 1)} | {"not_in_snapshot"}
    with pytest.raises(ValueError, match="test pool"):
        split_groups(listings, test_pool=pool)


def test_pool_is_matched_as_text_so_numeric_ids_work(listings):
    needed = len(split_groups(listings)["test"])
    frame = listings.assign(property_group_id=[f"{i:05d}" for i in range(len(listings))])
    pool = [f"{i:05d}" for i in range(needed)]
    assert ids(split_groups(frame, test_pool=pool)["test"]) == set(pool)


def test_pool_from_registry_audit_lets_reserve_test_succeed_where_default_split_fails(
    tmp_path, listings
):
    registry = tmp_path / "registry"
    initialize(registry)
    every = sorted(listings["property_group_id"])
    exposure = {"fit": every[:300], "tune": every[300:380], "evaluation": every[380:420]}
    record_groups(registry, exposure, run_id="run-001", actor="TV6")
    _, unexposed = audit_registry_exposure(listings, registry)
    assert len(unexposed) == 180

    # The plain split draws test groups at random, some already exposed: the registry refuses.
    plain_test = sorted(ids(split_groups(listings)["test"]))
    with pytest.raises(ValueError, match="exposed"):
        record_groups(registry, {"test_reserved": plain_test}, run_id="run-002", actor="TV6")

    # Restricted to the never-exposed pool, the same reservation is accepted.
    test = sorted(ids(split_groups(listings, test_pool=unexposed)["test"]))
    record_groups(registry, {"test_reserved": test}, run_id="run-002", actor="TV6")
