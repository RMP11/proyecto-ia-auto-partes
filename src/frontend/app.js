// The browser sends a scenario. The backend builds features and predicts sales.
const form = document.querySelector("#forecast-form");
const button = document.querySelector("#forecast-button");
const scenarios = {
  regular: {
    product_id: "MILK",
    planned_promotion: 0,
    stock_on_hand: 15,
    incoming_units: 0,
    safety_units: 5,
  },
  promotion: {
    product_id: "MILK",
    planned_promotion: 1,
    stock_on_hand: 15,
    incoming_units: 0,
    safety_units: 5,
  },
  stocked: {
    product_id: "MILK",
    planned_promotion: 0,
    stock_on_hand: 150,
    incoming_units: 0,
    safety_units: 5,
  },
  slow: {
    product_id: "COFFEE",
    planned_promotion: 0,
    stock_on_hand: 1,
    incoming_units: 0,
    safety_units: 1,
  },
};
let inputRevision = 0;
let catalogReady = false;

function setText(selector, value) {
  document.querySelector(selector).textContent = value;
}

function number(value, digits = 1) {
  return new Intl.NumberFormat("es", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function shortDate(value) {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function showError(selector, message) {
  const element = document.querySelector(selector);
  element.textContent = message;
  element.hidden = !message;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    signal: AbortSignal.timeout(15000),
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 422)
      throw new Error(
        "Revisa el producto, la fecha de simulación y las cantidades enteras no negativas.",
      );
    if (response.status === 503)
      throw new Error(
        "Falta el modelo o el historial. Genera los datos, entrena y reinicia el servidor; consulta README.md.",
      );
    throw new Error(
      "No se pudo completar la consulta. Revisa que el servidor esté funcionando.",
    );
  }
  return data;
}

function hidePreviousResult() {
  inputRevision += 1;
  document.querySelector("#forecast-result").hidden = true;
  document.querySelector("#empty-result").hidden = false;
  document.querySelector("#history-content").hidden = true;
  document.querySelector("#chart-placeholder").hidden = false;
  showError("#form-error", "");
}

form.addEventListener("input", hidePreviousResult);
document.querySelectorAll("[data-scenario]").forEach((control) => {
  control.addEventListener("click", () => {
    if (!catalogReady) return;
    for (const [name, value] of Object.entries(
      scenarios[control.dataset.scenario],
    )) {
      form.elements[name].value = value;
    }
    hidePreviousResult();
  });
});

document.querySelectorAll("[data-panel]").forEach((control) => {
  control.addEventListener("click", () => {
    document
      .querySelectorAll("[data-panel]")
      .forEach((item) =>
        item.setAttribute("aria-pressed", String(item === control)),
      );
    document.querySelectorAll(".panel").forEach((panel) => {
      panel.hidden = panel.id !== control.dataset.panel;
    });
  });
});

function addTableRow(body, values) {
  const row = document.createElement("tr");
  values.forEach((value, index) => {
    const cell = document.createElement(index === 0 ? "th" : "td");
    if (index === 0) cell.scope = "row";
    cell.textContent = value;
    row.append(cell);
  });
  body.append(row);
}

function svgElement(tag, attributes, text = "") {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes))
    element.setAttribute(key, value);
  element.textContent = text;
  return element;
}

