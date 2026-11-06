"""
ml/train.py
Tác giả: TV2 – ML Linear/Polynomial
Mục đích: Orchestration training, validation, đánh giá mô hình và xuất artifact.
"""

import os
from typing import Any, Dict

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate

from ml.models import build_baseline_model, build_linear_model, build_polynomial_model


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Tính toán các chỉ số đo lường hiệu năng."""
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    return {"rmse": rmse, "mae": mae, "r2": r2}


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Hàm wrapper tương thích với ml/evaluate.py"""
    return evaluate_predictions(y_true, y_pred)


def train_and_evaluate(
    df: pd.DataFrame,
    target_col: str,
    num_features: list,
    cat_features: list,
    output_dir: str = "artifacts"
) -> Dict[str, Any]:
    """Orchestration huấn luyện và lựa chọn mô hình phù hợp nhất."""
    os.makedirs(output_dir, exist_ok=True)
    X = df[num_features + cat_features]
    y = df[target_col]

    models = {
        "Baseline": build_baseline_model(),
        "Linear_Ridge": build_linear_model(num_features, cat_features, model_type="ridge"),
        "Polynomial_Deg2": build_polynomial_model(num_features, cat_features, degree=2)
    }

    results = {}
    best_score = float('inf')
    best_pipeline = None
    best_model_name = None

    kf = KFold(n_splits=5, shuffle=True, random_state=42)

    for name, model in models.items():
        if name == "Baseline":
            model.fit(X, y)
            preds = model.predict(X)
            metrics_vals = evaluate_predictions(y, preds)
        else:
            cv_results = cross_validate(
                model, X, y, cv=kf,
                scoring=['neg_root_mean_squared_error', 'neg_mean_absolute_error', 'r2']
            )
            metrics_vals = {
                "rmse": float(-cv_results['test_neg_root_mean_squared_error'].mean()),
                "mae": float(-cv_results['test_neg_mean_absolute_error'].mean()),
                "r2": float(cv_results['test_r2'].mean())
            }
            model.fit(X, y)

        results[name] = metrics_vals
        if metrics_vals["rmse"] < best_score:
            best_score = metrics_vals["rmse"]
            best_model_name = name
            best_pipeline = model

    return {
        "results": results,
        "best_model_name": best_model_name,
        "best_pipeline": best_pipeline
    }
def fit_candidates(X, y):
    """Hàm wrapper tương thích với test của nhóm"""
    return train_and_evaluate(
        df=pd.concat([X, y], axis=1),
        target_col=y.name if hasattr(y, 'name') else 'target',
        num_features=list(X.select_dtypes(include=[np.number]).columns),
        cat_features=list(X.select_dtypes(exclude=[np.number]).columns)
    )
