"""Freeze/evaluate CLI contract; byte fixtures are not market artifacts."""

import hashlib
import json
import subprocess
import sys

import pytest


def freeze_cli(run, reviewer="test-reviewer"):
    return subprocess.run(
        [sys.executable, "-B", "-m", "ml.freeze", "--run-dir", str(run), "--reviewer", reviewer],
        capture_output=True,
        text=True,
    )


def test_freeze_records_bytes_without_loading_model_or_evaluating_labels(tmp_path):
    contents = {
        "candidates.joblib": b"not a serialized model",
        "splits.csv": b"private split bytes",
        "holdout.csv": b"private labels: do not parse",
    }
    for name, data in contents.items():
        (tmp_path / name).write_bytes(data)
    result = freeze_cli(tmp_path)
    assert result.returncode == 0, result.stderr
    record = json.loads((tmp_path / "freeze.json").read_text(encoding="utf-8"))
    assert record["reviewer"] == "test-reviewer"
    assert record["artifacts"] == {
        name: hashlib.sha256(data).hexdigest() for name, data in contents.items()
    }
    assert not (tmp_path / "evaluation.json").exists()
    assert all((tmp_path / name).read_bytes() == data for name, data in contents.items())


@pytest.mark.parametrize(
    "problem", ["already_frozen", "already_evaluated", "blank_reviewer", "missing_artifact"]
)
def test_freeze_refuses_invalid_lifecycle_without_overwriting_evidence(tmp_path, problem):
    for name in ("candidates.joblib", "splits.csv", "holdout.csv"):
        (tmp_path / name).write_bytes(b"fixture")
    record = tmp_path / "freeze.json"
    if problem == "already_frozen":
        record.write_text("original freeze", encoding="utf-8")
    elif problem == "already_evaluated":
        (tmp_path / "evaluation.json").write_text("original report", encoding="utf-8")
    elif problem == "missing_artifact":
        (tmp_path / "splits.csv").unlink()
    result = freeze_cli(tmp_path, " " if problem == "blank_reviewer" else "test-reviewer")
    assert result.returncode != 0
    if problem == "already_frozen":
        assert record.read_text(encoding="utf-8") == "original freeze"
    else:
        assert not record.exists()
    if problem == "already_evaluated":
        assert (tmp_path / "evaluation.json").read_text(encoding="utf-8") == "original report"


@pytest.mark.parametrize(
    "problem",
    ["missing_freeze", "candidates.joblib", "splits.csv", "holdout.csv", "malformed_freeze"],
)
def test_evaluate_rejects_unfrozen_or_changed_bytes_before_loading_model(tmp_path, problem):
    for name in ("candidates.joblib", "splits.csv", "holdout.csv"):
        (tmp_path / name).write_bytes(b"not deserializable; must reject before loading")
    if problem != "missing_freeze":
        assert freeze_cli(tmp_path).returncode == 0
        if problem == "malformed_freeze":
            (tmp_path / "freeze.json").write_text("{}", encoding="utf-8")
        else:
            with (tmp_path / problem).open("ab") as output:
                output.write(b"changed after review")
    result = subprocess.run(
        [sys.executable, "-B", "-m", "ml.evaluate", "--run-dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Freeze verification failed" in result.stderr
    assert not (tmp_path / "evaluation.json").exists()
