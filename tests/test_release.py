"""Release CLI gates; synthetic rows labelled real only to exercise the release path."""

import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import joblib
import pandas as pd
import pytest
from conftest import synthetic_listings
from fastapi.testclient import TestClient
from test_registry import cli, train_cli

from backend.app import configured_app, create_app
from backend.service import load_approved
from ml.schema import FEATURES

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


def test_released_package_serves_offline_prices_over_http(workspace, monkeypatch):
    """TV6-08: the package written by ml.release is what MODEL_DIR serves, price for price."""
    assert release(workspace, "TV6", "TV4").returncode == 0
    approved = workspace / "approved"
    monkeypatch.setenv("MODEL_DIR", str(approved))
    configured = configured_app()
    client = TestClient(configured)
    assert client.get("/health/ready").status_code == 200
    metadata = client.get("/api/v1/metadata").json()
    manifest = json.loads((approved / "manifest.json").read_text(encoding="utf-8"))
    assert metadata["serving_status"] == "ready"
    assert metadata["model_id"] == manifest["model_id"]
    codes = sorted(manifest["supported_districts"])
    assert [d["code"] for d in metadata["supported_districts"]] == codes
    rows = [
        {"area_m2": area, "district_code": code, "bedrooms": 2, "bathrooms": 1, "floor_level": None}
        for code in codes
        for area in (35.5, 80.0, 140.0)
    ]
    offline = joblib.load(approved / "pipeline.joblib").predict(
        pd.DataFrame(rows, columns=FEATURES)
    )
    # Same MODEL_DIR model with a high limit: the default 5-request burst would throttle a batch.
    batch = TestClient(create_app(configured.state.model, rate_limit_capacity=1000))
    for row, expected in zip(rows, offline, strict=True):
        response = batch.post("/api/v1/predictions", json=row)
        assert response.status_code == 200, response.text
        assert response.json()["predicted_price_vnd"] == pytest.approx(float(expected), rel=1e-12)
    assert client.get("/api/v1/report").json() == json.loads(
        (approved / "report.json").read_text(encoding="utf-8")
    )
    served = load_approved(approved)
    expired = served.manifest.data_as_of + timedelta(days=14, seconds=1)
    stale = TestClient(create_app(served, lambda: expired))
    assert stale.get("/api/v1/metadata").json()["serving_status"] == "stale"
    assert stale.post("/api/v1/predictions", json=rows[0]).json()["error"]["code"] == "stale_model"
    with (approved / "pipeline.joblib").open("ab") as handle:
        handle.write(b"tampered")
    unavailable = TestClient(configured_app())
    assert unavailable.get("/api/v1/metadata").json()["serving_status"] == "unavailable"
    assert unavailable.post("/api/v1/predictions", json=rows[0]).status_code == 503
