"""
ml/models.py
Tác giả: TV2 — ML Linear/Polynomial
Mục đích: Định nghĩa Shared Preprocessing và các Factory Model.
"""

from typing import List
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, PolynomialFeatures


def create_shared_preprocessor(
    num_features: List[str],
    cat_features: List[str]
) -> ColumnTransformer:
    """Tạo Pipeline tiền xử lý dùng chung cho nhóm."""
    num_transformer = Pipeline(steps=[
        ('scaler', StandardScaler())
    ])

    cat_transformer = Pipeline(steps=[
        ('ohe', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', num_transformer, num_features),
            ('cat', cat_transformer, cat_features)
        ],
        remainder='drop'
    )
    return preprocessor


def build_baseline_model(strategy: str = "mean") -> DummyRegressor:
    """Tạo mô hình Baseline (Dummy Regressor)."""
    return DummyRegressor(strategy=strategy)


def build_linear_model(
    num_features: List[str],
    cat_features: List[str],
    model_type: str = "ridge",
    alpha: float = 1.0
) -> Pipeline:
    """Xây dựng Pipeline mô hình Hồi quy tuyến tính."""
    preprocessor = create_shared_preprocessor(num_features, cat_features)
    
    if model_type.lower() == "ridge":
        regressor = Ridge(alpha=alpha)
    elif model_type.lower() == "lasso":
        regressor = Lasso(alpha=alpha)
    else:
        regressor = LinearRegression()

    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', regressor)
    ])
    return model_pipeline


def build_polynomial_model(
    num_features: List[str],
    cat_features: List[str],
    degree: int = 2,
    alpha: float = 1.0
) -> Pipeline:
    """Xây dựng Pipeline mô hình Hồi quy đa thức."""
    preprocessor = create_shared_preprocessor(num_features, cat_features)

    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('poly', PolynomialFeatures(degree=degree, include_bias=False)),
        ('regressor', Ridge(alpha=alpha))
    ])
    return model_pipeline
def make_model(
    num_features: List[str], cat_features: List[str], model_type: str = "ridge", **kwargs
):
    if model_type.lower() == "poly" or "degree" in kwargs:
        degree = kwargs.get("degree", 2)
        alpha = kwargs.get("alpha", 1.0)
        return build_polynomial_model(num_features, cat_features, degree=degree, alpha=alpha)
    else:
        alpha = kwargs.get("alpha", 1.0)
        return build_linear_model(num_features, cat_features, model_type=model_type, alpha=alpha)
