"""ml.train options for historical snapshots and a reservable test pool (synthetic fixtures)."""

import hashlib
import json

import pandas as pd
import pytest
from test_registry import train_cli


def run_dir(tmp_path):
    return tmp_path / "run"


def selection(tmp_path):
    return json.loads((run_dir(tmp_path) / "selection.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(("kind", "expected"), [(None, "current"), ("historical", "historical")])
def test_selection_records_the_snapshot_kind_of_the_card(tmp_path, listings, kind, expected):
    result = train_cli(tmp_path, listings, "synthetic", snapshot_kind=kind)
    assert result.returncode == 0, result.stderr
    assert selection(tmp_path)["snapshot_kind"] == expected


def write_pool(tmp_path, groups, encoding="utf-8"):
    path = tmp_path / "pool.csv"
    path.write_text("property_group_id\n" + "\n".join(groups) + "\n", encoding=encoding)
    return path


def test_test_pool_restricts_the_frozen_holdout_and_is_hashed(tmp_path, listings):
    pool = write_pool(tmp_path, [f"synthetic_group_{i}" for i in range(0, 600, 2)])
    result = train_cli(tmp_path, listings, "synthetic", "--test-pool-csv", pool)
    assert result.returncode == 0, result.stderr
    holdout = pd.read_csv(run_dir(tmp_path) / "holdout.csv")
    assert set(holdout["property_group_id"]) <= {f"synthetic_group_{i}" for i in range(0, 600, 2)}
    assert selection(tmp_path)["test_pool_sha256"] == hashlib.sha256(pool.read_bytes()).hexdigest()


def test_without_a_pool_the_hash_is_null(tmp_path, listings):
    assert train_cli(tmp_path, listings, "synthetic").returncode == 0
    assert selection(tmp_path)["test_pool_sha256"] is None


def test_pool_with_a_windows_bom_is_accepted(tmp_path, listings):
    pool = write_pool(
        tmp_path, [f"synthetic_group_{i}" for i in range(0, 600, 2)], encoding="utf-8-sig"
    )
    assert train_cli(tmp_path, listings, "synthetic", "--test-pool-csv", pool).returncode == 0


@pytest.mark.parametrize(
    ("problem", "message"),
    [
        ("too_small", "test pool"),
        ("no_column", "property_group_id column"),
        ("blank_id", "invalid"),
        ("duplicate_id", "invalid"),
    ],
)
def test_bad_pool_is_refused_before_any_output(tmp_path, listings, problem, message):
    ids = [f"synthetic_group_{i}" for i in range(0, 600, 2)]
    pool = tmp_path / "pool.csv"
    if problem == "too_small":
        write_pool(tmp_path, ids[:10])
    elif problem == "no_column":
        pool.write_text("group\n" + "\n".join(ids) + "\n", encoding="utf-8")
    elif problem == "blank_id":
        write_pool(tmp_path, [*ids, "  "])
    else:
        write_pool(tmp_path, [*ids, ids[0]])
    result = train_cli(tmp_path, listings, "synthetic", "--test-pool-csv", pool)
    assert result.returncode != 0 and message in result.stderr, result.stderr
    assert not run_dir(tmp_path).exists()


def test_audit_pool_train_and_reserve_test_work_end_to_end(tmp_path, listings):
    """TV1 audit -> pool CSV -> ml.train --test-pool-csv -> reserve-test of the frozen test set."""
    from ml.data import audit_registry_exposure, export_unexposed_test_candidates
    from ml.registry import initialize, record_groups

    registry = tmp_path / "registry"
    initialize(registry)
    every = sorted(listings["property_group_id"])
    record_groups(registry, {"fit": every[:420]}, run_id="run-001", actor="TV6")
    _, unexposed = audit_registry_exposure(listings, registry)
    pool = export_unexposed_test_candidates(unexposed, tmp_path / "pool.csv")

    args = ["--registry-dir", registry, "--run-id", "run-002", "--actor", "TV2"]
    result = train_cli(tmp_path, listings, "synthetic", *args, "--test-pool-csv", pool)
    assert result.returncode == 0, result.stderr

    splits = pd.read_csv(run_dir(tmp_path) / "splits.csv", dtype=str)
    test_groups = splits.loc[splits["split"] == "test", "property_group_id"].tolist()
    assert set(test_groups) <= set(unexposed)
    record_groups(registry, {"test_reserved": test_groups}, run_id="run-002", actor="TV6")
