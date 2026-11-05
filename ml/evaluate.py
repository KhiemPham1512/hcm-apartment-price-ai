"""TV6's explicit final holdout evaluation; never selects a winner using test."""

import argparse
import hashlib
import json
from contextlib import nullcontext
from pathlib import Path

import joblib
import pandas as pd

from ml.data import feature_frame
from ml.freeze import verify_freeze
from ml.registry import evaluation_claim
from ml.schema import FEATURES, SCHEMA_VERSION
from ml.train import metrics


def _validate_split(splits: pd.DataFrame) -> pd.DataFrame:
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
    return splits.loc[splits["split"] == "test", identity]


def _validate_holdout(expected: pd.DataFrame, holdout: pd.DataFrame) -> None:
    identity = ["source_id", "listing_id", "property_group_id"]
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
    parser.add_argument("--registry-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--actor")
    args = parser.parse_args()
    registry_options = (args.registry_dir, args.run_id, args.actor)
    if any(value is not None for value in registry_options) and not all(
        value is not None and str(value).strip() for value in registry_options
    ):
        parser.error("Registry requires registry-dir, nonblank run-id and actor together")
    output = args.run_dir / "evaluation.json"
    if output.exists():
        parser.error("Holdout already evaluated; preserve evidence rather than overwrite")
    try:
        frozen = verify_freeze(args.run_dir)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(f"Freeze verification failed: {exc}")
    # Local trusted artifacts only: never expose this loader through an upload endpoint.
    bundle = joblib.load(args.run_dir / "candidates.joblib")
    if bundle.get("schema_version") != SCHEMA_VERSION or bundle.get("features") != FEATURES:
        parser.error("Candidate feature contract mismatch")
    if bundle["dataset_card"].get("data_kind") not in ("real", "synthetic"):
        parser.error("Invalid candidate data kind")
    if bundle["dataset_card"]["data_kind"] == "real" and args.registry_dir is None:
        parser.error("Real evaluation requires registry")
    for name in ("holdout", "splits"):
        actual = hashlib.sha256((args.run_dir / f"{name}.csv").read_bytes()).hexdigest()
        if actual != bundle[f"{name}_sha256"]:
            parser.error(f"Frozen {name} data was modified")
    try:
        splits = pd.read_csv(args.run_dir / "splits.csv", dtype=str)
        expected = _validate_split(splits)
        claim = (
            evaluation_claim(
                args.registry_dir, expected["property_group_id"].tolist(), args.run_id, args.actor
            )
            if args.registry_dir is not None
            else nullcontext({"registry_status": "not_checked_synthetic"})
        )
        with claim as evidence:
            test = pd.read_csv(
                args.run_dir / "holdout.csv",
                dtype={key: str for key in ("source_id", "listing_id", "property_group_id")},
            )
            _validate_holdout(expected, test)
            report = evaluate(bundle, test)
            report.update(evidence)
            report["candidate_sha256"] = hashlib.sha256(
                (args.run_dir / "candidates.joblib").read_bytes()
            ).hexdigest()
            report["splits_sha256"] = hashlib.sha256(
                (args.run_dir / "splits.csv").read_bytes()
            ).hexdigest()
            for name in ("source_sha256", "dataset_sha256", "package_versions"):
                report[name] = bundle[name]
            report["freeze_sha256"] = frozen["sha256"]
            report["freeze_reviewer"] = frozen["reviewer"]
            report["frozen_at"] = frozen["frozen_at"]
            with output.open("x", encoding="utf-8") as destination:
                json.dump(report, destination, indent=2, allow_nan=False)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    print("Test report written; this does not approve a model for public serving.")


if __name__ == "__main__":
    main()
