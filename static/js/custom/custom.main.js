const isBsModal = (link, bsModal) =>
  bsModal ? `data-form-url='${link}'` : `href='${link}'`;

const optionsColumn = (options = []) => {
  if (!options.length) return "";
  return `<div class="btn-group dropstart">
      <a role="button" class="dropdown-toggle dropdown-toggle--not-icon" type="button" data-bs-toggle="dropdown" aria-expanded="false">
        <img src="/static/images/tables/options.svg" alt="Opciones" width="24" height="24">
      </a>
      <ul class="dropdown-menu">
        ${options
          .map(
            ({
              label = "Acción",
              link = "#",
              className = "",
              bsModal = false,
              icon = "",
              attrs = "",
            }) =>
              `<li><a class="dropdown-item dropdown-item--custom ${className}" ${isBsModal(
                link,
                bsModal,
              )} ${attrs}>${
                icon
                  ? `<span class="material-symbols-outlined">${icon}</span>`
                  : ""
              } ${label}</a></li>`,
          )
          .join("")}  
      </ul>
    </div>`;
};

const emptyStateTemplate = (
  image = "/static/images/icons/icono-1.png",
  message = "Sin registros para esta sección",
) => `
  <div class="dt-empty-state">
    <img class="dt-empty-state__img" src="${image}" alt="">
    <b class="dt-empty-state__text">${message}</b>
  </div>`;

// Loader "gooey" del indicador de carga (processing) de las tablas.
// El marcado vive aquí; los colores/animación se definen en
// custom.datatables.css (sección 7) usando la paleta global.
const LOADER_HALVAN_PATH =
  "m 164,100 c 0,-35.346224 -28.65378,-64 -64,-64 -35.346224,0 -64,28.653776 -64,64 0,35.34622 28.653776,64 64,64 35.34622,0 64,-26.21502 64,-64 0,-37.784981 -26.92058,-64 -64,-64 -37.079421,0 -65.267479,26.922736 -64,64 1.267479,37.07726 26.703171,65.05317 64,64 37.29683,-1.05317 64,-64 64,-64";

const processingLoaderTemplate = (message = "Procesando…") => `
  <div class="dt-loader" role="status" aria-label="${message}">
    <svg class="dt-loader__gegga" aria-hidden="true">
      <defs>
        <filter id="dtLoaderGoo">
          <feGaussianBlur in="SourceGraphic" stdDeviation="7" result="blur" />
          <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 20 -10" result="inreGegga" />
          <feComposite in="SourceGraphic" in2="inreGegga" operator="atop" />
        </filter>
      </defs>
    </svg>
    <svg class="dt-loader__snurra" viewBox="0 0 200 200" aria-hidden="true">
      <defs>
        <linearGradient id="dtLoaderGradientStops">
          <stop class="dt-loader__stop1" offset="0" />
          <stop class="dt-loader__stop2" offset="1" />
        </linearGradient>
        <linearGradient y2="160" x2="160" y1="40" x1="40" gradientUnits="userSpaceOnUse" id="dtLoaderGradient" href="#dtLoaderGradientStops" />
      </defs>
      <path class="halvan" d="${LOADER_HALVAN_PATH}" />
      <circle class="strecken" cx="100" cy="100" r="64" />
    </svg>
    <svg class="dt-loader__skugga" viewBox="0 0 200 200" aria-hidden="true">
      <path class="halvan" d="${LOADER_HALVAN_PATH}" />
      <circle class="strecken" cx="100" cy="100" r="64" />
    </svg>
    <span class="visually-hidden">${message}</span>
  </div>`;

const renderDataTable = ({
  tableID = "#id_table",
  url = "",
  columns = [],
  requestData = {},
  extraConfig = {},
}) => {
  const {
    columnsDefs = [],
    exportConfig = null,
    layout: customLayout = {},
    ajax: customAjax = {},
    language: customLanguage = {},
    ...settings
  } = extraConfig;

  const { topStart: customTopStart = null, ...restLayout } = customLayout;
  const exportNode = exportConfig ? buildExportButtonNode(exportConfig) : null;

  // Sin `url` => modo data LOCAL: la tabla lee el DOM (sin ajax ni serverSide).
  // Con `url` => comportamiento de siempre (serverSide por ajax).
  const isLocal = !url;

  const config = {
    language: {
      ...DATATABLES_LANGUAGE,
      info: "Total resultado: _TOTAL_",
      infoEmpty: "Total resultado: 0",
      infoFiltered: "",
      search: "",
      searchPlaceholder: "Buscar",
      processing: processingLoaderTemplate(),
      loadingRecords: "",
      emptyTable: emptyStateTemplate(),
      zeroRecords: emptyStateTemplate(
        "/static/images/tables/empty-1.png",
        "Sin resultados encontrados",
      ),
      ...customLanguage,
    },
    layout: {
      topStart: combineTopStart(customTopStart, exportNode),
      topEnd: "search",
      bottomStart: "info",
      bottomEnd: "paging",
      ...restLayout,
    },
    paging: true,
    pagingType: "simple_numbers",
    pageLength: 10,
    searching: true,
    lengthChange: false,
    info: true,
    processing: true,
    serverSide: !isLocal,
    stateSave: false,
    order: [[0, "asc"]],
    responsive: true,
    scrollX: false,
    fixedColumns: null,
    scrollCollapse: false,
    columnsDefs: [
      { targets: [0, -1], orderable: false, responsivePriority: 1 },
      ...columnsDefs,
    ],
    ...settings,
  };

  // En modo servidor: ajax. En modo local: se omite (usa el DOM).
  if (!isLocal) {
    config.ajax = {
      url,
      type: "GET",
      data: (data) => ({ ...data, ...requestData }),
      error: (xhr, status, error) => {
        notifyAlert(xhr.responseJSON, xhr.status, 4000);
      },
      ...customAjax,
    };
  }

  // `columns` solo si se proveen; en modo local se infieren del DOM.
  if (columns.length) {
    config.columns = columns;
  }

  return $(tableID).DataTable(config);
};

