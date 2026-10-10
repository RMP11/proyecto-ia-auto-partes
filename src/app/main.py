"""Serve a local forecasting API and its static interface."""

import hashlib
import json
from contextlib import asynccontextmanager

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.app.data import forecast_context, validate_sales
from src.app.inventory import replenishment_plan
from src.app.schemas import ForecastInput
from src.app.settings import (
    ARTIFACT_DIR,
    DATA_DIR,
    FEATURES,
    FRONTEND_DIR,
    PRODUCTS,
    BRANCHES,
    VALIDATION_END,
)
from src.app.train import predict_units


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.bundle = None
    app.state.report = None
    app.state.sales = None

    model_path = ARTIFACT_DIR / "model.joblib"
    metrics_path = ARTIFACT_DIR / "metrics.json"
    sales_path = DATA_DIR / "sales.csv"

    paths = [model_path, metrics_path, sales_path]

    if all(path.exists() for path in paths):
        # 1. Cargar artefactos entrenados
        bundle = joblib.load(model_path)
        report = json.loads(metrics_path.read_text(encoding="utf-8"))

        # 2. Validar consistencia de características (FEATURES) y versión
        if (
            bundle["model_version"] != report["model_version"]
            or bundle["features"] != FEATURES
        ):
            raise RuntimeError(
                "Desalineación entre el modelo, reporte o la lista FEATURES. "
                "Vuelve a entrenar el modelo con `python -m app.train`."
            )

        # 3. Validar integridad de los datos históricos de ventas via SHA256
        saved_sha256 = bundle.get("sales_sha256")
        if (
            saved_sha256
            and hashlib.sha256(sales_path.read_bytes()).hexdigest() != saved_sha256
        ):
            raise RuntimeError(
                "El archivo sales.csv ha sido modificado desde el último entrenamiento. Vuelve a entrenar con `python -m app.train`."
            )

        # 4. Cargar dataset con tipos de datos explícitos (incluyendo branch_id)
        sales = pd.read_csv(
            sales_path,
            parse_dates=["date"],
            dtype={
                "branch_id": "string",
                "product_id": "string",
                "category": "string",
                # "planned_promotion": "int8",
            },
        )

        # 5. Validar esquema e integridad del dataset multisucursal
        validate_sales(sales)

        app.state.bundle = bundle
        app.state.report = report
        app.state.sales = sales

    yield


app = FastAPI(title="Inventory Forecast Demo", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, error: RequestValidationError):
    details = [
        {"loc": item["loc"], "msg": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


def require_model():
    if app.state.bundle is None:
        raise HTTPException(
            503, "Model unavailable. Generate data, train and restart the server."
        )
    return app.state.bundle


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok" if app.state.bundle else "model_missing",
        "synthetic_data": True,
    }


@app.get("/api/catalog")
def catalog():
    require_model()
    sales = app.state.sales

    next_date = str((sales["date"].max() + pd.Timedelta(days=1)).date())

    return {
        "products": [
            {
                "product_id": key,
                "name": value.get("name"),
            }
            for key, value in PRODUCTS.items()
        ],
        "branches": [
            {
                "branch_id": branch_id,
                "name": branch_id.replace("SUC_", "").replace("_", " ").title(),
            }
            for branch_id in BRANCHES
        ],
        "first_forecast_date": VALIDATION_END,
        "last_forecast_date": next_date,
        "default_forecast_date": next_date,
        "historical_rows": len(sales),
        "synthetic_data": True,
    }


@app.get("/api/metrics")
def metrics():
    require_model()
    return app.state.report


@app.post("/api/forecast")
def forecast(inputs: ForecastInput):
    bundle = require_model()
    date = pd.Timestamp(inputs.forecast_date)

    max_supported_date = app.state.sales.date.max() + pd.Timedelta(days=1)
    if not (pd.Timestamp(VALIDATION_END) <= date <= max_supported_date):
        raise HTTPException(
            status_code=422,
            detail=f"Seleccione una fecha dentro del periodo de simulación ({VALIDATION_END} a {max_supported_date.date()}).",
        )

    # 2. Extraer el contexto histórico (14 días previos) filtrado por Sucursal y Producto
    try:
        features, history = forecast_context(
            sales=app.state.sales,
            branch_id=inputs.branch_id,
            product_id=inputs.product_id,
            forecast_date=inputs.forecast_date,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    # 3. Construir el DataFrame para inferencia con el orden exacto de FEATURES
    frame = pd.DataFrame([features], columns=FEATURES)

    # 4. Inferencia del modelo (asegurando valores no negativos)
    forecast_units = float(predict_units(bundle["model"], frame)[0])

    # 5. Plan de reposición según stock actual, transito y stock de seguridad
    plan = replenishment_plan(
        forecast_units=forecast_units,
        stock_on_hand=inputs.stock_on_hand,
        incoming_units=inputs.incoming_units,
        safety_units=inputs.safety_units,
    )

    return {
        "branch_id": inputs.branch_id,
        "product_id": inputs.product_id,
        "product_name": PRODUCTS[inputs.product_id]["name"],
        "category": PRODUCTS[inputs.product_id]["category"],
        "forecast_date": str(inputs.forecast_date),
        "forecast_units": round(forecast_units, 2),
        "baseline_units": features["sales_lag_7"],
        "plan": plan,
        "history": history,
        "features": features,
        "model_version": bundle["model_version"],
        "synthetic_data": True,
    }
