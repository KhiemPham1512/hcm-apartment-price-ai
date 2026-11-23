"""TV6 release: package a frozen, registry-evaluated winner only when every gate passes."""

import argparse
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd

# The serving contract is the release gate, so offline packaging and HTTP cannot drift.
from backend.service import Manifest, load_approved
from ml.data import load_current_csv, split_groups
from ml.freeze import verify_freeze
from ml.schema import MIN_DISTRICT_GROUPS, NUMERIC_FEATURES


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(run_dir: Path, csv: Path, reviewers: list[str], now: datetime):
    frozen = verify_freeze(run_dir)
    report = json.loads((run_dir / "evaluation.json").read_text(encoding="utf-8"))
    candidate = (run_dir / "candidates.joblib").read_bytes()
    if report.get("candidate_sha256") != _sha256(candidate) or (
        report.get("freeze_sha256") != frozen["sha256"]
    ):
        raise ValueError("Evaluation does not match the frozen candidate")
    if report.get("registry_status") != "checked":
        raise ValueError("Release requires a registry-checked evaluation")
    # Local trusted artifacts only, same as the evaluator.
    bundle = joblib.load(io.BytesIO(candidate))
    if bundle["dataset_card"].get("snapshot_kind", "current") != "current":
        raise ValueError("Historical snapshot cannot be released for current-price serving")
    if _sha256(csv.read_bytes()) != bundle["dataset_sha256"]:
        raise ValueError("Dataset does not match the candidate")
    frame = load_current_csv(csv, now)  # enforces publication freshness at release time
    train = split_groups(frame)["train"]
    splits = pd.read_csv(run_dir / "splits.csv", dtype=str)
    if set(train["property_group_id"]) != set(
        splits.loc[splits["split"] == "train", "property_group_id"]
    ):
        raise ValueError("Dataset split does not reproduce the frozen train groups")
    card, winner = bundle["dataset_card"], bundle["winner"]
    counts = train.groupby("district_code")["property_group_id"].nunique()
    observed = pd.to_datetime(frame["price_observed_at"], utc=True)
    published = pd.to_datetime(frame["published_at"], utc=True)
    snapshot = pd.to_datetime(frame["source_snapshot_at"], utc=True)
    buffer = io.BytesIO()
    joblib.dump(bundle["models"][winner], buffer)
    pipeline = buffer.getvalue()
    run_id, test = report["registry_run_id"], report["test"][winner]
    manifest = Manifest(
        release_status="approved",
        data_kind=card["data_kind"],
        source_verified=card["source_verified"],
        schema_version=bundle["schema_version"],
        model_id=f"{run_id}-{winner}",
        run_id=run_id,
        dataset_version=card["dataset_version"],
        pipeline_sha256=_sha256(pipeline),
        features=bundle["features"],
        data_as_of=observed.min().to_pydatetime(),
        data_latest_at=observed.max().to_pydatetime(),
        source_snapshot_at=snapshot.max().to_pydatetime(),
        data_window_start=observed.min().to_pydatetime(),
        data_window_end=observed.max().to_pydatetime(),
        listing_window_start=published.min().to_pydatetime(),
        listing_window_end=published.max().to_pydatetime(),
        age_summary={
            "median_listing_age_days": float(((snapshot - published).dt.days).median()),
            "median_price_age_days": float(((now - observed).dt.days).median()),
            "computed_at": now.isoformat(),
        },
        area_basis=str(frame["area_basis"].iloc[0]),
        supported_districts={
            code: card["district_labels"][code]
            for code, n in counts.items()
            if n >= MIN_DISTRICT_GROUPS
        },
        training_ranges={
            key: (float(train[key].min()), float(train[key].max()))
            for key in NUMERIC_FEATURES
            if train[key].notna().any()
        },
        n_groups=frame["property_group_id"].nunique(),
        test_n=test["n"],
        test_rmse_vnd=test["rmse_vnd"],
        baseline_test_rmse_vnd=report["test"]["baseline"]["rmse_vnd"],
        test_r2=test["r2"],
        invalid_output_count=test["invalid_output_count"],
        reviewers=reviewers,
    )
    public = {
        **report,
        "run_id": run_id,
        "model_id": manifest.model_id,
        "dataset_version": manifest.dataset_version,
        "validation": bundle["validation"],
    }
    return manifest, pipeline, public


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewer", action="append", required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; release into a new directory")
    try:
        manifest, pipeline, report = build(
            args.run_dir, args.csv, args.reviewer, datetime.now(timezone.utc)
        )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(f"Release refused: {exc}")
    args.output.mkdir(parents=True)
    (args.output / "pipeline.joblib").write_bytes(pipeline)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    (args.output / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    load_approved(args.output)
    print("Approved package written; the API serves it only after MODEL_DIR points here.")


if __name__ == "__main__":
    main()
