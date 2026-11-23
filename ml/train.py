"""Fit và lựa chọn mô hình chỉ dùng validation; không bao giờ đánh giá nhãn test."""

import argparse
import csv
import hashlib
import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

from ml.data import feature_frame, load_current_csv, split_groups
from ml.models import make_model
from ml.registry import record_groups
from ml.schema import FEATURES, NUMERIC_FEATURES, SCHEMA_VERSION, DatasetCard


def metrics(y, predictions) -> dict:
    y = np.asarray(y, dtype=float)
    predictions = np.asarray(predictions, dtype=float)
    if not np.isfinite(predictions).all():
        raise ValueError("Non-finite predictions")
    valid_r2 = len(y) >= 2 and np.ptp(y) > 0
    return {
        "rmse_vnd": float(root_mean_squared_error(y, predictions)),
        "mae_vnd": float(mean_absolute_error(y, predictions)),
        "r2": float(r2_score(y, predictions)) if valid_r2 else None,
        "r2_reason": None if valid_r2 else "insufficient_or_constant_target",
        "n": len(y),
        "invalid_output_count": int((predictions <= 0).sum()),
    }


def select_winner(scores: dict[str, dict]) -> str:
    best = min(scores[name]["rmse_vnd"] for name in ("linear", "polynomial", "tree"))
    for name in ("linear", "polynomial", "tree"):
        if scores[name]["rmse_vnd"] <= best * 1.01:
            return name
    raise ValueError("No valid candidate")


def fit_candidates(train: pd.DataFrame, validation: pd.DataFrame) -> dict:
    x_train, x_val = feature_frame(train), feature_frame(validation)
    # An all-missing numeric feature is kept as a constant column and reported, not dropped.
    uninformative_features = [f for f in NUMERIC_FEATURES if x_train[f].isna().all()]
    fitted, scores, configs = {}, {}, {}
    for name in ("baseline", "linear", "polynomial", "tree"):
        choices = (
            [(depth, leaf) for depth in (3, 5, 8, 12) for leaf in (5, 10, 20)]
            if name == "tree"
            else [(5, 5)]
        )
        for depth, leaf in choices:
            model = make_model(name, max_depth=depth, min_samples_leaf=leaf)
            model.fit(x_train, train["asking_price_vnd"])
            score = metrics(validation["asking_price_vnd"], model.predict(x_val))
            if name not in scores or score["rmse_vnd"] < scores[name]["rmse_vnd"]:
                fitted[name], scores[name] = model, score
                configs[name] = (
                    {"max_depth": depth, "min_samples_leaf": leaf} if (name == "tree") else {}
                )
    return {
        "models": fitted,
        "validation": scores,
        "configs": configs,
        "winner": select_winner(scores),
        "features": FEATURES,
        "schema_version": SCHEMA_VERSION,
        "uninformative_features": uninformative_features,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--dataset-card", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--registry-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--actor")
    parser.add_argument(
        "--test-pool-csv",
        type=Path,
        help="CSV with property_group_id: the holdout is drawn only from these groups",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; use a new run directory")
    registry_options = (args.registry_dir, args.run_id, args.actor)
    if any(value is not None for value in registry_options) and not all(
        value is not None and str(value).strip() for value in registry_options
    ):
        parser.error("Registry requires registry-dir, nonblank run-id and actor together")
    card = DatasetCard.model_validate_json(args.dataset_card.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    frame = load_current_csv(args.csv, now, card=card)
    if not set(frame["district_code"]).issubset(card.district_labels):
        parser.error("District labels missing from dataset card")
    if card.data_kind == "real" and args.registry_dir is None:
        parser.error("Real training requires registry")
    test_pool = None
    if args.test_pool_csv is not None:
        # Same reading and rules as ml.registry, so a pool accepted here can be reserved later.
        with args.test_pool_csv.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames or "property_group_id" not in reader.fieldnames:
                parser.error("Test pool CSV needs a property_group_id column")
            test_pool = [row["property_group_id"] or "" for row in reader]
        if any(not g.strip() or g != g.strip() for g in test_pool) or len(set(test_pool)) != len(
            test_pool
        ):
            parser.error("Test pool has invalid (blank, padded or duplicate) group IDs")
    try:
        splits = split_groups(frame, test_pool=test_pool)
    except ValueError as exc:
        parser.error(str(exc))
    if args.registry_dir is not None:
        # Record before fitting so a failed attempt still leaves its exposure history.
        exposures = {
            purpose: splits[name]["property_group_id"].astype(str).tolist()
            for purpose, name in (("fit", "train"), ("tune", "validation"))
        }
        try:
            record_groups(args.registry_dir, exposures, args.run_id, args.actor)
        except (OSError, ValueError, TypeError) as exc:
            parser.error(str(exc))
    bundle = fit_candidates(splits["train"], splits["validation"])
    bundle["dataset_card"] = card.model_dump()
    bundle["created_at"] = now.isoformat()
    bundle["dataset_sha256"] = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    bundle["test_pool_sha256"] = (
        hashlib.sha256(args.test_pool_csv.read_bytes()).hexdigest() if test_pool else None
    )
    bundle["package_versions"] = {
        name: importlib.metadata.version(name)
        for name in ("scikit-learn", "pandas", "numpy", "joblib", "pydantic")
    }
    bundle["source_sha256"] = hashlib.sha256(
        b"".join(
            path.name.encode() + path.read_bytes()
            for path in sorted(Path(__file__).parent.glob("*.py"))
        )
    ).hexdigest()
    args.output.mkdir(parents=True)
    splits["test"].to_csv(args.output / "holdout.csv", index=False)
    pd.concat(
        [
            part[["source_id", "listing_id", "property_group_id"]].assign(split=name)
            for name, part in splits.items()
        ]
    ).to_csv(args.output / "splits.csv", index=False)
    for name in ("holdout", "splits"):
        bundle[f"{name}_sha256"] = hashlib.sha256(
            (args.output / f"{name}.csv").read_bytes()
        ).hexdigest()
    joblib.dump(bundle, args.output / "candidates.joblib")
    public = {
        key: bundle[key]
        for key in ("winner", "validation", "configs", "created_at", "uninformative_features")
    }
    public["snapshot_kind"] = card.snapshot_kind
    public["test_pool_sha256"] = bundle["test_pool_sha256"]
    public["counts"] = {name: len(part) for name, part in splits.items()}
    public["release_status"] = "candidate"
    (args.output / "selection.json").write_text(
        json.dumps(public, indent=2, allow_nan=False), encoding="utf-8"
    )
    print("Candidate selected using validation; test not evaluated; release not approved.")


if __name__ == "__main__":
    main()
