# Modelo, evaluación y política de reposición

## Línea base

La referencia (baseline) predice las ventas estimadas para una combinación de sucursal y repuesto reutilizando el volumen de ventas del mismo día de la semana anterior:

```text
baseline_prediction[t] = units_sold[t - 7]
```

Es una heurística intuitiva y fácil de explicar que conserva la pauta semanal. Sin embargo, tiende a presentar desviaciones importantes ante cambios de patrones, estacionalidad o variaciones aleatorias. La evaluación comparativa de la línea base utiliza exactamente los mismos repuestos, sucursales y rangos de fechas que el modelo evaluado.

##  Modelo global de árboles (XGBoost)

Se utiliza el algoritmo XGBoost Regressor (XGBRegressor) mediante la librería xgboost e integrado en un Pipeline de Scikit-Learn. A diferencia de un modelo por producto, un único modelo global procesa la totalidad del catálogo en las 5 sucursales, aprendiendo patrones transversales de demanda intermitente, estacionalidad y relaciones no lineales entre las variables del calendario y el historial comercial.

Las variables categóricas como el repuesto (product_id), la sucursal (branch_id) y la línea de producto (category) se transforman mediante codificación técnica o OneHotEncoder dentro del subnodo preprocessing. Las variables numéricas (como el precio unit_price, rezagos sales_lag_* y promedios móviles sales_mean_*) no requieren escalado previo debido a la naturaleza invariante ante transformaciones de los árboles de decisión.

Se evalúan y comparan dos configuraciones de complejidad según la profundidad máxima de los árboles (max_depth):

- Configuración 1: max_depth = 3 (árboles de baja profundidad para evitar sobreajuste).
- Configuración 2: max_depth = 6 (árboles de mayor capacidad de interacción entre
variables).

Ambas configuraciones comparten los hiperparámetros base de ejecución: 160 estimadores (n_estimators = 160), tasa de aprendizaje de 0.06 (learning_rate = 0.06), regularización L2 de 2 (reg_lambda = 2), semilla fija para reproducibilidad (random_state = 42) y procesamiento multihilo (n_jobs = -1).

La selección final del hiperparámetro max_depth se determina evaluando el menor MAE en la partición de validación cronológica. Las predicciones del modelo se recortan a valores no negativos ($\max(0, \hat{y})$). Para el cálculo de métricas de desempeño se conservan los valores continuos con decimales (por ejemplo, un pronóstico de $3.2$ amortiguadores).

## Particiones

| Partición | Fechas objetivo | Cobertura temporal | Uso |
| --- | --- | ---: | --- |
| Entrenamiento | 15/01/2023–30/09/2024 | ~20.5 meses | Aprender codificación y modelo. |
| Validación | 01/10/2024–31/12/2024 | 3 meses | Elegir entre las dos configuraciones. |
| Prueba | 01/01/2025–30/06/2025 | 6 meses | Evaluación final con modelo fijo. |

El historial original inicia el 2023-01-01. Los primeros 14 días de registro para cada combinación de sucursal y producto actúan como ventana de calentamiento (warm-up) para calcular los rezagos de 1, 7 y 14 días y los promedios móviles, por lo que no se incluyen como filas entrenables.

### Dinámica de evaluación día a día

La predicción para una fecha determinada (por ejemplo, el 2 de enero) utiliza la información de ventas reales hasta el cierre del día anterior (1 de enero). El entrenamiento del modelo permanece fijo; únicamente se actualiza el vector de variables de entrada con la información histórica observada al cierre de la jornada.

Este enfoque evalúa pronósticos diarios sucesivos a un paso. No representa una predicción multi-step proyectada a 6 meses desde el 31 de diciembre. Los 1,000 repuestos comercializados en las 5 sucursales están presentes a lo largo de las tres particiones.

## Métricas de evaluación del modelo