function renderHistory(result) {
  const chart = document.querySelector("#history-chart");
  const points = [
    ...result.history,
    { date: result.forecast_date, units_sold: result.forecast_units },
  ];
  const maximum =
    Math.max(1, ...points.map((point) => point.units_sold)) * 1.15;
  const plotHeight = 160;
  chart.replaceChildren();
  chart.setAttribute(
    "aria-label",
    `Ventas de los últimos 14 días de ${result.product_name}; pronóstico para ${shortDate(result.forecast_date)}: ${number(result.forecast_units)} unidades. Tabla de valores disponible debajo.`,
  );
  [0, 0.5, 1].forEach((fraction) => {
    const y = 185 - fraction * plotHeight;
    chart.append(
      svgElement("line", { x1: 45, x2: 827, y1: y, y2: y, stroke: "#e1e6e1" }),
    );
    chart.append(
      svgElement(
        "text",
        {
          x: 35,
          y: y + 4,
          fill: "#697579",
          "text-anchor": "end",
          "font-size": 10,
        },
        number(maximum * fraction, 0),
      ),
    );
  });
  points.forEach((point, index) => {
    const x = 51 + index * 52;
    const height = (point.units_sold / maximum) * plotHeight;
    const bar = svgElement("rect", {
      x,
      y: 185 - height,
      width: 32,
      height,
      rx: 3,
      fill: index === 14 ? "var(--primary)" : "var(--text-secondary)",
    });
    bar.append(
      svgElement(
        "title",
        {},
        `${shortDate(point.date)}: ${number(point.units_sold)} unidades${index === 14 ? " (pronóstico)" : ""}`,
      ),
    );
    chart.append(bar);
    chart.append(
      svgElement(
        "text",
        {
          x: x + 16,
          y: 205,
          fill: "#697579",
          "text-anchor": "middle",
          "font-size": 10,
        },
        point.date.slice(8),
      ),
    );
  });
  const body = document.querySelector("#history-body");
  body.replaceChildren();
  points.forEach((point, index) =>
    addTableRow(body, [
      shortDate(point.date),
      number(point.units_sold, index === 14 ? 1 : 0),
      index === 14 ? "Pronóstico" : "Observado",
    ]),
  );
  const features = result.features;
  const summary = document.querySelector("#feature-summary");
  summary.replaceChildren();
  const descriptions = [
    `Día anterior: ${number(features.sales_lag_1, 0)} unidades.`,
    `Hace 7 días: ${number(features.sales_lag_7, 0)} unidades.`,
    `Hace 14 días: ${number(features.sales_lag_14, 0)} unidades.`,
    `Media de 7 días: ${number(features.sales_mean_7)} unidades.`,
    `Media de 14 días: ${number(features.sales_mean_14)} unidades.`,
  ];
  descriptions.forEach((description) => {
    const paragraph = document.createElement("p");
    paragraph.textContent = description;
    summary.append(paragraph);
  });
  document.querySelector("#history-content").hidden = false;
  document.querySelector("#chart-placeholder").hidden = true;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const inputs = {
    product_id: form.elements.product_id.value,
    forecast_date: form.elements.forecast_date.value,
    branch_id: form.elements.branch_id.value,
  };

  ["stock_on_hand", "incoming_units", "safety_units"].forEach((name) => {
    inputs[name] = Number(form.elements[name].value);
  });

  const submittedRevision = inputRevision;
  button.disabled = true;
  button.textContent = "Calculando…";
  showError("#form-error", "");
  try {
    const result = await requestJson("/api/forecast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(inputs),
    });
    if (submittedRevision !== inputRevision) return;
    document.querySelector("#empty-result").hidden = true;
    document.querySelector("#forecast-result").hidden = false;
    setText(
      "#result-caption",
      `${result.product_name} · ${shortDate(result.forecast_date)}`,
    );
    setText("#forecast-units", number(result.forecast_units));
    setText("#baseline-units", `${number(result.baseline_units, 0)} u.`);
    setText("#order-units", `${number(result.plan.suggested_order, 0)} u.`);
    setText(
      "#order-description",
      result.plan.suggested_order > 0
        ? "Unidades adicionales para alcanzar el objetivo de stock de este escenario."
        : "El stock y las entradas confirmadas alcanzan el objetivo calculado.",
    );
    setText("#target-stock", `${number(result.plan.target_stock, 0)} u.`);
    setText("#available-stock", `${number(result.plan.available_stock, 0)} u.`);
    renderHistory(result);
  } catch (error) {
    showError(
      "#form-error",
      error.name === "TimeoutError"
        ? "La consulta tardó demasiado. Intenta nuevamente."
        : error.message,
    );
  } finally {
    button.disabled = false;
    button.textContent = "Calcular pronóstico ↗";
  }
});