// id por defecto compartido entre el constructor del botón y el bindeo
const DEFAULT_EXPORT_BTN_ID = "export-btn";

// Si ya hay un topStart, ANEXA el botón (DataTables 2 admite un array en la celda); si no, va solo
const combineTopStart = (existing, node) => {
  if (!node) return existing;
  if (!existing) return node;
  return Array.isArray(existing) ? [...existing, node] : [existing, node];
};

// La url va en data-url (no usamos href); el icono es un recurso del sistema
const buildExportButtonNode = ({
  id = DEFAULT_EXPORT_BTN_ID,
  url = "",
  label = "Exportar",
}) =>
  $(`<a id="${id}" role="button" data-url="${url}"
        class="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-2">
        ${label}
        <img src="/static/images/common/download.svg" alt="Descargar" width="16" height="16">
      </a>`)[0];

// Arma los parámetros que necesita la URL de descarga (lee el DOM en el momento del click)
const buildExportParams = ({ form = null, fields = [], searchValue = "" } = {}) => {
  const params = new URLSearchParams();

  if (form) {
    const formEl = typeof form === "string" ? document.querySelector(form) : form;
    if (formEl) new FormData(formEl).forEach((value, key) => params.set(key, value));
  }

  fields.forEach((selector) => {
    const el = document.querySelector(selector);
    if (el) params.set(el.name || el.id, el.value); // usa el name -> coincide con el filter form del backend
  });

  if (searchValue) params.set("search[value]", searchValue); // misma clave que get_filter_by_search
  return params;
};

// Enlaza el botón (se invoca desde el initComplete de la vista). La url sale del data-url del botón.
const bindExportButton = ({
  buttonID = `#${DEFAULT_EXPORT_BTN_ID}`,
  form = null,
  fields = [],
  getSearchValue = null,
} = {}) => {
  const button = document.querySelector(buttonID);
  if (!button) return;
  button.addEventListener("click", (event) => {
    event.preventDefault();
    const params = buildExportParams({
      form,
      fields,
      searchValue: getSearchValue?.() ?? "",
    });
    window.location = `${button.dataset.url}?${params.toString()}`; // data-url, no href
  });
};

const getCSRFToken = () =>
  document.querySelector('input[name="csrfmiddlewaretoken"]').value;

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const ajaxSubmitForm = async (url, data = {}, method = "POST") => {
  return new Promise((resolve, reject) => {
    $.ajax({
      url,
      method,
      dataType: "json",
      headers: { "X-CSRFToken": getCSRFToken() },
      data: { ...data },
      success: (data) => {
        return resolve([data, 200]);
      },
      error: (xhr, status, error) => {
        return reject([xhr.responseJSON, xhr.status]);
      },
    });
  });
};

const getResponseToRequest = async (url, data, method = "POST") => {
  try {
    const response = await ajaxSubmitForm(url, data, method);
    return response;
  } catch (error) {
    return error;
  }
};

const getMessageOr500 = (response, statusCode) => {
  return statusCode < 500
    ? response.message
    : "Error 500: Hubo un problema inesperado, vuelva intentar en unos minutos.";
};

const notifyAlert = (
  response = "",
  statusCode = 200,
  duration = 3200,
  config = {},
) => {
  const text = getMessageOr500(response, statusCode);
  if (!text) return;

  const background = [200].includes(statusCode)
    ? "linear-gradient(to top, #56ab2f, #a8e063)"
    : "linear-gradient(to top, #f00000, #dc281e)";
  Toastify({
    text: text,
    duration,
    gravity: "bottom",
    position: "center",
    className: "notify-alert",
    style: {
      minWidth: "250px",
      textAlign: "center",
      background: background,
    },
    ...config,
  }).showToast();
};

function wrapText(text, maxCharacters = 23) {
  return text && window.innerWidth < 700
    ? text.slice(0, maxCharacters) + "..."
    : text;
}

const wrapTextColumns = (text, maxCharacters = 17) => {
  return wrapText(text, maxCharacters);
};

const initTooltips = (selector = '[data-bs-toggle="tooltip"]') => {
  $(selector).tooltip();
};
