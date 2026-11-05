"""
tests/test_ml_tv2.py
Unit tests cho các module của TV2.
"""

import pytest
import pandas as pd
import numpy as np
from ml.models import create_shared_preprocessor, build_linear_model
from ml.train import evaluate_predictions

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        'area': [50.0, 75.0, 100.0, 120.0, 60.0],
        'bedrooms': [1, 2, 3, 3, 2],
        'district': ['Q1', 'Q3', 'Q1', 'Q7', 'Q3'],
        'price': [2.5, 4.0, 6.0, 7.5, 3.2]
    })

def test_shared_preprocessor(sample_data):
    num_cols = ['area', 'bedrooms']
    cat_cols = ['district']
    preprocessor = create_shared_preprocessor(num_cols, cat_cols)
    transformed = preprocessor.fit_transform(sample_data)
    assert transformed.shape[0] == 5

def test_linear_model_fit_predict(sample_data):
    num_cols = ['area', 'bedrooms']
    cat_cols = ['district']
    X = sample_data[num_cols + cat_cols]
    y = sample_data['price']

    model = build_linear_model(num_cols, cat_cols, model_type="ridge")
    model.fit(X, y)
    preds = model.predict(X)
    assert len(preds) == len(y)

def test_evaluate_predictions():
    y_true = np.array([100, 200, 300])
    y_pred = np.array([110, 190, 310])
    metrics = evaluate_predictions(y_true, y_pred)
    assert metrics["mae"] == 10.0