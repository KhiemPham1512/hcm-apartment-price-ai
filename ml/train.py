"""
ml/train.py
Tác giả: TV2 – Orchestration & Training
"""

import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
import joblib

from ml.models import (
    get_baseline_model,
    get_linear_model,
    get_polynomial_model,
    get_tree_model,
)
from ml.schema import SCHEMA_VERSION, FEATURES


def metrics(y_true, y_pred) -> dict:
    """Hàm tính toán metrics chuẩn được gọi trực tiếp bởi ml.evaluate[cite: 28]."""
    y_t = np.asarray(y_true)
    y_p = np.asarray(y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_t, y_p)))
    mae = float(mean_absolute_error(y_t, y_p))
    r2 = float(r2_score(y_t, y_p))
    return {"rmse": rmse, "mae": mae, "r2": r2}


def fit_candidates(train_df: pd.DataFrame, val_df: pd.DataFrame) -> dict:
    """Huấn luyện các ứng viên mô hình và trả về bundle đúng hợp đồng với evaluate.py[cite: 28]."""
    X_train = train_df[FEATURES]
    y_train = train_df["asking_price_vnd"]
    X_val = val_df[FEATURES]
    y_val = val_df["asking_price_vnd"]

    models = {
        "baseline": get_baseline_model(),
        "linear": get_linear_model(),
        "polynomial": get_polynomial_model(degree=2),
        "tree": get_tree_model(),
    }

    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_val)
        results[name] = metrics(y_val, preds)

    # Chọn winner dựa trên validation RMSE thấp nhất (chỉ trong linear, polynomial, tree)[cite: 28]
    winner = min(
        ("linear", "polynomial", "tree"),
        key=lambda n: results[n]["rmse"]
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "features": FEATURES,
        "models": models,
        "results": results,
        "winner": winner,
    }


def run_training(csv_path: str, card_path: str, output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    card = json.loads(Path(card_path).read_text(encoding="utf-8"))

    groups = df["property_group_id"]
    gss = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=42)
    train_idx, val_idx = next(gss.split(df, groups=groups))
    
    train_df = df.iloc[train_idx]
    val_df = df.iloc[val_idx]

    splits_df = pd.DataFrame({
        "source_id": df["source_id"],
        "listing_id": df["listing_id"],
        "property_group_id": df["property_group_id"],
        "split": ["train" if i in train_idx else "validation" if i in val_idx else "test" for i in range(len(df))]
    })
    splits_csv_path = output_path / "splits.csv"
    splits_df.to_csv(splits_csv_path, index=False)

    holdout_csv_path = output_path / "holdout.csv"
    train_df.to_csv(holdout_csv_path, index=False)

    bundle = fit_candidates(train_df, val_df)
    bundle["dataset_card"] = card
    bundle["holdout_sha256"] = hashlib.sha256(holdout_csv_path.read_bytes()).hexdigest()
    bundle["splits_sha256"] = hashlib.sha256(splits_csv_path.read_bytes()).hexdigest()
    bundle["source_sha256"] = "synthetic-source"
    bundle["dataset_sha256"] = "synthetic-dataset"
    bundle["package_versions"] = {}

    joblib.dump(bundle, output_path / "candidates.joblib")
    print(f"Huấn luyện thành công! Winner: {bundle['winner']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--dataset-card", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run_training(args.csv, args.dataset_card, args.output)
