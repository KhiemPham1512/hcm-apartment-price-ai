"""
ml/train.py
Tác giả: TV2 – ML Linear/Polynomial
Mục đích: Orchestration training, validation, đánh giá mô hình và xuất artifact.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate
from sklearn.tree import DecisionTreeRegressor

from ml.models import build_baseline_model, build_linear_model, build_polynomial_model


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Tính toán các chỉ số đo lường hiệu năng."""
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    return {"rmse": rmse, "mae": mae, "r2": r2}


def train_and_evaluate(
    df: pd.DataFrame,
    target_col: str,
    num_features: list,
    cat_features: list,
    output_dir: str = "artifacts"
) -> dict:
    """Orchestration huấn luyện và lựa chọn mô hình phù hợp nhất."""
    X = df[num_features + cat_features]
    y = df[target_col]

    models = {
        "baseline": build_baseline_model(),
        "linear": build_linear_model(num_features, cat_features, model_type="ridge"),
        "polynomial": build_polynomial_model(num_features, cat_features, degree=2),
        "tree": DecisionTreeRegressor(random_state=42)
    }

    results = {}
    best_score = float('inf')
    best_pipeline = None
    best_model_name = "linear"

    kf = KFold(n_splits=5, shuffle=True, random_state=42)

    for name, model in models.items():
        if name == "baseline":
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
        "schema_version": "v1",
        "features": num_features + cat_features,
        "models": models,
        "results": results,
        "winner": best_model_name,
        "best_pipeline": best_pipeline
    }


def fit_candidates(train_df: pd.DataFrame, val_df: pd.DataFrame) -> dict:
    """Hàm tương thích với test suite yêu cầu fit_candidates."""
    # Tự động nhận diện cột mục tiêu (target) và các đặc trưng (features)
    target_col = "asking_price_vnd" if "asking_price_vnd" in train_df.columns else train_df.columns[-1]
    exclude_cols = {target_col, "source_id", "listing_id", "property_group_id", "split"}
    features = [col for col in train_df.columns if col not in exclude_cols]
    
    num_features = [col for col in features if pd.api.types.is_numeric_dtype(train_df[col])]
    cat_features = [col for col in features if col not in num_features]

    return train_and_evaluate(
        df=pd.concat([train_df, val_df], axis=0),
        target_col=target_col,
        num_features=num_features,
        cat_features=cat_features
    )
def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Hàm wrapper tương thích với ml/evaluate.py"""
    return evaluate_predictions(y_true, y_pred)
