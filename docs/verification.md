# Comprobaciones de la entrega

## Experimento ejecutado

- Registros transaccionales y ejemplos procesados con historial completo de 14 días.
- Dos configuraciones de profundidad de árbol para XGBoost (max_depth 3 y 6) entrenadas con el período inicial.
- Selección de la arquitectura óptima guiada por el menor MAE en la partición de validación.
- Evaluación sobre el conjunto de prueba (Test): cálculo de métricas de desempeño (MAE, RMSE, WAPE, Bias, MASE) frente a la referencia semanal (baseline t-7).
- Métricas, pronósticos y artefactos (.joblib y metrics.json) exportados dinámicamente desde el backend.

Los resultados describen el comportamiento del simulador de autopartes, no datos reales de una empresa.

---

## Frontend y escenarios de simulación

- La sintaxis de JavaScript se valida con: node --check frontend/app.js
- Se comprueban identificadores HTML, etiquetas de formulario, recursos estáticos y enlaces del proyecto.
- Los escenarios de prueba se ejecutan contra la API y sus respuestas se almacenan en artifacts/example_forecasts.json.
- Se verifica que modificar únicamente las existencias (stock_on_hand) o la reserva (safety_units) modifique la propuesta de reposición sin alterar la predicción de ventas emitida por XGBoost, y que un inventario abundante no genere órdenes de compra innecesarias.

---

## Revisión manual pendiente

1. Iniciar el servidor local ejecutando: python run.py
2. Probar los escenarios predeterminados en la interfaz y recorrer los módulos del sistema.
3. Verificar la renderización del gráfico SVG de ventas, la tabla histórica y los avisos de validación.
4. Modificar un campo del formulario y confirmar que se oculte la estimación anterior hasta volver a calcular.
5. Probar la navegación por teclado y la adaptabilidad de la pantalla en dispositivos móviles o ventanas estrechas.

Estas verificaciones se declaran como pruebas manuales pendientes por ejecutar en el navegador.
