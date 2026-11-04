"""The baseline and three models required by the assignment."""

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler
from sklearn.tree import DecisionTreeRegressor

from ml.schema import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def make_model(kind: str, *, max_depth: int = 5, min_samples_leaf: int = 5) -> Pipeline:
    numeric = [("impute", SimpleImputer(strategy="median"))]
    if kind == "polynomial":
        numeric.append(("polynomial", PolynomialFeatures(degree=2, include_bias=False)))
    if kind in ("linear", "polynomial"):
        numeric.append(("scale", StandardScaler()))
    preprocess = ColumnTransformer(
        [
            ("numeric", Pipeline(numeric), NUMERIC_FEATURES),
            (
                "district",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )
    estimators = {
        "baseline": DummyRegressor(strategy="median"),
        "linear": LinearRegression(),
        "polynomial": LinearRegression(),
        "tree": DecisionTreeRegressor(
            max_depth=max_depth, min_samples_leaf=min_samples_leaf, random_state=42
        ),
    }
    if kind not in estimators:
        raise ValueError(f"Unknown model: {kind}")
    return Pipeline([("preprocess", preprocess), ("model", estimators[kind])])
