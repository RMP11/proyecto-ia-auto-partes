# Contexto

## Proceso representado

Al cierre del día, una sucursal evalúa el histórico reciente de ventas, variaciones de demanda y los niveles actuales de existencias. A partir de esta información, busca estimar la demanda prevista para la jornada siguiente y generar automáticamente una propuesta dependiendo de la reposición de stock.

Una observación representa un repuesto o autoparte en una sucursal específica durante un día determinado. La unidad de medida corresponde al empaque o presentación comercial en la que se expende el producto (por ejemplo: una caja de pastillas de freno, un filtro de aceite, un juego de bujías, un amortiguador individual, un bidón de aceite sintético de 4 litros o un empaque de ampolletas halógenas).

## Calendario

Para pronosticar el 1 de julio de 2025 se utiliza información conocida,  es decir al finalizar el 30 de junio

## Historial original: `sales.csv`

| Campo | Significado | Restricción |
|---|---|---|
| `date` | Fecha de la operación | Calendario diario completo (`YYYY-MM-DD`), sin hora. |
| `branch_id` | Identificador de la sucursal | Puntos de venta registrados (ej. `SUC_01_CENTRO` a `SUC_05_OESTE`). |
| `product_id` | Código del repuesto | Código único de autoparte (ej. `REP_AMORTIGUADOR_DEL`, `REP_SENSOR_CKP`). |
| `category` | Línea de producto / categoría | Categorización del catálogo (ej. `Suspensión y Dirección`, `Electrónica y Sensores`). |
| `unit_price` | Precio unitario de venta | Valor decimal positivo en moneda local (ej. 87.15, 45.37). |
| `units_sold` | Unidades/piezas vendidas | Entero no negativo. Muestra frecuencia de ceros por demanda intermitente. |

El conjunto de datos abarca el período comprendido entre el **1 de enero de 2023 y el 30 de junio de 2025** (un total de **912 días de calendario**), registrando un total de **31.921 líneas** en la estructura del archivo. El historial se almacena ordenado cronológicamente por fecha, sucursal y producto.

El generador de datos combina una demanda base según el tipo de repuesto, patrones por día de la semana, estacionalidad anual del sector automotriz, tendencia general, variaciones de precio y ruido estocástico. El catálogo contempla una importante proporción de días con **ventas en cero**, simulando la rotación intermitente y dispersa propia del inventario de autopartes. Las relaciones e indicadores son sintéticos generados para el desarrollo.

## Variables de entrada del modelo

| Campo / Feature | Descripción / Cálculo | Disponible antes de predecir el día |
|---|---|---|
| `branch_id` | Identificador de la sucursal de venta | Sí. |
| `product_id` | Código del repuesto a pronosticar | Sí. |
| `category` | Categoría o línea de la autoparte | Sí. |
| `unit_price` | Precio unitario de venta del producto | Sí. |
| `day_of_week` | Día de la semana (Lunes = 0, Domingo = 6) | Sí. |
| `month` | Mes del año (1 a 12) | Sí. |
| `sales_lag_1` | Unidades vendidas el día anterior | Sí, tras el cierre del punto de venta. |
| `sales_lag_7` | Unidades vendidas hace siete días | Sí. |
| `sales_lag_14` | Unidades vendidas hace catorce días | Sí. |
| `sales_mean_7` | Promedio móvil de ventas de los últimos 7 días | Sí. |
| `sales_mean_14` | Promedio móvil de ventas de los últimos 14 días | Sí. |

La variable objetivo (*target*) es `units_sold` del día a predecir. Nunca se utiliza el valor del propio día como entrada para evitar fuga de información (*data leakage*). La fecha (`date`) se emplea exclusivamente para ordenar la serie temporal y dividir los períodos de entrenamiento y evaluación.

## Entradas exclusivas de la reposición

| Campo | Significado | Rango / Restricción |
|---|---|---|
| `stock_on_hand` | Existencias utilizables en el almacén de la sucursal al cierre previo | Entero no negativo (0 a 100,000). |
| `incoming_units` | Repuestos en tránsito confirmados para ingresar antes de la apertura | Entero no negativo (0 a 100,000). |
| `safety_units` | Reserva o stock de seguridad manual para cubrir variaciones de demanda | Entero no negativo (0 a 1,000). |

Estas tres cantidades **no forman parte del entrenamiento del modelo de machine learning (XGBoost)**. Su función es operativa: ajustar el valor de `stock_on_hand`, `incoming_units` o `safety_units` modifica directamente la cantidad sugerida en la orden de compra o transferencia de stock, pero no altera la predicción de ventas esperada. Los rangos definidos corresponden a reglas de validación del sistema, no a niveles estáticos recomendados.

## Ventas en cero, registros ausentes y quiebres de stock

* **Ventas en cero (`units_sold = 0`):** Representa una observación válida de demanda donde el repuesto estuvo disponible en la sucursal pero no tuvo salida.
* **Registros ausentes:** Corresponden a días faltantes en la secuencia temporal. El pipeline los rechaza al interrumpir la continuidad del calendario por producto y sucursal.
* **Quiebres de stock:** Si el repuesto está agotado, registrar cero ventas oculta la demanda real (demanda censurada). El conjunto de datos asume disponibilidad continua de inventario.

El historial asume que las ventas registradas equivalen a la demanda observada. No contempla devoluciones, cierres de sucursal, sustitución de repuestos, variaciones de precio ni obsolescencia.

## Validaciones y consistencia de datos

* **Pipelined Data Check:** Se valida la presencia de las columnas requeridas, la ausencia de valores nulos o duplicados por la combinación `(branch_id, product_id, date)`, la pertenecia al catálogo oficial de autopartes, precios unitarios positivos, unidades vendidas enteras y la continuidad del calendario diario por sucursal.
* **Integridad de la API:** La interfaz de inferencia rechaza repuestos o sucursales no contemplados, fechas fuera del rango permitido, volúmenes negativos o fraccionarios, campos no estructurados y registros incompletos.
* **Generación unificada de características:** La función `make_features()` procesa tanto el conjunto de datos para el entrenamiento de XGBoost como las solicitudes de inferencia en tiempo real. La función `forecast_context()` aísla únicamente el historial previo a la fecha a predecir; pruebas unitarias automatizadas aseguran que modificaciones en la fecha objetivo o en días posteriores no alteren las variables de entrada (*prevención de data leakage*).
* **Consistencia del entorno:** El archivo `sales.csv` actúa como una base de datos histórica fija para el entorno de desarrollo y demostración. Si el archivo sufre modificaciones tras el entrenamiento, el servidor requiere la reejecución del pipeline. En una arquitectura de producción real, el flujo de ingesta diaria de transacciones opera de forma desacoplada del ciclo de reentrenamiento programado del modelo.
