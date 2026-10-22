/**
 * Custom BS Modal Components
 * Funciones específicas para manejo de Bootstrap Modal Forms
 * Depende de: custom.main.js (utilidades AJAX y notificaciones)
 */

const BASE_BS_MODAL = {
  modalID: "#modal",
  modalContent: ".modal-content",
  modalForm: ".modal-content form",
  formURL: null,
  isDeleteForm: false,
  errorClass: "is-invalid",
  asyncUpdate: false,
  asyncSettings: {
    closeOnSubmit: false,
    successMessage: null,
    dataUrl: null,
    dataElementId: null,
    dataKey: null,
    addModalFormFunction: null,
  },
};

const initializeAllBSModals = (settings = {}) => {
  const { elementIDs = ".bs-modal", ...options } = settings;
  $(elementIDs).each(function () {
    const base_config = {
      ...BASE_BS_MODAL,
      formURL: $(this).data("form-url"),
    };
    $(this).modalForm({
      ...base_config,
      ...options,
    });
  });
};

const initializeBSModals = (elementID = ".bs-modal", settings = {}) => {
  const base_config = {
    ...BASE_BS_MODAL,
    formURL: $(elementID).data("form-url"),
  };
  $(elementID).modalForm({
    ...base_config,
    ...settings,
  });
};

const initializeAllBSXLModals = (settings = {}) => {
  const { elementIDs = ".bs-xl-modal", ...options } = settings;
  $(elementIDs).each(function () {
    const base_config = {
      ...BASE_BS_MODAL,
      modalID: "#xl_modal",
      modalContent: ".modal-content",
      modalForm: ".modal-content form",
      formURL: $(this).data("form-url"),
    };
    $(this).modalForm({
      ...base_config,
      ...options,
    });
  });
};

const initializeBSXLModals = (elementID = ".bs-xl-modal", settings = {}) => {
  const base_config = {
    ...BASE_BS_MODAL,
    modalID: "#xl_modal",
    modalContent: ".modal-content",
    modalForm: ".modal-content form",
    formURL: $(elementID).data("form-url"),
  };
  $(elementID).modalForm({
    ...base_config,
    ...settings,
  });
};

const initializeCanvasBSModals = (
  elementID = ".canvas-modal",
  settings = {},
) => {
  const base_config = {
    ...BASE_BS_MODAL,
    modalID: "#canvasModal",
    modalContent: ".modal-content",
    modalForm: ".modal-content form",
    formURL: $(elementID).data("form-url"),
  };
  $(elementID).modalForm({
    ...base_config,
    ...settings,
  });
};

const initializeAllCanvasBSModals = (
  elementIDs = ".canvas-modal",
  settings = {},
) => {
  $(elementIDs).each(function () {
    const base_config = {
      ...BASE_BS_MODAL,
      modalID: "#canvasModal",
      modalContent: ".modal-content",
      modalForm: ".modal-content form",
      formURL: $(this).data("form-url"),
    };
    $(this).modalForm({
      ...base_config,
      ...settings,
    });
  });
};

const openBSModal = (url, { modalID = "#modal" } = {}) => {
  $(modalID)
    .find(".modal-content")
    .load(url, (response, status, xhr) => {
      if (status === "error") {
        if (xhr.status === 401 && typeof redirectToLogin === "function") {
          redirectToLogin(xhr.responseJSON?.redirect);
          return;
        }
        notifyAlert({ message: "No se pudo abrir el formulario." }, xhr.status || 500);
        return;
      }
      $(modalID).modal("show");
    });
};

const showErrorsInBSModal = (form, errors) => {
  errors.forEach(({ id_element, error }) => {
    const element = form.querySelector(`#${id_element}`);
    const fieldError = form.querySelector(`.${id_element}`);
    element.classList.add("is-invalid");
    fieldError.textContent = error;
  });
};

const showOkInBSModal = (form) => {
  const elements = form.querySelectorAll(".is-invalid");
  const fieldErrors = form.querySelectorAll(".field_errors");
  elements.forEach((element) => {
    element.classList.remove("is-invalid");
    element.classList.add("is-valid");
  });
  fieldErrors.forEach((element) => {
    element.textContent = "";
  });
};

