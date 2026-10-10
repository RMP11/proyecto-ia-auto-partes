# Resultados del Experimento de Demanda de Autopartes

Pronóstico diario de ventas por producto y sucursal.

## Particiones de Datos

| Partición | Fechas | Filas |
|---|---|---:|
| train | 2023-01-15 a 2024-09-30 | 21875 |
| validation | 2024-10-01 a 2024-12-31 | 3220 |
| test | 2025-01-01 a 2025-06-30 | 6335 |

## Selección en Validación

| Candidato | MAE (unidades) |
|---|---:|
| Hasta 7 hojas | 0.722 |
| Hasta 15 hojas | 0.722 |
| Hasta 31 hojas | 0.722 |
| Referencia semanal (Lag-7) | 0.917 |

Elegido: **7 hojas máximas por árbol**.

## Evaluación Final en Test

| Métrica | Referencia semanal | Modelo |
|---|---:|---:|
| MAE (unidades) | 1.077 | **0.831** |
| RMSE (unidades) | 1.988 | **1.452** |
| MASE | 1.000 | **0.771** |
| Sesgo Medio | -0.010 | **-0.068** |
| WAPE | 74.8% | **57.7%** |

**Mejora del MAE respecto a la referencia: 2288.0%.**

### Desglose por Sucursal

| Sucursal | MAE Referencia | MAE Modelo | MASE |
|---|---:|---:|---:|
| SUC_01_CENTRO | 1.328 | 1.031 | 0.776 |
| SUC_02_NORTE | 1.178 | 0.878 | 0.745 |
| SUC_03_SUR | 0.984 | 0.772 | 0.785 |
| SUC_04_ESTE | 0.985 | 0.755 | 0.766 |
| SUC_05_OESTE | 0.909 | 0.717 | 0.788 |

### Desglose por Producto

| Producto | MAE Referencia | MAE Modelo |
|---|---:|---:|
| Amortiguador delantero | 0.814 | 0.680 |
| Batería 12V | 1.203 | 0.978 |
| Cigüeñal de motor | 0.034 | 0.048 |
| Filtro de aceite | 2.818 | 2.099 |
| Kit de embrague | 0.077 | 0.085 |
| Pastillas de freno | 2.429 | 1.748 |
| Sensor CKP | 0.164 | 0.176 |
