/* ==========================================================================
   DASHBOARD FILTERS — filtro global de período (presets + rango personalizado)
   --------------------------------------------------------------------------
   Única fuente de verdad: el querystring de la URL. Al cambiar el filtro:
   actualiza la URL (replaceState), refresca el label de cada card y llama a
   DashboardCore.reloadAll(params).

   El "kind" identifica el preset activo (months / year / custom) y se guarda
   en la URL para poder restaurar el label exacto al recargar (p. ej. "Este
   año" vs. "Personalizado", que comparten params de rango).
   Se carga DESPUÉS de los chart.*.js (que ya se registraron en el core).
   ========================================================================== */
(function (window) {
  "use strict";

  var DEFAULT_MONTHS = 6;

  function pad(n) {
    return n < 10 ? "0" + n : "" + n;
  }

  // Date -> "dd/mm/aaaa" (formato del bootstrap-datepicker del proyecto)
  function formatDate(d) {
    return pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear();
  }

  function monthsLabel(n) {
    return "Últimos " + n + " meses";
  }

  // ---- Constructores de estado -------------------------------------------
  // Un estado = { kind, params, label }

  function monthsState(n) {
    return { kind: "months", params: { months: n }, label: monthsLabel(n) };
  }

  function yearState() {
    var now = new Date();
    return {
      kind: "year",
      params: {
        date_from: formatDate(new Date(now.getFullYear(), 0, 1)),
        date_to: formatDate(now),
      },
      label: "Este año",
    };
  }

  function customState(from, to) {
    return {
      kind: "custom",
      params: { date_from: from, date_to: to },
      label: "Personalizado",
    };
  }

  // ---- URL <-> estado -----------------------------------------------------

  function readState() {
    var qs = new URLSearchParams(window.location.search);
    var from = qs.get("date_from");
    var to = qs.get("date_to");
    if (from && to) {
      if (qs.get("preset") === "year") {
        return { kind: "year", params: { date_from: from, date_to: to }, label: "Este año" };
      }
      return customState(from, to);
    }
    var months = parseInt(qs.get("months"), 10);
    if (months) return monthsState(months);
    return monthsState(DEFAULT_MONTHS);
  }

  function writeState(state) {
    var qs = new URLSearchParams();
    if (state.params.date_from && state.params.date_to) {
      qs.set("date_from", state.params.date_from);
      qs.set("date_to", state.params.date_to);
      if (state.kind === "year") qs.set("preset", "year");
    } else if (state.params.months) {
      qs.set("months", state.params.months);
    }
    window.history.replaceState(
      null,
      "",
      window.location.pathname + "?" + qs.toString()
    );
  }

  // ---- UI -----------------------------------------------------------------

  function updateLabels(text) {
    document.querySelectorAll("[data-period-label]").forEach(function (el) {
      el.textContent = text;
    });
  }

  function highlight(root, state) {
    root.querySelectorAll(".dashboard-filters__presets .btn").forEach(function (b) {
      b.classList.remove("active");
    });
    var selector = null;
    if (state.kind === "months") selector = '[data-months="' + state.params.months + '"]';
    else if (state.kind === "year") selector = '[data-preset="year"]';
    else if (state.kind === "custom") selector = '[data-preset="custom"]';
    var btn = selector && root.querySelector(selector);
    if (btn) btn.classList.add("active");
  }

  function apply(root, state) {
    highlight(root, state);
    updateLabels(state.label);
    writeState(state);
    DashboardCore.reloadAll(state.params);
  }

  function init() {
    var current = readState();
    var root = document.querySelector("[data-dashboard-filters]");

    // Sin barra de filtros: cargar y etiquetar según la URL.
    if (!root) {
      updateLabels(current.label);
      DashboardCore.reloadAll(current.params);
      return;
    }

    var rangeBox = root.querySelector("[data-filter-range]");

    // Presets de meses (3 / 6 / 12 …)
    root.querySelectorAll("[data-months]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (rangeBox) rangeBox.classList.add("d-none");
        apply(root, monthsState(parseInt(btn.getAttribute("data-months"), 10)));
      });
    });

    // "Este año"
    var yearBtn = root.querySelector('[data-preset="year"]');
    if (yearBtn) {
      yearBtn.addEventListener("click", function () {
        if (rangeBox) rangeBox.classList.add("d-none");
        apply(root, yearState());
      });
    }

    // "Personalizado" -> muestra/oculta los datepickers
    var customBtn = root.querySelector('[data-preset="custom"]');
    if (customBtn && rangeBox) {
      customBtn.addEventListener("click", function () {
        rangeBox.classList.toggle("d-none");
      });
    }

    // Inicializa los datepickers del rango (reusa el helper del proyecto).
    // initializeDatePickers se declara con `const` en custom.datepicker.js, así
    // que es un global léxico (no window.*); se referencia por nombre.
    if (typeof initializeDatePickers === "function") {
      initializeDatePickers({ selector: "[data-filter-range] .datepicker" });
    }

    // Aplica el rango personalizado
    var applyBtn = root.querySelector("[data-apply-range]");
    if (applyBtn) {
      applyBtn.addEventListener("click", function () {
        var from = root.querySelector("[data-from]").value;
        var to = root.querySelector("[data-to]").value;
        if (!from || !to) return;
        apply(root, customState(from, to));
      });
    }

    // Estado inicial: refleja la URL, etiqueta y dispara la primera carga
    highlight(root, current);
    updateLabels(current.label);
    DashboardCore.reloadAll(current.params);
  }

  $(function () {
    init();
  });

  window.DashboardFilters = { init: init };
})(window);
