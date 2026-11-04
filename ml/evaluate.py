"""TV6's explicit final holdout evaluation; never selects a winner using test."""

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd

from ml.data import feature_frame
from ml.train import metrics


def evaluate(bundle: dict, holdout: pd.DataFrame) -> dict:
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
    test = pd.read_csv(args.run_dir / "holdout.csv")
    report = evaluate(bundle, test)
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
