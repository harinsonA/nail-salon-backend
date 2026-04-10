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
