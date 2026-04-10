const isBsModal = (link, bsModal) =>
  bsModal ? `data-form-url='${link}'` : `href='${link}'`;

const optionsColumn = (options = []) => {
  if (!options.length) return "";
  return `<div class="btn-group dropstart">
      <a role="button" class="dropdown-toggle dropdown-toggle--not-icon" type="button" data-bs-toggle="dropdown" aria-expanded="false">
        <span class="material-symbols-outlined">
          more_horiz
        </span>
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

const renderDataTable = ({
  tableID = "#id_table",
  url = "",
  columns = [],
  requestData = {},
  extraConfig = {},
}) => {
  const {
    customStartTop = null,
    columnsDefs = [],
    layout: customLayout = {},
    ajax: customAjax = {},
    language: customLanguage = {},
    ...settings
  } = extraConfig;

  return $(tableID).DataTable({
    ajax: {
      url,
      type: "GET",
      data: (data) => ({ ...data, ...requestData }),
      error: (xhr, status, error) => {
        notifyAlert(xhr.responseJSON, xhr.status, 4000);
      },
      ...customAjax,
    },
    language: {
      ...DATATABLES_LANGUAGE,
      info: "Total resultado: _TOTAL_",
      infoEmpty: "Total resultado: 0",
      ...customLanguage,
    },
    layout: {
      topStart: customStartTop,
      topEnd: "search",
      bottomStart: "info",
      bottomEnd: "paging",
      ...customLayout,
    },
    paging: true,
    pageLength: 10,
    searching: true,
    lengthChange: false,
    info: true,
    processing: true,
    serverSide: true,
    stateSave: false,
    order: [[0, "asc"]],
    responsive: true,
    scrollX: false,
    fixedColumns: null,
    scrollCollapse: false,
    columns,
    columnsDefs: [
      { targets: [0, -1], orderable: false, responsivePriority: 1 },
      ...columnsDefs,
    ],
    ...settings,
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