function renderMetrics(report) {
  const { model, baseline, mae_improvement_percent: improvement } = report.test;
  setText("#metric-mae", `${number(model.mae, 2)} u.`);
  setText("#metric-baseline", `${number(baseline.mae, 2)} u.`);
  setText(
    "#metric-improvement",
    improvement === null ? "No definido" : `${number(Math.abs(improvement))}%`,
  );
  setText(
    "#improvement-label",
    improvement !== null && improvement < 0
      ? "Aumento del error"
      : "Reducción del error",
  );
  const metricsBody = document.querySelector("#metrics-body");
  metricsBody.replaceChildren();
  [
    ["mae", "MAE · unidades"],
    ["mase", "MASE · unidades"],
    ["rmse", "RMSE · unidades"],
    ["wape", "WAPE"],
    ["bias", "Sesgo · unidades"],
  ].forEach(([key, label]) => {
    const format = (value) =>
      value === null
        ? "No definido"
        : key === "wape"
          ? `${number(value * 100)}%`
          : number(value, 2);

    console.log(baseline)
    console.log(model)
    addTableRow(metricsBody, [
      label,
      format(baseline[key]),
      format(model[key]),
    ]);
  });

  const productBody = document.querySelector("#product-body");
  report.by_product.forEach((product) =>
    addTableRow(productBody, [
      product.name.split(" · ")[0],
      number(product.baseline.mae, 2),
      number(product.model.mae, 2),
    ]),
  );
  const labels = {
    train: "Entrenamiento",
    validation: "Validación",
    test: "Prueba final",
  };
  for (const [name, split] of Object.entries(report.splits)) {
    const element = document.createElement("div");
    element.className = "split";
    const title = document.createElement("h4");
    title.textContent = labels[name];
    const description = document.createElement("p");
    description.textContent = `${shortDate(split.first_date)} → ${shortDate(split.last_date)} · ${split.rows} filas`;
    element.append(title, description);
    document.querySelector("#split-timeline").append(element);
  }
  const total = Object.values(report.splits).reduce(
    (sum, split) => sum + split.rows,
    0,
  );
  setText(
    "#dataset-summary",
    `${total.toLocaleString("es")} ejemplos utilizables después de reunir 14 días de historial por producto.`,
  );
  setText(
    "#selection-summary",
    `Se compararon árboles de hasta 7 y 15 hojas. Se eligieron ${report.selected_max_leaf_nodes} hojas por el menor MAE de validación. No se entrenó con la prueba.`,
  );

  const branchBody = document.querySelector("#branch-body");

  report.by_branch.forEach((branch) => {
    addTableRow(branchBody, [
      branch.branch_id,
      number(branch.baseline.mae, 2),
      number(branch.model.mae, 2),
    ]);
  });
}

async function initialize() {
  try {
    const [catalog, report] = await Promise.all([
      requestJson("/api/catalog"),
      requestJson("/api/metrics"),
    ]);
    const selectSucursales = form.elements.branch_id;
    const select = form.elements.product_id;
    select.replaceChildren();
    catalog.products.forEach((product) => {
      const option = document.createElement("option");
      option.value = product.product_id;
      option.textContent = product.name;
      select.append(option);
    });

    selectSucursales.replaceChildren();
    catalog.branches.forEach((branch) => {
      const option = document.createElement("option");
      option.value = branch.branch_id;
      option.textContent = branch.name;
      selectSucursales.append(option);
    });

    select.value = "REP_FILTRO_ACEITE";
    form.elements.forecast_date.min = catalog.first_forecast_date;
    form.elements.forecast_date.max = catalog.last_forecast_date;
    form.elements.forecast_date.value = catalog.default_forecast_date;
    renderMetrics(report);

    catalogReady = true;
    button.disabled = false;
    setText("#connection-status", "Modelo conectado");
  } catch (error) {
    console.log(error);
    setText("#connection-status", "Modelo no disponible");
    showError("#global-error", error.message);
  }
}

initialize();
