# Leer el código desde cero

## Vocabulario mínimo

- **Variable:** Nombre que guarda un dato, como `forecast_units`.
- **Función:** Instrucciones agrupadas para una tarea específica, como `replenishment_plan()`.
- **DataFrame:** Tabla de datos en Pandas que permite filtrar, limpiar y transformar las transacciones comerciales.
- **Rezago (*Lag*):** Valor de ventas de un día anterior. Por ejemplo, `sales_lag_7` corresponde a las unidades vendidas hace siete días para esa combinación de repuesto y sucursal.
- **Modelo de regresión (XGBoost):** Algoritmo basado en árboles de decisión (*Gradient Boosting*) que aprende a estimar una cantidad numérica continua (`units_sold`).
- **Pipeline:** Ensamblaje ordenado en Scikit-Learn que une el preprocesamiento de características (`preprocessing`) con el modelo final (`XGBRegressor`).
- **API:** Interfaz de programación que permite al cliente (frontend) solicitar pronósticos y sugerencias de reposición al servidor backend.
- **JSON:** Formato ligero de intercambio de datos estructurados entre el cliente y el servidor.

Los comentarios en Python comienzan con `#`. La sangría (indentación) forma parte de la sintaxis del lenguaje: conserva los cuatro espacios al modificar una función.

---

## Recorrido del flujo del proyecto

```markdown
Historial comercial (sales.csv) → Generación de rezagos y medias móviles → Partición cronológica
    → Entrenamiento de XGBoost (max_depth 3 vs 6) → Selección por menor MAE en Validación 
    → Evaluación final en Prueba → Exportación del modelo (.joblib) y métricas (metrics.json)

Formulario Web → Petición HTTP a la API → Carga de contexto histórico (14 días previos)
    → Inferencia de demanda con XGBoost → Aplicación de política de reposición (safety_units) 
    → Respuesta JSON → Renderizado de resultados, tabla de reposición y gráfico SVG
```

---

## `settings.py`: Decisiones del experimento

Define las constantes globales del sistema: las 5 sucursales (`branch_id`), el catálogo de autopartes (`product_id` / `category`), precios unitarios, las fechas de corte para el *split* temporal (`TRAIN_END`, `VALIDATION_END`), la semilla de reproducibilidad (`SEED = 42`) y las variables del sistema.

- **`FEATURES`:** Enumera las columnas que entran al modelo (`branch_id`, `product_id`, `category`, `unit_price`, `day_of_week`, `month`, `sales_lag_1`, `sales_lag_7`, `sales_lag_14`, `sales_mean_7`, `sales_mean_14`).
- **`TARGET = "units_sold"`:** Representa la variable objetivo que se desea predecir.

> **Nota de diseño:** Los datos de inventario (`stock_on_hand`, `incoming_units`, `safety_units`) **no** forman parte de `FEATURES`. El inventario sirve únicamente para calcular la orden de compra en la regla de negocio y no para predecir la demanda observada.

---

## `data.py`: Carga, validación y feature engineering

- **`generate_sales()` / Carga de datos:** Procesa la base transaccional histórica con las operaciones registradas entre 2023 y 2025.
- **`validate_sales()`:** Verifica la integridad del dataset. Rechaza duplicados en la clave compuesta `(branch_id, product_id, date)`, valores nulos, precios o unidades negativas y saltos en la continuidad del calendario.
- **`make_features()`:** Construye los rezagos y las medias móviles para una ventana de 14 días históricos. En Python, `values[-1]` obtiene la venta del día anterior (`sales_lag_1`), `values[-7]` la de hace una semana (`sales_lag_7`) y `values[-7:].mean()` el promedio móvil semanal (`sales_mean_7`).
- **`build_dataset()`:** Aplica iterativamente la transformación de características sobre la serie temporal por sucursal y producto.
- **`forecast_context()`:** Recupera el contexto de ventas previo a la fecha consultada en el formulario. La condición estricta `sales.date < target_date` aísla el historial para evitar *data leakage* (fuga de información).

## `train.py`: Aprendizaje y selección de modelo

Ejecuta el ciclo de entrenamiento mediante el `Pipeline` que integra el preprocesamiento de categorías y el estimador **XGBoost**:

```python
pipeline = build_model(max_depth_val)
pipeline.fit(train[FEATURES], train[TARGET])
```

Posteriormente, el sistema evalúa las candidaturas en el conjunto de validación:

