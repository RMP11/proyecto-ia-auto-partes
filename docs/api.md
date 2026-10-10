# API local

## Direcciones y Endpoints

| Método | Ruta | Función y descripción |
| --- | --- | --- |
| GET | / | Carga e interfaz de la aplicación web de gestión de inventario. |
| GET | /api/health | Estado del servidor y disponibilidad del modelo XGBoost cargado. |
| GET | /api/catalog | Catálogo de sucursales, repuestos y rango de fechas admitido. |
| GET | /api/metrics | Métricas de rendimiento (mae, rmse, wape, bias, mase) del experimento. |
| POST | /api/forecast | Estimación de demanda y cálculo del plan de reposición de stock. |
| GET | /docs | Documentación interactiva Swagger servida por FastAPI. |

El frontend y el backend se sirven desde el mismo puerto local. No se requiere servidor Node.js ni configurar reglas de CORS.

---

## Entrada de ejemplo (JSON)

{
  "branch_id": "SUC_01_CENTRO",
  "product_id": "REP_AMORTIGUADOR_DEL",
  "forecast_date": "2025-07-01",
  "stock_on_hand": 15,
  "incoming_units": 0,
  "safety_units": 5
}

- branch_id y product_id: Coincidentes con el catálogo activo de autopartes.
- forecast_date: Formato AAAA-MM-DD dentro del calendario permitido.
- Cantidades de inventario: Números enteros no negativos (0 o mayores).
- El servidor calcula automáticamente los rezagos (lags) y promedios móviles a partir de sales.csv.

## Prueba interactiva de la API

Desde la terminal de comandos (cURL):

curl -X POST <http://127.0.0.1:8981/api/forecast> -H 'Content-Type: application/json' -d '{"branch_id":"SUC_01_CENTRO","product_id":"REP_AMORTIGUADOR_DEL","forecast_date":"2025-07-01","stock_on_hand":15,"incoming_units":0,"safety_units":5}'

---

## Estructura de la respuesta (Response)

- forecast_units: Pronóstico de ventas proyectado por XGBoost.
- baseline_units: Ventas reales registradas hace 7 días (t-7).
- plan.target_stock: Meta de inventario (techo de pronóstico + reserva).
- plan.available_stock: Stock disponible (existencias + entradas confirmadas).
- plan.suggested_order: Propuesta de compra o transferencia de repuestos.
- history: Ventas registradas en los últimos 14 días.
- features: Variables de entrada que recibió el modelo XGBoost.
- branch_id, product_id, forecast_date: Metadatos de la consulta.

---

## Manejo de errores HTTP

- 422: Datos incorrectos, repuesto no registrado, fechas fuera de rango o números negativos.
- 503: No se encuentra cargado el archivo del modelo (.joblib) o el historial sales.csv.
- Error de inicio: El archivo sales.csv cambió desde el entrenamiento. Se debe reentrenar.