"""
ml/models.py
Tác giả: TV2 – ML Linear/Polynomial & Tree Models
"""

from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler
from sklearn.tree import DecisionTreeRegressor

from ml.schema import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def create_shared_preprocessor(num_cols=None, cat_cols=None) -> ColumnTransformer:
    """Tạo ColumnTransformer dùng chung cho số và phân loại."""
    n_cols = num_cols if num_cols is not None else NUMERIC_FEATURES
    c_cols = cat_cols if cat_cols is not None else CATEGORICAL_FEATURES

    num_pipeline = Pipeline([
        ("scaler", StandardScaler()),
    ])

    cat_pipeline = Pipeline([
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    return ColumnTransformer(
        transformers=[
            ("num", num_pipeline, n_cols),
            ("cat", cat_pipeline, c_cols),
        ]
    )


def build_baseline_model() -> BaseEstimator:
    """Mô hình B0: Baseline (Median)."""
    return DummyRegressor(strategy="median")


def build_linear_model(num_cols=None, cat_cols=None, model_type: str = "ridge") -> BaseEstimator:
    """Mô hình M1: Linear/Ridge Regression kết hợp preprocessor."""
    preprocessor = create_shared_preprocessor(num_cols, cat_cols)
    return Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", Ridge(alpha=1.0))
    ])


def build_polynomial_model(num_cols=None, cat_cols=None, degree: int = 2) -> BaseEstimator:
    """Mô hình M2: Polynomial Regression (Bậc 2 trên đặc trưng số)."""
    n_cols = num_cols if num_cols is not None else NUMERIC_FEATURES
    c_cols = cat_cols if cat_cols is not None else CATEGORICAL_FEATURES

    num_poly_pipeline = Pipeline([
        ("poly", PolynomialFeatures(degree=degree, include_bias=False)),
        ("scaler", StandardScaler()),
    ])

    cat_pipeline = Pipeline([
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num_poly", num_poly_pipeline, n_cols),
            ("cat", cat_pipeline, c_cols),
        ]
    )

    return Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", Ridge(alpha=1.0))
    ])


def make_model(name: str) -> BaseEstimator:
    """Factory function chuẩn cho các test suite và conftest."""
    if name == "baseline":
        return build_baseline_model()
    elif name == "linear":
        return build_linear_model()
    elif name == "polynomial":
        return build_polynomial_model(degree=2)
    elif name == "tree":
        return Pipeline([
            ("preprocessor", create_shared_preprocessor()),
            ("regressor", DecisionTreeRegressor(random_state=42))
        ])
    else:
        raise ValueError(f"Unknown model name: {name}")
