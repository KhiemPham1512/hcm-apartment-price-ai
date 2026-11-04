"""TV6's explicit final holdout evaluation; never selects a winner using test."""

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd

from ml.data import feature_frame
from ml.train import metrics


def _validate_split(splits: pd.DataFrame, holdout: pd.DataFrame) -> None:
    identity = ["source_id", "listing_id", "property_group_id"]
    required = identity + ["split"]
    if not set(required).issubset(splits.columns):
        raise ValueError("Invalid frozen split: missing identity or split columns")
    if splits[required].isna().any().any() or any(
        splits[column].str.strip().eq("").any() for column in required
    ):
        raise ValueError("Invalid frozen split: empty identity or split")
    if set(splits["split"]) != {"train", "validation", "test"}:
        raise ValueError("Invalid frozen split: expected train, validation and test")
    if splits.duplicated(["source_id", "listing_id"]).any():
        raise ValueError("Invalid frozen split: repeated listing")
    if splits["property_group_id"].duplicated().any():
        raise ValueError("Invalid frozen split: repeated property group")
    expected = splits.loc[splits["split"] == "test", identity]
    if (
        not set(identity).issubset(holdout.columns)
        or len(holdout) != len(expected)
        or set(holdout[identity].itertuples(index=False, name=None))
        != set(expected.itertuples(index=False, name=None))
    ):
        raise ValueError("Holdout does not match frozen test membership")


def evaluate(bundle: dict, holdout: pd.DataFrame) -> dict:
    if set(bundle["models"]) != {"baseline", "linear", "polynomial", "tree"}:
        raise ValueError("Evaluation requires baseline, linear, polynomial and tree")
    if bundle.get("winner") not in ("linear", "polynomial", "tree"):
        raise ValueError("Validation winner must be linear, polynomial or tree")
    x_test = feature_frame(holdout)
    return {
        "evaluation_kind": "current_snapshot_grouped",
        "winner_selected_by_validation": bundle["winner"],
        "test": {
            name: metrics(holdout["asking_price_vnd"], model.predict(x_test))
            for name, model in bundle["models"].items()
        },
        "data_kind": bundle["dataset_card"]["data_kind"],
        "release_status": "candidate",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.run_dir / "evaluation.json"
    if output.exists():
        parser.error("Holdout already evaluated; preserve evidence rather than overwrite")
    # Local trusted artifacts only: never expose this loader through an upload endpoint.
    bundle = joblib.load(args.run_dir / "candidates.joblib")
    for name in ("holdout", "splits"):
        actual = hashlib.sha256((args.run_dir / f"{name}.csv").read_bytes()).hexdigest()
        if actual != bundle[f"{name}_sha256"]:
            parser.error(f"Frozen {name} data was modified")
    try:
        splits = pd.read_csv(args.run_dir / "splits.csv", dtype=str)
        test = pd.read_csv(
            args.run_dir / "holdout.csv",
            dtype={key: str for key in ("source_id", "listing_id", "property_group_id")},
        )
        _validate_split(splits, test)
        report = evaluate(bundle, test)
    except ValueError as exc:
        parser.error(str(exc))
    report["candidate_sha256"] = hashlib.sha256(
        (args.run_dir / "candidates.joblib").read_bytes()
    ).hexdigest()
    report["splits_sha256"] = hashlib.sha256((args.run_dir / "splits.csv").read_bytes()).hexdigest()
    for name in ("source_sha256", "dataset_sha256", "package_versions"):
        report[name] = bundle[name]
    output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print("Test report written; this does not approve a model for public serving.")


if __name__ == "__main__":
    main()
