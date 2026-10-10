"""Keep experiment choices, product definitions and paths in one place."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ARTIFACT_DIR = ROOT / "artifacts"
FRONTEND_DIR = ROOT / "frontend"
SEED = 42
START_DATE = "2023-01-01"
END_DATE = "2025-06-30"
TRAIN_END = "2024-10-01"
VALIDATION_END = "2025-01-01"
HISTORY_DAYS = 14
TARGET = "units_sold"
BRANCHES = ["SUC_01_CENTRO", "SUC_02_NORTE", "SUC_03_SUR", "SUC_04_ESTE", "SUC_05_OESTE"]

PRODUCTS = {
    # --- ALTA ROTACIÓN ---
    "REP_FILTRO_ACEITE": {
        "name": "Filtro de aceite",
        "category": "Filtros",
        "base_demand": 4.5,
        "price": 12.50,
        "zero_prob": 0.05
    },
    "REP_PASTILLAS_FRENO": {
        "name": "Pastillas de freno",
        "category": "Frenos",
        "base_demand": 3.0,
        "price": 35.00,
        "zero_prob": 0.10
    },

    # --- MEDIA ROTACIÓN ---
    "REP_BATERIA_12V": {
        "name": "Batería 12V",
        "category": "Sistema Eléctrico",
        "base_demand": 1.2,
        "price": 110.00,
        "zero_prob": 0.35
    },
    "REP_AMORTIGUADOR_DEL": {
        "name": "Amortiguador delantero",
        "category": "Suspensión y Dirección",
        "base_demand": 0.8,
        "price": 85.00,
        "zero_prob": 0.45
    },

    # --- BAJA ROTACIÓN / INTERMITENTE ---
    "REP_SENSOR_CKP": {
        "name": "Sensor CKP",
        "category": "Electrónica y Sensores",
        "base_demand": 0.3,
        "price": 45.00,
        "zero_prob": 0.75
    },
    "REP_CIGUENAL_MOTOR": {
        "name": "Cigüeñal de motor",
        "category": "Motor",
        "base_demand": 0.1,
        "price": 320.00,
        "zero_prob": 0.90
    },
    "REP_KIT_EMBRAGUE": {
        "name": "Kit de embrague",
        "category": "Transmisión",
        "base_demand": 0.2,
        "price": 195.00,
        "zero_prob": 0.82
    },
}

# NUMERIC_FEATURES = [
#     "day_of_week", "month", "planned_promotion", "sales_lag_1",
#     "sales_lag_7", "sales_lag_14", "sales_mean_7", "sales_mean_14",
# ]
# FEATURES = ["product_id", *NUMERIC_FEATURES]

CATEGORICAL_FEATURES = ["branch_id", "product_id", "category"]

NUMERIC_FEATURES = [
    "unit_price",          # Precio unitario
    "day_of_week", 
    "month", 
    "sales_lag_1", 
    "sales_lag_7", 
    "sales_lag_14", 
    "sales_mean_7", 
    "sales_mean_14",
]

# Unir ambas listas en FEATURES
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

