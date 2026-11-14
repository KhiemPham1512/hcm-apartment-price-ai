"""Release CLI gates; synthetic rows labelled real only to exercise the release path."""

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import pytest
from conftest import synthetic_listings
from test_registry import cli, train_cli

from backend.service import load_approved

REGISTRY = ["--run-id", "r1", "--actor", "TV6"]


def run_module(*args):
    return subprocess.run(
        [sys.executable, "-B", "-m", *map(str, args)], capture_output=True, text=True
    )


@pytest.fixture(scope="module")
def evaluated(tmp_path_factory):
    base = tmp_path_factory.mktemp("release")
    registry = base / "registry"
    assert cli("init", "--registry-dir", registry).returncode == 0
    listings = synthetic_listings(datetime.now(timezone.utc))
    trained = train_cli(
        base, listings, "real", "--registry-dir", registry, *REGISTRY, source_verified=True
    )
    assert trained.returncode == 0, trained.stderr
    run = base / "run"
    rows = (run / "splits.csv").read_text(encoding="utf-8").splitlines()[1:]
    groups = base / "test-groups.csv"
    groups.write_text(
        "property_group_id\n" + "\n".join(r.split(",")[2] for r in rows if r.endswith(",test")),
        encoding="utf-8",
    )
    steps = [
        ["ml.registry", "reserve-test", "--registry-dir", registry, "--groups-csv", groups],
        ["ml.freeze", "--run-dir", run, "--reviewer", "TV6"],
        ["ml.evaluate", "--run-dir", run, "--registry-dir", registry, *REGISTRY],
    ]
    for step in steps:
        result = run_module(*step, *(REGISTRY if step[1] == "reserve-test" else []))
        assert result.returncode == 0, result.stderr
    return base


@pytest.fixture
def workspace(evaluated, tmp_path):
    for name in ("run", "input.csv"):
        source = evaluated / name
        (shutil.copytree if source.is_dir() else shutil.copy)(source, tmp_path / name)
    return tmp_path


def release(workspace, *reviewers):
    reviewer_args = [arg for name in reviewers for arg in ("--reviewer", name)]
    return run_module(
        "ml.release",
        "--run-dir",
        workspace / "run",
        "--csv",
        workspace / "input.csv",
        "--output",
        workspace / "approved",
        *reviewer_args,
    )


def test_release_packages_frozen_evaluated_winner_for_serving(workspace):
    result = release(workspace, "TV6", "TV4")
    assert result.returncode == 0, result.stderr
    served = load_approved(workspace / "approved")
    selection = json.loads((workspace / "run" / "selection.json").read_text(encoding="utf-8"))
    evaluation = json.loads((workspace / "run" / "evaluation.json").read_text(encoding="utf-8"))
    manifest = served.manifest
    assert manifest.release_status == "approved" and manifest.run_id == "r1"
    assert manifest.model_id == f"r1-{selection['winner']}"
    assert manifest.test_rmse_vnd == evaluation["test"][selection["winner"]]["rmse_vnd"]
    assert manifest.n_groups == 600 and manifest.reviewers == ["TV6", "TV4"]
    assert set(manifest.supported_districts) == {f"fixture_{i}" for i in range(3)}
    assert served.report["validation"] == selection["validation"]
    served.require_ready(datetime.now(timezone.utc))


@pytest.mark.parametrize(
    ("problem", "message"),
    [
        ("not_evaluated", "evaluation.json"),
        ("one_reviewer", "Distinct operational reviewers"),
        ("dataset_changed", "Dataset does not match"),
        ("evaluation_tampered", "does not match the frozen candidate"),
        ("registry_unchecked", "registry-checked evaluation"),
        ("output_exists", "Output already exists"),
    ],
)
def test_release_gate_failure_writes_no_package(workspace, problem, message):
    run = workspace / "run"
    reviewers = ["TV6", "TV4"]
    if problem == "not_evaluated":
        (run / "evaluation.json").unlink()
    elif problem == "one_reviewer":
        reviewers = ["TV6", "TV6"]
    elif problem == "dataset_changed":
        with (workspace / "input.csv").open("a", encoding="utf-8") as handle:
            handle.write("\n")
    elif problem in ("evaluation_tampered", "registry_unchecked"):
        report = json.loads((run / "evaluation.json").read_text(encoding="utf-8"))
        if problem == "evaluation_tampered":
            report["candidate_sha256"] = "0" * 64
        else:
            report["registry_status"] = "not_checked_synthetic"
        (run / "evaluation.json").write_text(json.dumps(report), encoding="utf-8")
    else:
        (workspace / "approved").mkdir()
    result = release(workspace, *reviewers)
    assert result.returncode != 0 and message in result.stderr, result.stderr
    approved = workspace / "approved"
    assert not approved.exists() or not any(approved.iterdir())
