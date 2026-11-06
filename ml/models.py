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
from sklearn.imputer import SimpleImputer
from sklearn.tree import DecisionTreeRegressor

from ml.schema import NUMERIC_FEATURES, CATEGORICAL_FEATURES


def build_shared_preprocessor() -> ColumnTransformer:
    """Tạo ColumnTransformer dùng chung cho số và phân loại để chống rò rỉ."""
    num_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    
    cat_pipeline = Pipeline([
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    
    return ColumnTransformer(
        transformers=[
            ("num", num_pipeline, NUMERIC_FEATURES),
            ("cat", cat_pipeline, CATEGORICAL_FEATURES),
        ]
    )


def get_baseline_model() -> BaseEstimator:
    """Mô hình B0: Baseline (Median)."""
    return DummyRegressor(strategy="median")


def get_linear_model() -> BaseEstimator:
    """Mô hình M1: Linear/Ridge Regression kết hợp preprocessor."""
    return Pipeline([
        ("preprocessor", build_shared_preprocessor()),
        ("regressor", Ridge(alpha=1.0))
    ])


def get_polynomial_model(degree: int = 2) -> BaseEstimator:
    """Mô hình M2: Polynomial Regression (Bậc 2 trên đặc trưng số)."""
    num_poly_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("poly", PolynomialFeatures(degree=degree, include_bias=False)),
        ("scaler", StandardScaler()),
    ])
    
    cat_pipeline = Pipeline([
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num_poly", num_poly_pipeline, NUMERIC_FEATURES),
            ("cat", cat_pipeline, CATEGORICAL_FEATURES),
        ]
    )
    
    return Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", Ridge(alpha=1.0))
    ])


def get_tree_model() -> BaseEstimator:
    """Mô hình M3: Decision Tree Regressor kết hợp preprocessor."""
    return Pipeline([
        ("preprocessor", build_shared_preprocessor()),
        ("regressor", DecisionTreeRegressor(random_state=42))
    ])


def make_model(name: str) -> BaseEstimator:
    """Factory function chuẩn cho các test suite và conftest."""
    if name == "baseline":
        return get_baseline_model()
    elif name == "linear":
        return get_linear_model()
    elif name == "polynomial":
        return get_polynomial_model(degree=2)
    elif name == "tree":
        return get_tree_model()
    else:
        raise ValueError(f"Unknown model name: {name}")