```python
predictions = pipeline.predict(validation[FEATURES])
val_mae = mean_absolute_error(validation[TARGET], predictions)
```

Se comparan dos configuraciones de profundidad de árbol (`max_depth = 3` frente a `max_depth = 6`). Se selecciona la arquitectura que obtenga el menor **MAE** en validación. Únicamente tras congelar la configuración ganadora se ejecuta la evaluación sobre el conjunto de prueba (*Test*).

---

## `evaluation.py`: Medición del desempeño de negocio

Módulo de evaluación del modelo mediante tres funciones clave:

- **`split_by_date()`:** Divide el dataset cronológicamente en entrenamiento, validación y prueba, validando la continuidad de las fechas y la presencia de datos.
- **`regression_metrics()`:** Calcula el conjunto de métricas cuantitativas: `mae`, `rmse`, `wape`, `bias` y `mase`.
- **`improvement_percent()`:** Determina el porcentaje de reducción relativa del MAE frente a la línea base semanal (*baseline* $t-7$).

> No se emplean métricas de clasificación (como *Precision*, *Recall* o *F1-score*) ya que el objetivo es estimar el volumen continuo de repuestos a reponer, no clasificar una categoría binaria.

---

## `inventory.py`: Lógica de reposición de stock

Contiene la función desacoplada del modelo de Machine Learning (`replenishment_plan()`). Implementa la regla operativa del negocio:

$$\text{target\_stock} = \lceil \text{forecast\_units} + \text{safety\_units} \rceil$$
$$\text{suggested\_order} = \max(0, \text{target\_stock} - (\text{stock\_on\_hand} + \text{incoming\_units}))$$

Mantener esta lógica en un módulo independiente garantiza que modificar los parámetros de inventario en la interfaz actualice la orden propuesta sin alterar de manera espuria el pronóstico de ventas emitido por XGBoost.

---

## `schemas.py` y `main.py`: Backend y API

- **`schemas.py`:** Define los modelos Pydantic (`ForecastInput`, etc.) que validan los tipos de datos y rangos permitidos provenientes del formulario.
- **`main.py`:** Expone los *endpoints* de la aplicación FastAPI / Flask. Al arrancar el servidor, carga en memoria el pipeline guardado (`.joblib`), las métricas (`metrics.json`) y el archivo histórico `sales.csv`.

Para garantizar la consistencia, el servidor puede verificar la huella SHA-256 del dataset original. Solo se deben cargar artefactos `.joblib` generados localmente por el pipeline de entrenamiento para evitar vulnerabilidades de ejecución de código arbitrario mediante deserialización.

---

## Arquitectura Frontend (Interfaz Web)

El frontend se compone de tres archivos principales:

- **`index.html`:** Estructura los selectores de sucursal (`branch_id`), repuesto (`product_id`), parámetros de stock y botones de acción.
- **`styles.css`:** Define la distribución visual, tipografía corporativa y diseño adaptativo (*responsive*).
- **`app.js`:** Captura las entradas del usuario, realiza las peticiones asíncronas (`fetch()`) a la API, procesa las respuestas en JSON y renderiza dinámicamente el gráfico SVG con las ventas históricas y la predicción.

El navegador no realiza cálculos de Machine Learning ni entrena el modelo. Todas las métricas mostradas provienen del backend. Si el usuario modifica una entrada mientras se procesa una solicitud anterior, el cliente descarta la respuesta previa para prevenir incoherencias visuales.

---

## Modificaciones recomendadas para experimentación

1. **Simulación de inventario:** Modificar el `stock_on_hand` o la reserva (`safety_units`) en la interfaz para validar cómo se ajusta la cantidad propuesta en la sugerencia de reposición.
2. **Evaluación de Baseline:** Reemplazar el cálculo del *baseline* ($t-7$) por un promedio móvil de los últimos 7 días (`sales_mean_7`) y evaluar el impacto en la métrica `mase`.
3. **Sintonización de XGBoost:** Probar una tercera configuración de hiperparámetros (por ejemplo, ajustar `learning_rate` o incorporar `max_depth = 4`) y seleccionar el modelo ganador guiándose exclusivamente por el conjunto de validación.
4. **Ampliación de catálogo:** Agregar nuevas familias de autopartes al dataset sintético, reejecutar el pipeline de entrenamiento (`train.py`) y comprobar las métricas resultantes en `evaluation.py`.
