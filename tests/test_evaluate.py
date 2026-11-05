"""TV6 evaluation guards; synthetic technical fixtures only."""

import hashlib
import json
import subprocess
import sys

import joblib
import pandas as pd
import pytest

from ml.data import split_groups
from ml.train import fit_candidates


@pytest.fixture
def candidate_run(tmp_path, listings):
    splits = split_groups(listings)
    bundle = fit_candidates(splits["train"], splits["validation"])
    bundle["dataset_card"] = {"data_kind": "synthetic"}
    bundle["source_sha256"] = "synthetic-source-not-market-evidence"
    bundle["dataset_sha256"] = "synthetic-dataset-not-market-evidence"
    bundle["package_versions"] = {}
    splits["test"].to_csv(tmp_path / "holdout.csv", index=False)
    pd.concat(
        [
            part[["source_id", "listing_id", "property_group_id"]].assign(split=name)
            for name, part in splits.items()
        ]
    ).to_csv(tmp_path / "splits.csv", index=False)
    for name in ("holdout", "splits"):
        bundle[f"{name}_sha256"] = hashlib.sha256(
            (tmp_path / f"{name}.csv").read_bytes()
        ).hexdigest()
    joblib.dump(bundle, tmp_path / "candidates.joblib")
    return tmp_path


def evaluate_cli(run, *args):
    frozen = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "ml.freeze",
            "--run-dir",
            str(run),
            "--reviewer",
            "technical-test-reviewer",
        ],
        capture_output=True,
        text=True,
    )
    assert frozen.returncode == 0, frozen.stderr
    return subprocess.run(
        [sys.executable, "-B", "-m", "ml.evaluate", "--run-dir", str(run), *map(str, args)],
        capture_output=True,
        text=True,
    )


def test_real_candidate_requires_registry_before_evaluation(candidate_run):
    path = candidate_run / "candidates.joblib"
    bundle = joblib.load(path)
    # Synthetic fixture exercising the real-mode gate, not market evidence.
    bundle["dataset_card"]["data_kind"] = "real"
    joblib.dump(bundle, path)
    result = evaluate_cli(candidate_run)
    assert result.returncode != 0
    assert "Real evaluation requires registry" in result.stderr
    assert not (candidate_run / "evaluation.json").exists()


