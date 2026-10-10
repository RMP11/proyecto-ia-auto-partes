# Inventario a tiempo

Ejemplo educativo completo de **pronóstico de ventas y reposición diaria** para una sucursal ficticia. Incluye datos sintéticos, entrenamiento, evaluación, backend e interfaz web.

El código, las funciones y los comentarios están en inglés. La interfaz y la documentación están en español. No contiene nombres de personas ni datos comerciales reales.

## La pregunta del proyecto

**Al cerrar la tienda, ¿cuántas unidades se espera vender de un producto al día siguiente de que sucursal y cuántas convendría reponer antes de abrir?**

Hay dos tareas diferentes:

1. El modelo estima ventas utilizando historial, calendario y que sucursal.
2. Una regla calcula la reposición a partir del pronóstico, la reserva manual, el stock y las entradas confirmadas.

La aplicación muestra una propuesta. No registra compras ni modifica el inventario.

## Qué incluye

- Historial sintético de 7 productos y 5 sucursales, de enero de 2023 a junio de 2025: **31.920 filas producto-día**.
- **31.430 ejemplos de modelado**, después de reunir 14 días de historial inicial por producto.
- Referencia semanal: repetir las ventas del mismo día de la semana anterior.
- Un modelo global de árboles de regresión (XGBoost) que comparte aprendizaje entre todos los productos y las 5 sucursales.
- Tres configuraciones de complejidad de árboles (máximo 7, 15 y 31 hojas) comparadas en el conjunto de validación temporal, seleccionando el candidato con menor MAE.
- API FastAPI, frontend HTML/CSS/JavaScript.
- Documentación para empezar, leer el código, explicar la clase y adaptar el ejemplo.

## Empezar desde cero

### 1. Preparar Python y la carpeta

Se utilizó **Python 3.12**. Instálalo desde [python.org](https://www.python.org/downloads/) si no lo tienes. Descomprime el ZIP y abre una terminal dentro de la carpeta `inventory-forecast`, donde están este archivo y `run.py`.

Una terminal permite escribir instrucciones. Ejecuta una línea a la vez y espera a que termine.

### 2. Instalar las dependencias

En macOS o Linux, desde la carpeta que contiene el proyecto:

```bash
cd inventory-forecast
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
```

En Windows PowerShell:

```powershell
cd inventory-forecast
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

Si la terminal ya está dentro de `inventory-forecast`, omite la primera línea. `.venv` es un entorno que mantiene las librerías separadas de otros proyectos. La instalación requiere Internet; después, el ejemplo funciona localmente sin claves ni servicios externos.

### 3. Iniciar la aplicación

macOS o Linux, con el entorno activado:

```bash
python run.py
```

Windows:

```powershell
.\.venv\Scripts\python.exe run.py
```

Abre **http://127.0.0.1:8981**. Mantén la terminal abierta; para detener el servidor pulsa `Ctrl+C`. El puerto es diferente al del ejemplo de cuotas, así que ambos pueden ejecutarse por separado.

El paquete incluye datos y modelo entrenado. Si faltan, el comando los genera antes de iniciar.

### 4. Explorar

1. Pulsa **Día normal** y luego **Calcular pronóstico**.
2. Repite con **Con promoción** y compara las estimaciones. Este cambio de escenario no demuestra un efecto causal real.
3. Pulsa **Stock abundante**. Observa que cambia la compra sugerida, pero el stock no es una entrada del modelo de ventas.
4. Prueba **Baja rotación** para ver el comportamiento de un producto con ventas pequeñas y días con cero unidades.
5. Revisa el gráfico y despliega su tabla de valores.
6. Abre **Resultados** y **Datos y método**.

La fecha predeterminada es **1 de julio de 2025**, el día siguiente al último registro simulado. No es la fecha actual de tu computadora. El selector permite simular desde el 1 de enero hasta el 1 de julio de 2025; para cada día usa únicamente sus 14 días anteriores.

## Repetir el experimento

Detén el servidor y ejecuta:

```bash
python -m app.data
python -m app.train
python run.py
```

En Windows reemplaza `python` por `.\.venv\Scripts\python.exe`.

También puedes regenerar, entrenar e iniciar con:

```bash
python run.py --rebuild
```

La regeneración reemplaza los CSV y artefactos del ejemplo. Si hiciste cambios que deseas conservar, copia primero la carpeta. Para entrenar sobre un CSV editado, ejecuta solo `python -m app.train` y reinicia el servidor. El entrenamiento reconstruye las variables desde `data/sales.csv`; editar `features.csv` no cambia el origen del experimento.

## Estructura del proyecto

```text
inventory-forecast/
├── README.md
├── run.py                       # Inicia el servidor local
├── requirements.txt             # Dependencias directas
├── requirements-lock.txt        # Versiones exactas probadas
└── src
    ├── app/
    │   ├── settings.py              # Catálogo, rutas, fechas y variables
    │   ├── data.py                  # Simulación y construcción del historial
    │   ├── evaluation.py            # Particiones temporales y métricas
    │   ├── train.py                 # Entrenamiento, selección y exportación
    │   ├── inventory.py             # Regla de reposición, separada del modelo
    │   ├── schemas.py               # Validación de las solicitudes
    │   └── main.py                  # API y entrega del frontend
    ├── frontend/
    │   ├── index.html               # Formulario, resultados y método
    │   ├── styles.css               # Apariencia y adaptación de pantalla
    │   └── app.js                   # Consultas y gráfico sin librerías externas
    ├── data/
    │   ├── sales.csv                # Historial original sintético
    │   ├── features.csv             # Variables y resultado por producto-día
    │   ├── train.csv
    │   ├── validation.csv
    │   └── test.csv
    └── artifacts/
        ├── model.joblib             # Pipeline entrenado
        ├── metrics.json             # Cifras que consulta la interfaz
        ├── evaluation.md            # Informe legible del experimento
        ├── test_predictions.csv     # Valores reales, referencia y pronóstico
        └── example_forecasts.json   # Respuestas verificadas de los escenarios
```

## Documentación

- [Contexto y diccionario de datos](docs/data.md).
- [Modelo, validación y métricas](docs/methodology.md).
- [Leer el código desde cero](docs/code-guide.md).
- [API y peticiones de ejemplo](docs/api.md).
- [Resultados del entrenamiento](src/artifacts/evaluation.md).
- [Comprobaciones y límites de verificación](docs/verification.md).

## Alcance

Proyección de demanda: Pronostica ventas diarias por producto y sucursal usando XGBoost sobre el historial 2024– ultimo registro, asumiendo tiendas abiertas diariamente y recepciones de mercancía antes de abrir.

Simulador local: Incluye una interfaz local para comparar el modelo contra la regla manual (mismo día de la semana anterior) mediante métricas e historial.

## Limitaciones

Sin gestión de stock ni costos: Solo predice la demanda; no simula la evolución diaria del inventario físico ni calcula costos de almacenamiento.

Sin validación en producción: Las mejoras se evalúan con métricas (MAE/MASE), sin afirmar un ahorro o reducción real de faltantes hasta su uso en vivo.

Sin garantías en el método manual: La reserva manual previa no asegura un nivel de servicio estandarizado.

Infraestructura básica: Funciona en un servidor local sin inicio de sesión, historial de consultas.

## Referencias técnicas

- [scikit-learn: variables rezagadas y evaluación temporal](https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html).
- [scikit-learn: error absoluto medio](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html).