La evaluación del modelo se realiza mediante la función `regression_metrics()`, utilizando métricas expresadas en unidades comerciales de repuestos para facilitar la interpretación del negocio:

| Métrica | Cálculo en código | Significado y lectura en el negocio |
| --- | --- | --- |
| **MAE** | `mean_absolute_error(actual, predicted)` | Error absoluto medio. Mide la magnitud promedio del error en unidades físicas de autopartes por día y sucursal. **Métrica principal**. |
| **RMSE** | `np.sqrt(mean_squared_error(actual, predicted))` | Raíz del error cuadrático medio. Penaliza con mayor severidad los errores o picos grandes de predicción. |
| **WAPE** | `sum(|actual - predicted|) / sum(actual)` | Error Porcentual Absoluto Ponderado. Mide el error relativo al volumen total de ventas reales, evitando divisiones por cero en días sin ventas. |
| **Bias** | `np.mean(predicted - actual)` | Sesgo medio de predicción. Un valor positivo indica sobreestimación de demanda; un valor negativo indica subestimación (riesgo de quiebre de stock). |
| **MASE** | `mae / mae_baseline` | Error Absoluto Escalado Medio. Compara el MAE del modelo frente al MAE de la línea base (*baseline*). Un valor $< 1.0$ demuestra que el modelo supera la heurística de referencia. |

Si el total de unidades reales del conjunto evaluado es cero (`total_units == 0`), la métrica WAPE se reporta como `None`. La ganancia porcentual de precisión respecto al modelo de referencia se calcula mediante `improvement_percent()`:

$$\text{Reducción MAE (\%)} = 100 \times \frac{\text{MAE}_{\text{baseline}} - \text{MAE}_{\text{modelo}}}{\text{MAE}_{\text{baseline}}}$$

## Regla de reposición

```text
target_stock = ceil(forecast_units + safety_units)
available_stock = stock_on_hand + incoming_units
suggested_order = max(0, target_stock - available_stock)
```

Ejemplo: pronóstico = 31,2; reserva = 4; stock = 20; entradas confirmadas = 8. El objetivo es 36 y la disponibilidad es 28, por lo que se sugieren 8 unidades nuevas.

`ceil()` redondea hacia arriba a unidades enteras. Nunca se propone una compra negativa. No se redondea el pronóstico antes de calcular las métricas.

La regla supone revisión diaria y que tanto lo confirmado como la compra nueva lleguen antes de abrir. Si la entrega tarda tres días, no basta multiplicar arbitrariamente el pronóstico de mañana: hay que pronosticar demanda durante el horizonte pertinente y considerar el inventario en tránsito.

La reserva es una elección manual de la demostración, no un intervalo de predicción ni una garantía de nivel de servicio. No se calcula un inventario óptimo económico.

## Límites de las conclusiones

Límites y alcance de las conclusiones
Datos sintéticos: Los datos de ventas han sido generados mediante modelos estocásticos que simulan patrones automotrices reales; no corresponden a la base transaccional histórica directa de un ERP operativo real.

Modelo no causal: El modelo pronostica patrones de demanda, pero no estima efectos causales directos de elasticidad-precio ni simula la variabilidad en los tiempos de entrega (lead times) de los proveedores de autopartes.

Evaluación estática de stock: La regla de reposición calcula la sugerencia puntual al cierre del día. No constituye un simulador de eventos discretos para medir costos financieros de almacenamiento, merma o venta perdida a lo largo del tiempo.

### Referencias técnicas

- **Tutorial y arquitectura del estimador:** [XGBoost Python API Reference](https://xgboost.readthedocs.io/en/stable/python/python_api.html#module-xgboost.sklearn)
- **Ejemplo práctico de series temporales en scikit-learn:** [Time-series lagging and evaluation in Scikit-Learn](https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html)
- **Métricas de evaluación (MAE / RMSE):** [Scikit-Learn Regression Metrics Reference](https://scikit-learn.org/stable/modules/classes.html#module-sklearn.metrics)
