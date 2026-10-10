"""Fit two small tree models, choose on validation, then evaluate on later days."""

import hashlib
import json
import platform
from importlib.metadata import version

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

from src.app.data import build_dataset, validate_sales
from src.app.evaluation import improvement_percent, regression_metrics, split_by_date
from src.app.settings import (
    ARTIFACT_DIR,
    DATA_DIR,
    FEATURES,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    SEED,
    TARGET,
    PRODUCTS,
)

preprocessing = ColumnTransformer(
    [
        (
            "categorical",
            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            CATEGORICAL_FEATURES,
        ),
        ("numeric", "passthrough", NUMERIC_FEATURES),
    ]
)


def calculate_mase(y_true, y_pred, y_baseline):
    """
    Calculates MASE using the reference (lag-7) as the scaling factor.
    """
    mae_model = np.mean(np.abs(y_true - y_pred))
    mae_baseline = np.mean(np.abs(y_true - y_baseline))
    if mae_baseline == 0:
        return 1.0
    return float(mae_model / mae_baseline)


def regression_metrics(y_true, y_pred, y_baseline=None):
    """
    Calculates technical error metrics.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    bias = float(np.mean(y_pred - y_true))

    sum_true = np.sum(y_true)
    wape = float(np.sum(np.abs(y_true - y_pred)) / sum_true) if sum_true > 0 else None

    mase = None
    if y_baseline is not None:
        mase = calculate_mase(y_true, y_pred, y_baseline)

    return {"mae": mae, "rmse": rmse, "bias": bias, "wape": wape, "mase": mase}


def build_model(max_depth_val):
    return Pipeline(
        [
            ("preprocessing", preprocessing),
            (
                "regressor",
                XGBRegressor(
                    max_depth=6,
                    max_leaf_nodes=max_depth_val,
                    n_estimators=160,
                    learning_rate=0.06,
                    reg_lambda=2,
                    random_state=SEED,
                    n_jobs=-1,
                    verbosity=0,
                ),
            ),
        ]
    )


def predict_units(model, data):
    return np.maximum(0, model.predict(data[FEATURES]))


def describe_split(part):
    return {
        "rows": len(part),
        "days": int(part.date.nunique()),
        "first_date": str(part.date.min().date()),
        "last_date": str(part.date.max().date()),
    }


def write_report(report):
    baseline = report["test"]["baseline"]
    model = report["test"]["model"]

    improvement = report["test"]["mae_improvement_percent"]

    lines = [
        "# Resultados del Experimento de Demanda de Autopartes",
        "",
        "Pronóstico diario de ventas por producto y sucursal.",
        "",
        "## Particiones de Datos",
        "",
        "| Partición | Fechas | Filas |",
        "|---|---|---:|",
    ]

    for name, part in report["splits"].items():
        lines.append(
            f"| {name} | {part['first_date']} a "
            f"{part['last_date']} | {part['rows']} |"
        )

    lines += [
        "",
        "## Selección en Validación",
        "",
        "| Candidato | MAE (unidades) |",
        "|---|---:|",
    ]

    for candidate in report["validation"]["candidates"]:
        lines.append(
            f"| Hasta {candidate['max_leaf_nodes']} hojas | "
            f"{candidate['mae']:.3f} |"
        )

    lines += [
        f"| Referencia semanal (Lag-7) | "
        f"{report['validation']['baseline']['mae']:.3f} |",
        "",
        f"Elegido: **{report['selected_max_leaf_nodes']} " "hojas máximas por árbol**.",
        "",
        "## Evaluación Final en Test",
        "",
        "| Métrica | Referencia semanal | Modelo |",
        "|---|---:|---:|",
    ]

    lines.append(
        f"| MAE (unidades) | {baseline['mae']:.3f} | " f"**{model['mae']:.3f}** |"
    )

    lines.append(
        f"| RMSE (unidades) | {baseline['rmse']:.3f} | " f"**{model['rmse']:.3f}** |"
    )

    lines.append(f"| MASE | 1.000 | **{model['mase']:.3f}** |")

    lines.append(
        f"| Sesgo Medio | {baseline['bias']:.3f} | " f"**{model['bias']:.3f}** |"
    )

    if model["wape"] is not None:
        lines.append(f"| WAPE | {baseline['wape']:.1%} | " f"**{model['wape']:.1%}** |")

    if improvement is not None:
        lines += [
            "",
            f"**Mejora del MAE respecto a la referencia: " f"{improvement:.1%}.**",
        ]

    lines += [
        "",
        "### Desglose por Sucursal",
        "",
        "| Sucursal | MAE Referencia | MAE Modelo | MASE |",
        "|---|---:|---:|---:|",
    ]

    for row in report["by_branch"]:
        lines.append(
            f"| {row['branch_id']} | "
            f"{row['baseline']['mae']:.3f} | "
            f"{row['model']['mae']:.3f} | "
            f"{row['model']['mase']:.3f} |"
        )

    lines += [
        "",
        "### Desglose por Producto",
        "",
        "| Producto | MAE Referencia | MAE Modelo |",
        "|---|---:|---:|",
    ]
    for row in report["by_product"]:
        lines.append(
            f"| {row['name']} | {row['baseline']['mae']:.3f} | {row['model']['mae']:.3f} |"
        )

    ARTIFACT_DIR.mkdir(exist_ok=True)

    (ARTIFACT_DIR / "evaluation.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main():
    source = DATA_DIR / "sales.csv"
    if not source.exists():
        raise SystemExit(f"No se encontró el archivo de origen en {source}")

    sales = pd.read_csv(source, parse_dates=["date"])

    # Construcción de características y división de datos
    data = build_dataset(sales)
    train, validation, test = split_by_date(data)

    # Búsqueda de hiperparámetros en Validación
    candidates = []
    fitted_models = []
    for leaves in [7, 15, 31]:
        model = build_model(leaves)
        model.fit(train[FEATURES], train[TARGET])
        preds_val = predict_units(model, validation)
        score = regression_metrics(
            validation[TARGET], preds_val, validation.sales_lag_7
        )
        candidates.append({"max_leaf_nodes": leaves, "mae": score["mae"]})
        fitted_models.append(model)

    best_index = min(
        range(len(candidates)),
        key=lambda i: (candidates[i]["mae"], candidates[i]["max_leaf_nodes"]),
    )
    selected_model = fitted_models[best_index]

    # Evaluación Final en el Conjunto de Prueba (Test)
    predictions = predict_units(selected_model, test)
    baseline_predictions = test.sales_lag_7.to_numpy()

    test_metrics = regression_metrics(test[TARGET], predictions, baseline_predictions)
    baseline_metrics = regression_metrics(
        test[TARGET], baseline_predictions, baseline_predictions
    )

    sales_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    model_version = f"forecast-autopartes-v1-{sales_hash[:8]}"

    predicted_rows = test[
        ["date", "branch_id", "product_id", "category", TARGET]
    ].copy()
    predicted_rows["model_prediction"] = predictions
    predicted_rows["baseline_prediction"] = baseline_predictions

    by_product = []
    for product_id, rows in predicted_rows.groupby("product_id"):
        by_product.append(
            {
                "product_id": product_id,
                "name": PRODUCTS[product_id]["name"],
                "rows": len(rows),
                "model": regression_metrics(rows[TARGET], rows.model_prediction),
                "baseline": regression_metrics(rows[TARGET], rows.baseline_prediction),
            }
        )

    # Métricas agregadas por Sucursal
    by_branch = []
    for branch_id, rows in predicted_rows.groupby("branch_id"):
        by_branch.append(
            {
                "branch_id": branch_id,
                "rows": len(rows),
                "model": regression_metrics(
                    rows[TARGET], rows.model_prediction, rows.baseline_prediction
                ),
                "baseline": regression_metrics(
                    rows[TARGET], rows.baseline_prediction, rows.baseline_prediction
                ),
            }
        )

    report = {
        "seed": SEED,
        "model_version": model_version,
        "sales_sha256": sales_hash,
        "features": FEATURES,
        "selected_max_leaf_nodes": candidates[best_index]["max_leaf_nodes"],
        "versions": {
            "python": platform.python_version(),
            **{n: version(n) for n in ["scikit-learn", "lightgbm", "numpy", "pandas"]},
        },
        "splits": {
            name: describe_split(part)
            for name, part in [
                ("train", train),
                ("validation", validation),
                ("test", test),
            ]
        },
        "validation": {
            "candidates": candidates,
            "baseline": regression_metrics(
                validation[TARGET], validation.sales_lag_7, validation.sales_lag_7
            ),
        },
        "test": {
            "model": test_metrics,
            "baseline": baseline_metrics,
            "mae_improvement_percent": improvement_percent(
                baseline_metrics["mae"], test_metrics["mae"]
            ),
        },
        "by_branch": by_branch,
        "by_product": by_product,
    }

    ARTIFACT_DIR.mkdir(exist_ok=True)

    joblib.dump(
        {
            "model": selected_model,
            "features": FEATURES,
            "model_version": model_version,
            "sales_sha256": sales_hash,
        },
        ARTIFACT_DIR / "model.joblib",
    )

    (ARTIFACT_DIR / "metrics.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )

    predicted_rows.to_csv(ARTIFACT_DIR / "test_predictions.csv", index=False)
    write_report(report)

    print(f"Modelo seleccionado con {report['selected_max_leaf_nodes']} hojas.")
    print(f"MAE Test: {test_metrics['mae']:.3f} | MASE: {test_metrics['mase']:.3f}")
    print("Entrenamiento completado y artefactos guardados en /artifacts.")


if __name__ == "__main__":
    main()
