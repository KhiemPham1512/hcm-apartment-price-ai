"""Permutation importance and ablation on VALIDATION only; test rows and labels are never used."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from ml.data import feature_frame, load_current_csv
from ml.models import make_model
from ml.schema import FEATURES, DatasetCard
from ml.train import metrics

MODELS = ("linear", "polynomial", "tree")
REPEATS, SEED = 10, 42
ABLATIONS = {
    "area_m2": ["area_m2"],
    "district_code": ["district_code"],
    "area_m2+district_code": ["area_m2", "district_code"],
}
LIMITS = [
    "Permutation importance is not causal and says nothing about law or fairness.",
    "Correlated features share importance; read it together with the ablation.",
    "Ablation neutralises a column in train and validation and refits with the candidate's "
    "fixed hyperparameters; it is not re-tuned.",
    "Everything is measured on validation; the frozen test set is untouched.",
]


def _neutralise(x: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    x = x.copy()
    for column in columns:
        x[column] = "ablated" if column == "district_code" else np.nan
    return x


def analyse(bundle: dict, train: pd.DataFrame, validation: pd.DataFrame) -> dict:
    """Only train and validation rows can be passed in, so test labels are out of reach."""
    x_train, y_train = feature_frame(train), train["asking_price_vnd"].to_numpy(dtype=float)
    x_val, y_val = feature_frame(validation), validation["asking_price_vnd"].to_numpy(dtype=float)
    models = {}
    for name in MODELS:
        model = bundle["models"][name]
        full = metrics(y_val, model.predict(x_val))["rmse_vnd"]
        shuffled = permutation_importance(
            model,
            x_val,
            y_val,
            scoring="neg_root_mean_squared_error",
            n_repeats=REPEATS,
            random_state=SEED,
        )
        ranking = sorted(
            (
                {"feature": f, "importance_mean_vnd": float(m), "importance_std_vnd": float(s)}
                for f, m, s in zip(FEATURES, shuffled.importances_mean, shuffled.importances_std)
            ),
            key=lambda row: -row["importance_mean_vnd"],
        )
        for rank, row in enumerate(ranking, 1):
            row["rank"] = rank
        ablation = []
        for label, columns in ABLATIONS.items():
            refit = make_model(name, **bundle["configs"][name])
            refit.fit(_neutralise(x_train, columns), y_train)
            rmse = metrics(y_val, refit.predict(_neutralise(x_val, columns)))["rmse_vnd"]
            ablation.append(
                {"removed": label, "validation_rmse_vnd": rmse, "delta_vs_full_vnd": rmse - full}
            )
        models[name] = {"validation_rmse_vnd": full, "permutation": ranking, "ablation": ablation}
    return {"models": models, "n_train": len(train), "n_validation": len(validation)}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--dataset-card", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="default: <run-dir>/importance.json")
    args = parser.parse_args()
    output = args.output or args.run_dir / "importance.json"
    if output.exists():
        parser.error(f"{output} already exists; keep the evidence, use --output for a new file")
    try:
        # Local trusted artifact, as in ml.evaluate.
        bundle = joblib.load(args.run_dir / "candidates.joblib")
        if _sha256(args.csv) != bundle["dataset_sha256"]:
            parser.error("CSV does not match the candidate's dataset")
        if _sha256(args.run_dir / "splits.csv") != bundle["splits_sha256"]:
            parser.error("splits.csv does not match the candidate")
        card = DatasetCard.model_validate_json(args.dataset_card.read_text(encoding="utf-8"))
        if card.model_dump() != bundle["dataset_card"]:
            parser.error("Dataset card does not match the candidate")
        frame = load_current_csv(args.csv, datetime.now(timezone.utc), card=card)
        splits = pd.read_csv(args.run_dir / "splits.csv", dtype=str)
        wanted = splits.loc[splits["split"].isin(["train", "validation"])]
        # Keep train/validation rows at once; test rows are dropped here and never touched.
        frame = frame.merge(
            wanted[["source_id", "listing_id", "split"]], on=["source_id", "listing_id"]
        )
        if len(frame) != len(wanted):
            parser.error("CSV rows do not match the frozen splits")
        report = analyse(
            bundle, frame[frame["split"] == "train"], frame[frame["split"] == "validation"]
        )
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    report.update(
        {
            "analysis": "validation_permutation_importance_and_ablation",
            "scoring": "rmse_vnd",
            "repeats": REPEATS,
            "seed": SEED,
            "snapshot_kind": bundle["dataset_card"].get("snapshot_kind", "current"),
            "data_kind": bundle["dataset_card"]["data_kind"],
            "winner_selected_by_validation": bundle["winner"],
            "uninformative_features": bundle.get("uninformative_features", []),
            "candidate_sha256": _sha256(args.run_dir / "candidates.joblib"),
            "dataset_sha256": bundle["dataset_sha256"],
            "splits_sha256": bundle["splits_sha256"],
            "limits": LIMITS,
        }
    )
    with output.open("x", encoding="utf-8") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
    print("Importance report written (validation only); it does not open the test set.")


if __name__ == "__main__":
    main()
