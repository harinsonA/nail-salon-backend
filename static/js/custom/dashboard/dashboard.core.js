/* ==========================================================================
   DASHBOARD CORE — paleta, fetch, defaults y render compartidos
   --------------------------------------------------------------------------
   Se carga DESPUÉS de Chart.js y ANTES de los scripts de cada gráfico.
   El backend manda valores + etiquetas; los colores se asignan aquí (tema
   "Tierra" centralizado) según el `key` de cada dataset.
   ========================================================================== */
(function (window) {
  "use strict";

  // Colores por key de dataset (alineados con colors.main.css)
  var PALETTE = {
    // Series temporales
    atendidas: { border: "#a67f56", background: "rgba(166, 127, 86, 0.15)" }, // arena
    unicos: { border: "#5f7d99", background: "rgba(95, 125, 153, 0.15)" }, // azul invierno
    facturado: { border: "#a67f56", background: "rgba(166, 127, 86, 0.7)" }, // arena
    cobrado: { border: "#7d8b4e", background: "rgba(125, 139, 78, 0.7)" }, // oliva
    // Barras categóricas (un solo color de dataset)
    servicios: { border: "#5f7d99", background: "rgba(95, 125, 153, 0.7)" }, // azul
    ingresos: { border: "#a67f56", background: "rgba(166, 127, 86, 0.7)" }, // arena
    // Estados de cita (slices del doughnut)
    pendiente: { border: "#c8843c", background: "#c8843c" }, // tostado
    completada: { border: "#7d8b4e", background: "#7d8b4e" }, // oliva
    cancelada: { border: "#9b4a4a", background: "#9b4a4a" }, // burdeo
    // Métodos de pago (slices del pie)
    efectivo: { border: "#7d8b4e", background: "#7d8b4e" }, // oliva
    tarjeta: { border: "#5f7d99", background: "#5f7d99" }, // azul
    transferencia: { border: "#c8843c", background: "#c8843c" }, // tostado
    cheque: { border: "#8b6655", background: "#8b6655" }, // cocoa
  };
  var FALLBACK = { border: "#8b6655", background: "rgba(139, 102, 85, 0.15)" };

  // Paleta categórica para slices/barras sin key propia (se cicla por índice)
  var CATEGORICAL = [
    "#a67f56", "#5f7d99", "#7d8b4e", "#c8843c",
    "#9b4a4a", "#8b6655", "#c0a294", "#5e4438",
  ];

  function colorFor(key) {
    return PALETTE[key] || FALLBACK;
  }

  // Lista de colores para datasets con `keys` (uno por punto/slice/barra)
  function colorsFor(keys) {
    return keys.map(function (key, index) {
      var entry = PALETTE[key];
      return entry ? entry.border : CATEGORICAL[index % CATEGORICAL.length];
    });
  }

  // Defaults globales de Chart.js (fuente, color de texto, leyenda)
  function applyDefaults() {
    if (!window.Chart) return;
    var d = window.Chart.defaults;
    d.font.family = '"Segoe UI", system-ui, -apple-system, sans-serif';
    d.color = "#5e4438"; // cocoa-700
    d.plugins.legend.position = "bottom";
    d.plugins.legend.labels.usePointStyle = true;
    d.plugins.legend.labels.boxWidth = 8;
  }

  // GET del contrato JSON; admite params (querystring) para filtros futuros
  function fetchJSON(url, params) {
    var finalUrl = url;
    if (params && Object.keys(params).length) {
      var qs = new URLSearchParams(params).toString();
      finalUrl += (url.indexOf("?") === -1 ? "?" : "&") + qs;
    }
    return fetch(finalUrl, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    }).then(function (res) {
      if (!res.ok) {
        return res
          .json()
          .catch(function () {
            return {};
          })
          .then(function (body) {
            var err = new Error(body.message || "Error " + res.status);
            err.status = res.status;
            throw err;
          });
      }
      return res.json();
    });
  }

  // Alterna los estados loading/empty/error/ok del contenedor del canvas
  function setState(canvas, state) {
    var container = canvas.closest(".dashboard-chart");
    if (!container) return;
    var states = container.querySelectorAll("[data-state]");
    states.forEach(function (el) {
      el.classList.toggle("d-none", el.getAttribute("data-state") !== state);
    });
    canvas.classList.toggle("d-none", state !== "ok");
  }

  function isCircular(type) {
    return type === "pie" || type === "doughnut";
  }

  // Aplica colores de la paleta a cada dataset.
  // - datasets con `keys` (array): un color por punto (pie/doughnut o barra multicolor).
  // - datasets con `key` (string): un solo color (line / barra agrupada).
  function buildDatasets(payload, type) {
    return payload.datasets.map(function (ds) {
      // Color por punto (slices o barras categóricas)
      if (ds.keys && ds.keys.length) {
        var colors = colorsFor(ds.keys);
        var d = { label: ds.label, data: ds.data, backgroundColor: colors };
        if (isCircular(type)) {
          d.borderColor = "#fff";
          d.borderWidth = 2;
        } else {
          d.borderColor = colors;
          d.borderWidth = 0;
        }
        return d;
      }
      // Color único de dataset
      var color = colorFor(ds.key);
      var base = {
        label: ds.label,
        data: ds.data,
        borderColor: color.border,
        backgroundColor: color.background,
      };
      if (type === "line") {
        base.borderWidth = 2;
        base.tension = 0.35;
        base.fill = true;
        base.pointBackgroundColor = color.border;
        base.pointRadius = 3;
        base.pointHoverRadius = 5;
      } else {
        base.borderWidth = 0;
      }
      return base;
    });
  }

  // Renderiza un gráfico a partir del contrato JSON uniforme
  function renderChart(canvasId, type, payload, optionsExtra) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    var noData =
      !payload ||
      !payload.datasets ||
      !payload.datasets.length ||
      (payload.meta && payload.meta.empty);
    if (noData) {
      setState(canvas, "empty");
      return null;
    }
    setState(canvas, "ok");
    var defaults = { responsive: true, maintainAspectRatio: false };
    if (!isCircular(type)) {
      // Solo los gráficos cartesianos (line/bar) usan ejes
      defaults.interaction = { mode: "index", intersect: false };
      defaults.scales = { y: { beginAtZero: true, ticks: { precision: 0 } } };
    }
    var options = Object.assign(defaults, optionsExtra || {});
    return new window.Chart(canvas, {
      type: type,
      data: { labels: payload.labels, datasets: buildDatasets(payload, type) },
      options: options,
    });
  }

  // Atajo: lee data-url del canvas, hace fetch y renderiza, gestionando estados
  function loadChart(canvasId, type, params, optionsExtra) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var url = canvas.getAttribute("data-url");
    setState(canvas, "loading");
    fetchJSON(url, params)
      .then(function (payload) {
        renderChart(canvasId, type, payload, optionsExtra);
      })
      .catch(function () {
        setState(canvas, "error");
      });
  }

  applyDefaults();

  window.DashboardCore = {
    palette: PALETTE,
    colorFor: colorFor,
    fetchJSON: fetchJSON,
    renderChart: renderChart,
    loadChart: loadChart,
    setState: setState,
  };
})(window);