const showTabsWithErrors = (form) => {
  let firstTab = null;
  form.querySelectorAll('[data-bs-toggle="pill"]').forEach((tab) => {
    const pane = form.querySelector(tab.dataset.bsTarget);
    const hasErrors = Boolean(pane && pane.querySelector(".is-invalid"));
    tab.classList.toggle("has-errors", hasErrors);
    if (hasErrors && !firstTab) {
      firstTab = tab;
    }
  });
  if (firstTab) {
    bootstrap.Tab.getOrCreateInstance(firstTab).show();
  }
};

const submitSerializedBSModal = (form) =>
  new Promise((resolve) => {
    $.ajax({
      url: form.action,
      method: "POST",
      dataType: "json",
      headers: { "X-CSRFToken": getCSRFToken() },
      data: $(form).serialize(),
      success: (data) => resolve([data, 200]),
      error: (xhr) => resolve([xhr.responseJSON, xhr.status]),
    });
  });

const submitRequestBSModal = async (form, settings = {}) => {
  const { extraData = null, reload = false, callBack = null } = settings;
  const formData = new FormData(form);
  const url = form.action;
  const data = Object.fromEntries(formData.entries());
  if (extraData) {
    Object.keys(extraData).forEach((key) => {
      data[key] = extraData[key];
    });
    console.log("Data with extraData:", data);
  }
  const [response, statusCode] = await getResponseToRequest(url, data);
  if ([500].includes(statusCode)) {
    notifyAlert(response, statusCode);
    if (callBack) {
      return callBack(form, response, statusCode);
    }
    return [response, statusCode];
  }

  showOkInBSModal(form);
  notifyAlert(response, statusCode);
  if ([400].includes(statusCode)) {
    showErrorsInBSModal(form, response?.errors || []);
    if (callBack) {
      return callBack(form, response, statusCode);
    }
    return [response, statusCode];
  }
  const isOK = [200].includes(statusCode);
  if (isOK) {
    if (callBack) {
      return callBack(form, response, statusCode);
    }
    if (reload) {
      location.reload();
    }
    return [response, statusCode];
  }
  return [response, statusCode];
};

const submitProfileModalForm = (target) => {
  const buttonSubmit = target.querySelector("#profile_submit_btn");
  $(buttonSubmit).click(async () => {
    const form = target.querySelector("form");
    const [response, statusCode] = await submitRequestBSModal(form);
    if ([200].includes(statusCode)) {
      $(target).modal("hide");
    }
  });
};

const initializeActionModal = (modalID, { onDone = () => {} } = {}) => {
  $(modalID).on("show.bs.modal", ({ target }) => {
    const form = target.querySelector("form[data-action-modal]");
    const submitBtn = form?.querySelector(".action-modal__submit");
    if (!submitBtn) return;
    const result = form.querySelector(".action-modal__result");

    $(submitBtn).click(async () => {
      submitBtn.disabled = true;
      const [response, statusCode] = await submitRequestBSModal(form);
      if (statusCode !== 200) {
        submitBtn.disabled = false;
        return;
      }
      $(modalID).data("actionDone", true);
      if (!result) {
        $(modalID).modal("hide");
        return;
      }
      form.querySelector(".action-modal__request")?.classList.add("d-none");
      form.querySelectorAll("input[type=checkbox]").forEach((input) => {
        input.disabled = true;
      });
      result.querySelectorAll("[data-result]").forEach((node) => {
        node.textContent = response[node.dataset.result] ?? "";
      });
      result.classList.remove("d-none");
      submitBtn.remove();
      const closeBtn = form.querySelector(".action-modal__close");
      closeBtn.textContent = "Cerrar";
      closeBtn.classList.replace("btn-secondary", "btn-primary");
      closeBtn.classList.remove("me-2");
      closeBtn.focus();
    });

  });

  $(modalID).on("hidden.bs.modal", ({ target }) => {
    if (target.querySelector("form[data-sensitive]")) {
      target.querySelector(".modal-content").innerHTML = "";
    }
    if ($(modalID).data("actionDone")) {
      $(modalID).data("actionDone", false);
      onDone();
    }
  });
};

$(document).on("click", ".copy-button", async function () {
  const icon = this.querySelector(".material-symbols-outlined");
  const source = this.parentElement.querySelector("[data-copy-value]");
  try {
    await navigator.clipboard.writeText(source.textContent.trim());
    icon.textContent = "check";
    setTimeout(() => {
      icon.textContent = "content_copy";
    }, 1500);
  } catch {
    notifyAlert({ message: "No se pudo copiar: selecciónalo y cópialo a mano." }, 400);
  }
});
