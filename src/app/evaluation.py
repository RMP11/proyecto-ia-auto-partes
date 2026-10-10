"""Chronological splits and regression metrics in business-readable units."""

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.app.settings import TRAIN_END, VALIDATION_END


def split_by_date(data):
    train = data[data.date < TRAIN_END].copy()
    validation = data[(data.date >= TRAIN_END) & (data.date < VALIDATION_END)].copy()
    test = data[data.date >= VALIDATION_END].copy()
    
    # 1. Validar que ninguna partición esté vacía
    if any(part.empty for part in [train, validation, test]):
        raise ValueError("Training, validation and test periods must all contain observations.")
        
    # 2. Validar continuidad y no solapamiento de fechas
    if not train.date.max() < validation.date.min() or not validation.date.max() < test.date.min():
        raise ValueError("The temporal partitions overlap.")
        
    # 3. Advertencia flexible para variaciones en el catálogo de productos
    train_prods, val_prods, test_prods = set(train.product_id), set(validation.product_id), set(test.product_id)
    if not (train_prods == val_prods == test_prods):
        print("⚠️ ADVERTENCIA: El catálogo de productos varía entre las particiones de entrenamiento, validación y prueba.")
        
    return train, validation, test


def regression_metrics(actual, predicted, baseline=None):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    total_units = float(actual.sum())
    
    mae = float(mean_absolute_error(actual, predicted))
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    bias = float(np.mean(predicted - actual))
    wape = float(np.abs(actual - predicted).sum() / total_units) if total_units > 0 else None
    
    mase = None
    if baseline is not None:
        baseline = np.asarray(baseline, dtype=float)
        mae_baseline = float(mean_absolute_error(actual, baseline))
        mase = float(mae / mae_baseline) if mae_baseline > 0 else 1.0

    return {
        "mae": mae,
        "rmse": rmse,
        "wape": wape,
        "bias": bias,
        "mase": mase
    }


def improvement_percent(baseline_mae, model_mae):
    return 100 * (baseline_mae - model_mae) / baseline_mae if baseline_mae > 0 else None