@pytest.fixture
def reserved_run(candidate_run):
    registry = candidate_run / "registry"
    groups = candidate_run / "test-groups.csv"
    splits = pd.read_csv(candidate_run / "splits.csv", dtype=str)
    splits.loc[splits["split"] == "test", ["property_group_id"]].to_csv(groups, index=False)
    for args in (
        ["init", "--registry-dir", registry],
        [
            "reserve-test",
            "--registry-dir",
            registry,
            "--groups-csv",
            groups,
            "--run-id",
            "fixture-run",
            "--actor",
            "TV6",
        ],
    ):
        result = subprocess.run(
            [sys.executable, "-B", "-m", "ml.registry", *map(str, args)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    return candidate_run, registry


@pytest.mark.parametrize("data_kind", ["synthetic", "real"])
def test_registered_evaluation_preserves_reservation_and_records_exposure(reserved_run, data_kind):
    run, registry = reserved_run
    bundle_path = run / "candidates.joblib"
    bundle = joblib.load(bundle_path)
    bundle["dataset_card"]["data_kind"] = data_kind  # Gate fixture, not market data.
    joblib.dump(bundle, bundle_path)
    original = {p.name: p.read_bytes() for p in (registry / "events").iterdir()}
    result = evaluate_cli(
        run, "--registry-dir", registry, "--run-id", "fixture-run", "--actor", "TV6"
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((run / "evaluation.json").read_text(encoding="utf-8"))
    assert report["registry_status"] == "checked"
    assert report["registry_run_id"] == "fixture-run"
    assert "actor" not in report and "groups" not in report
    event_path = registry / "events" / report["registry_event_id"]
    assert report["registry_event_sha256"] == hashlib.sha256(event_path.read_bytes()).hexdigest()
    event = json.loads(event_path.read_text(encoding="utf-8"))
    assert event["purpose"] == "evaluation"
    assert event["actor"] == "TV6"
    assert set(report["test"]) == {"baseline", "linear", "polynomial", "tree"}
    assert report["release_status"] == "candidate"
    assert len(list((registry / "events").iterdir())) == 2
    assert all((registry / "events" / name).read_bytes() == data for name, data in original.items())


@pytest.mark.parametrize(
    "problem", ["missing", "wrong_run", "groups", "exposed", "corrupt", "busy"]
)
def test_registry_violation_stops_before_label_parsing(reserved_run, problem):
    run, registry = reserved_run
    reservation = next((registry / "events").iterdir())
    run_id = "wrong-run" if problem == "wrong_run" else "fixture-run"
    if problem == "missing":
        reservation.unlink()
    elif problem == "groups":
        event = json.loads(reservation.read_text(encoding="utf-8"))
        event["groups"] = event["groups"][:-1]
        reservation.write_text(json.dumps(event), encoding="utf-8")
    elif problem == "exposed":
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "ml.registry",
                "record",
                "--registry-dir",
                str(registry),
                "--groups-csv",
                str(run / "test-groups.csv"),
                "--run-id",
                "another-run",
                "--actor",
                "TV2",
                "--purpose",
                "fit",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    elif problem == "corrupt":
        reservation.write_text("{}", encoding="utf-8")
    elif problem == "busy":
        (registry / ".write-lock").write_text("another writer", encoding="utf-8")
    before = {p.name: p.read_bytes() for p in (registry / "events").iterdir()}
    (run / "holdout.csv").write_bytes(b"\xfflabels must not be parsed")
    bundle_path = run / "candidates.joblib"
    bundle = joblib.load(bundle_path)
    bundle["holdout_sha256"] = hashlib.sha256((run / "holdout.csv").read_bytes()).hexdigest()
    joblib.dump(bundle, bundle_path)
    result = evaluate_cli(run, "--registry-dir", registry, "--run-id", run_id, "--actor", "TV6")
    assert result.returncode != 0
    assert "codec can't decode" not in result.stderr
    assert not (run / "evaluation.json").exists()
    assert {p.name: p.read_bytes() for p in (registry / "events").iterdir()} == before
    if problem == "busy":
        assert (registry / ".write-lock").read_text(encoding="utf-8") == "another writer"
    else:
        assert not (registry / ".write-lock").exists()


def test_failure_after_claim_keeps_exposure_and_refuses_retry(reserved_run):
    run, registry = reserved_run
    (run / "holdout.csv").write_bytes(b"\xffbad labels")
    bundle_path = run / "candidates.joblib"
    bundle = joblib.load(bundle_path)
    bundle["holdout_sha256"] = hashlib.sha256((run / "holdout.csv").read_bytes()).hexdigest()
    joblib.dump(bundle, bundle_path)
    args = ["--registry-dir", registry, "--run-id", "fixture-run", "--actor", "TV6"]
    first = evaluate_cli(run, *args)
    assert first.returncode != 0
    assert "codec can't decode" in first.stderr
    events = [json.loads(p.read_text(encoding="utf-8")) for p in (registry / "events").iterdir()]
    assert sorted(e["purpose"] for e in events) == ["evaluation", "test_reserved"]
    assert not (run / "evaluation.json").exists()
    assert not (registry / ".write-lock").exists()
    second = subprocess.run(
        [sys.executable, "-B", "-m", "ml.evaluate", "--run-dir", str(run), *map(str, args)],
        capture_output=True,
        text=True,
    )
    assert second.returncode != 0
    assert "exact unused test reservation" in second.stderr
    assert "codec can't decode" not in second.stderr
    assert len(list((registry / "events").iterdir())) == 2


def test_deleting_report_does_not_reset_evaluation_history(reserved_run):
    run, registry = reserved_run
    args = ["--registry-dir", registry, "--run-id", "fixture-run", "--actor", "TV6"]
    assert evaluate_cli(run, *args).returncode == 0
    (run / "evaluation.json").unlink()  # Technical fixture simulates losing the local report.
    result = subprocess.run(
        [sys.executable, "-B", "-m", "ml.evaluate", "--run-dir", str(run), *map(str, args)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "exact unused test reservation" in result.stderr
    assert not (run / "evaluation.json").exists()
    assert len(list((registry / "events").iterdir())) == 2


def test_concurrent_evaluations_consume_reservation_once(reserved_run):
    run, registry = reserved_run
    frozen = subprocess.run(
        [sys.executable, "-B", "-m", "ml.freeze", "--run-dir", str(run), "--reviewer", "TV6"],
        capture_output=True,
        text=True,
    )
    assert frozen.returncode == 0, frozen.stderr
    command = [
        sys.executable,
        "-B",
        "-m",
        "ml.evaluate",
        "--run-dir",
        str(run),
        "--registry-dir",
        str(registry),
        "--run-id",
        "fixture-run",
        "--actor",
        "TV6",
    ]
    processes = [
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)
    ]
    for process in processes:
        process.communicate(timeout=60)
    assert sum(p.returncode == 0 for p in processes) == 1
    assert (run / "evaluation.json").exists()
    assert len(list((registry / "events").iterdir())) == 2
    assert not (registry / ".write-lock").exists()


@pytest.mark.parametrize(
    "options",
    [
        ["--run-id", "fixture-run"],
        [
            "--registry-dir",
            "missing",
            "--run-id",
            "fixture-run",
            "--actor",
            " ",
        ],
    ],
)
def test_partial_or_blank_registry_options_are_rejected(candidate_run, options):
    result = evaluate_cli(candidate_run, *options)
    assert result.returncode != 0
    assert "Registry requires" in result.stderr
    assert not (candidate_run / "evaluation.json").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "unsupported"),
        ("schema_version", None),
        ("schema_version", 1),
        ("features", None),
        ("features", ["area_m2", "bedrooms", "bathrooms", "floor_level"]),
        ("features", ["district_code", "area_m2", "bedrooms", "bathrooms", "floor_level"]),
        ("features", ["area_m2", "bedrooms", "bathrooms", "floor_level", "asking_price_vnd"]),
        (
            "features",
            [
                "area_m2",
                "bedrooms",
                "bathrooms",
                "floor_level",
                "district_code",
                "listing_id",
            ],
        ),
    ],
)
def test_evaluation_rejects_incompatible_contract_before_opening_holdout(
    candidate_run, field, value
):
    bundle_path = candidate_run / "candidates.joblib"
    bundle = joblib.load(bundle_path)
    if value is None:
        bundle.pop(field)
    else:
        bundle[field] = value
    # Matching hashes/freeze cannot make an incompatible contract safe to evaluate.
    (candidate_run / "holdout.csv").write_bytes(b"\xffnot CSV labels")
    bundle["holdout_sha256"] = hashlib.sha256(
        (candidate_run / "holdout.csv").read_bytes()
    ).hexdigest()
    joblib.dump(bundle, bundle_path)

    result = evaluate_cli(candidate_run)

    assert result.returncode != 0
    assert "Candidate feature contract mismatch" in result.stderr
    assert "UnicodeDecodeError" not in result.stderr
    assert not (candidate_run / "evaluation.json").exists()


@pytest.mark.parametrize("missing", ["baseline", "linear", "polynomial", "tree"])
def test_evaluation_requires_baseline_and_all_three_models(candidate_run, missing):
    bundle_path = candidate_run / "candidates.joblib"
    bundle = joblib.load(bundle_path)
    del bundle["models"][missing]
    joblib.dump(bundle, bundle_path)

    result = evaluate_cli(candidate_run)

    assert result.returncode != 0
    assert "baseline, linear, polynomial and tree" in result.stderr
    assert not (candidate_run / "evaluation.json").exists()


@pytest.mark.parametrize("winner", ["baseline", "unknown", None])
def test_evaluation_rejects_winner_outside_the_three_required_models(candidate_run, winner):
    bundle_path = candidate_run / "candidates.joblib"
    bundle = joblib.load(bundle_path)
    bundle["winner"] = winner
    joblib.dump(bundle, bundle_path)

    result = evaluate_cli(candidate_run)

    assert result.returncode != 0
    assert "Validation winner must be linear, polynomial or tree" in result.stderr
    assert not (candidate_run / "evaluation.json").exists()


@pytest.mark.parametrize(
    "problem",
    [
        "group_leakage",
        "listing_leakage",
        "unknown_split",
        "missing_partition",
        "missing_column",
        "empty_identity",
        "duplicate_representative",
    ],
)
def test_evaluation_rejects_invalid_split_even_with_matching_checksum(candidate_run, problem):
    path = candidate_run / "splits.csv"
    splits = pd.read_csv(path)
    train_index = splits.index[splits["split"] == "train"][0]
    test_row = splits.loc[splits["split"] == "test"].iloc[0]
    if problem == "group_leakage":
        splits.loc[train_index, "property_group_id"] = test_row["property_group_id"]
    elif problem == "listing_leakage":
        splits.loc[train_index, ["source_id", "listing_id"]] = test_row[
            ["source_id", "listing_id"]
        ].values
    elif problem == "unknown_split":
        splits.loc[train_index, "split"] = "unrecognized"
    elif problem == "missing_partition":
        splits = splits.loc[splits["split"] != "validation"]
    elif problem == "missing_column":
        splits = splits.drop(columns="source_id")
    elif problem == "empty_identity":
        splits.loc[train_index, "listing_id"] = " "
    else:
        splits = pd.concat([splits, splits.iloc[[0]]], ignore_index=True)
    splits.to_csv(path, index=False)
    bundle_path = candidate_run / "candidates.joblib"
    bundle = joblib.load(bundle_path)
    bundle["splits_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    joblib.dump(bundle, bundle_path)

    result = evaluate_cli(candidate_run)

    assert result.returncode != 0
    assert "Invalid frozen split" in result.stderr
    assert not (candidate_run / "evaluation.json").exists()


@pytest.mark.parametrize(
    "problem", ["missing_row", "duplicate_row", "different_listing", "different_group"]
)
def test_evaluation_requires_exact_frozen_test_membership(candidate_run, problem):
    path = candidate_run / "holdout.csv"
    holdout = pd.read_csv(path)
    if problem == "missing_row":
        holdout = holdout.iloc[1:]
    elif problem == "duplicate_row":
        holdout = pd.concat([holdout, holdout.iloc[[0]]], ignore_index=True)
    elif problem == "different_listing":
        holdout.loc[0, "listing_id"] = "not-the-frozen-listing"
    else:
        holdout.loc[0, "property_group_id"] = "not-the-frozen-group"
    holdout.to_csv(path, index=False)
    bundle_path = candidate_run / "candidates.joblib"
    bundle = joblib.load(bundle_path)
    bundle["holdout_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    joblib.dump(bundle, bundle_path)

    result = evaluate_cli(candidate_run)

    assert result.returncode != 0
    assert "Holdout does not match frozen test membership" in result.stderr
    assert not (candidate_run / "evaluation.json").exists()


def test_evaluation_accepts_reordered_holdout_and_preserves_string_ids(candidate_run):
    splits = pd.read_csv(candidate_run / "splits.csv")
    holdout = pd.read_csv(candidate_run / "holdout.csv")
    for column in ("source_id", "listing_id", "property_group_id"):
        mapping = {value: f"00{index}" for index, value in enumerate(splits[column].unique())}
        holdout[column] = holdout[column].map(mapping)
        splits[column] = splits[column].map(mapping)
    splits.to_csv(candidate_run / "splits.csv", index=False)
    holdout.sample(frac=1, random_state=17).to_csv(candidate_run / "holdout.csv", index=False)
    bundle_path = candidate_run / "candidates.joblib"
    bundle = joblib.load(bundle_path)
    for name in ("holdout", "splits"):
        bundle[f"{name}_sha256"] = hashlib.sha256(
            (candidate_run / f"{name}.csv").read_bytes()
        ).hexdigest()
    joblib.dump(bundle, bundle_path)
    frozen_bytes = bundle_path.read_bytes()

    result = evaluate_cli(candidate_run)

    assert result.returncode == 0, result.stderr
    report = json.loads((candidate_run / "evaluation.json").read_text(encoding="utf-8"))
    assert set(report["test"]) == {"baseline", "linear", "polynomial", "tree"}
    assert report["winner_selected_by_validation"] == bundle["winner"]
    assert all(score["n"] == 90 for score in report["test"].values())
    assert report["release_status"] == "candidate"
    assert report["data_kind"] == "synthetic"
    assert report["registry_status"] == "not_checked_synthetic"
    assert bundle_path.read_bytes() == frozen_bytes
    assert report["freeze_reviewer"] == "technical-test-reviewer"
    assert (
        report["freeze_sha256"]
        == hashlib.sha256((candidate_run / "freeze.json").read_bytes()).hexdigest()
    )
