"""Mô-đun TV2: Định nghĩa Shared Preprocessing Pipeline và
Factory tạo mô hình Baseline, Linear, Polynomial và Tree.
"""

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler
from sklearn.tree import DecisionTreeRegressor

from ml.schema import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def build_shared_preprocessor() -> ColumnTransformer:
    """Tạo ColumnTransformer dùng chung cho cả Linear và Polynomial để chống rò rỉ dữ liệu."""
    num_pipeline = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    cat_pipeline = Pipeline(
        [
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", num_pipeline, NUMERIC_FEATURES),
            ("district", cat_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def make_model(
    kind: str,
    *,
    max_depth: int = 5,
    min_samples_leaf: int = 5,
    degree: int = 2,
    **kwargs,
) -> Pipeline:
    """Factory tổng hợp hỗ trợ baseline, linear, polynomial và tree theo chuẩn hợp đồng."""
    if kind == "baseline":
        return Pipeline([("model", DummyRegressor(strategy="median"))])

    if kind == "linear":
        return Pipeline(
            [
                ("preprocess", build_shared_preprocessor()),
                ("model", LinearRegression()),
            ]
        )

    if kind == "polynomial":
        num_pipeline = Pipeline(
            [
                ("impute", SimpleImputer(strategy="median")),
                ("poly", PolynomialFeatures(degree=degree, include_bias=False)),
                ("scale", StandardScaler()),
            ]
        )
        cat_pipeline = Pipeline(
            [
                ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ]
        )
        preprocessor = ColumnTransformer(
            transformers=[
                ("numeric", num_pipeline, NUMERIC_FEATURES),
                ("district", cat_pipeline, CATEGORICAL_FEATURES),
            ],
            remainder="drop",
        )
        return Pipeline(
            [
                ("preprocess", preprocessor),
                ("model", LinearRegression()),
            ]
        )

    if kind == "tree":
        preprocess = ColumnTransformer(
            transformers=[
                ("numeric", SimpleImputer(strategy="median"), NUMERIC_FEATURES),
                (
                    "district",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    CATEGORICAL_FEATURES,
                ),
            ],
            remainder="drop",
        )
        return Pipeline(
            [
                ("preprocess", preprocess),
                (
                    "model",
                    DecisionTreeRegressor(
                        max_depth=max_depth,
                        min_samples_leaf=min_samples_leaf,
                        random_state=42,
                    ),
                ),
            ]
        )

    raise ValueError(f"Unknown model: {kind}")
