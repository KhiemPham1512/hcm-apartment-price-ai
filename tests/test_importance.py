"""Validation-only permutation importance and ablation (synthetic: price depends only on area)."""

import hashlib
import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
from test_registry import train_cli

MODELS = ("linear", "polynomial", "tree")


def make_run(tmp_path, listings):
    result = train_cli(tmp_path, listings, "synthetic")
    assert result.returncode == 0, result.stderr
    return tmp_path / "run", tmp_path / "input.csv", tmp_path / "card.json"


def importance_cli(run, csv, card, *args):
    command = [sys.executable, "-B", "-m", "ml.importance", "--run-dir", run, "--csv", csv]
    command += ["--dataset-card", card, *args]
    return subprocess.run(list(map(str, command)), capture_output=True, text=True)


def same(a, b):
    """Equal up to float noise (multithreaded linear algebra is not bit-reproducible)."""
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, float):
        return a == pytest.approx(b, rel=1e-9, abs=1e-6)
    return a == b


def analysed(tmp_path, listings):
    run, csv, card = make_run(tmp_path, listings)
    result = importance_cli(run, csv, card)
    assert result.returncode == 0, result.stderr
    return run, json.loads((run / "importance.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", MODELS)
def test_the_only_real_driver_ranks_first_and_removing_it_hurts(tmp_path, listings, name):
    _, report = analysed(tmp_path, listings)
    model = report["models"][name]
    ranking = model["permutation"]
    assert [row["rank"] for row in ranking] == sorted(row["rank"] for row in ranking)
    assert ranking[0]["feature"] == "area_m2"
    others = max(row["importance_mean_vnd"] for row in ranking[1:])
    assert ranking[0]["importance_mean_vnd"] > 5 * max(others, 1.0)
    ablation = {row["removed"]: row for row in model["ablation"]}
    assert set(ablation) == {"area_m2", "district_code", "area_m2+district_code"}
    assert ablation["area_m2"]["validation_rmse_vnd"] > 10 * max(model["validation_rmse_vnd"], 1e6)
    assert (
        ablation["district_code"]["delta_vs_full_vnd"]
        < 0.2 * ablation["area_m2"]["delta_vs_full_vnd"]
    )


def test_it_uses_validation_rows_only_and_never_needs_the_holdout(tmp_path, listings):
    run, csv, card = make_run(tmp_path, listings)
    splits = pd.read_csv(run / "splits.csv", dtype=str)
    (run / "holdout.csv").unlink()  # the analysis must not depend on, or read, the test rows
    assert importance_cli(run, csv, card).returncode == 0
    report = json.loads((run / "importance.json").read_text(encoding="utf-8"))
    assert report["n_validation"] == int((splits["split"] == "validation").sum())
    assert report["n_train"] == int((splits["split"] == "train").sum())


def test_a_constant_feature_has_exactly_zero_importance(tmp_path, listings):
    _, report = analysed(tmp_path, listings.assign(floor_level=np.nan))
    for name in MODELS:
        floor = next(
            r for r in report["models"][name]["permutation"] if r["feature"] == "floor_level"
        )
        assert floor["importance_mean_vnd"] == 0.0 and floor["importance_std_vnd"] == 0.0


def test_report_records_lineage_and_is_reproducible(tmp_path, listings):
    run, csv, card = make_run(tmp_path, listings)
    assert importance_cli(run, csv, card).returncode == 0
    assert importance_cli(run, csv, card, "--output", tmp_path / "again.json").returncode == 0
    first = json.loads((run / "importance.json").read_text(encoding="utf-8"))
    again = json.loads((tmp_path / "again.json").read_text(encoding="utf-8"))
    assert same(first, again)
    assert first["snapshot_kind"] == "current" and first["seed"] == 42 and first["repeats"] == 10
    assert (
        first["candidate_sha256"]
        == hashlib.sha256((run / "candidates.joblib").read_bytes()).hexdigest()
    )
    assert first["dataset_sha256"] == hashlib.sha256(csv.read_bytes()).hexdigest()
    assert first["winner_selected_by_validation"] in MODELS
    assert first["limits"], "interpretation limits must be stated"


@pytest.mark.parametrize(
    "problem", ["csv_changed", "card_changed", "splits_changed", "output_exists"]
)
def test_inputs_that_do_not_match_the_candidate_are_refused(tmp_path, listings, problem):
    run, csv, card = make_run(tmp_path, listings)
    message = "does not match"
    if problem == "csv_changed":
        with csv.open("a", encoding="utf-8") as handle:
            handle.write("\n")
    elif problem == "card_changed":
        data = json.loads(card.read_text(encoding="utf-8"))
        card.write_text(json.dumps({**data, "dataset_version": "other"}), encoding="utf-8")
    elif problem == "splits_changed":
        with (run / "splits.csv").open("a", encoding="utf-8") as handle:
            handle.write("\n")
    else:
        (run / "importance.json").write_text("{}", encoding="utf-8")
        message = "already exists"
    result = importance_cli(run, csv, card)
    assert result.returncode != 0 and message in result.stderr, result.stderr
    if problem != "output_exists":
        assert not (run / "importance.json").exists()


def test_report_does_not_change_when_only_the_test_labels_change(tmp_path, listings):
    """The core guarantee: test labels cannot influence the analysis."""
    import shutil

    import joblib

    run, csv, card = make_run(tmp_path, listings)
    splits = pd.read_csv(run / "splits.csv", dtype=str)
    test_ids = set(splits.loc[splits["split"] == "test", "listing_id"])
    frame = pd.read_csv(csv)
    frame.loc[frame["listing_id"].isin(test_ids), "asking_price_vnd"] *= 3
    changed = tmp_path / "input_with_other_test_labels.csv"
    frame.to_csv(changed, index=False)
    other_run = tmp_path / "run_other"
    shutil.copytree(run, other_run)
    bundle = joblib.load(other_run / "candidates.joblib")
    bundle["dataset_sha256"] = hashlib.sha256(changed.read_bytes()).hexdigest()
    joblib.dump(bundle, other_run / "candidates.joblib")

    assert importance_cli(run, csv, card).returncode == 0
    assert importance_cli(other_run, changed, card).returncode == 0
    first = json.loads((run / "importance.json").read_text(encoding="utf-8"))
    second = json.loads((other_run / "importance.json").read_text(encoding="utf-8"))
    assert same(first["models"], second["models"])
