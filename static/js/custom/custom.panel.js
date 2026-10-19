$(document).on("click", ".modal .password-toggle", function () {
  const input = this.closest("form").querySelector(this.dataset.target);
  const show = input.type === "password";
  input.type = show ? "text" : "password";
  $(this).find(".eye-open").toggleClass("d-none", show);
  $(this).find(".eye-closed").toggleClass("d-none", !show);
});

$(document).on("change", ".modal #id_is_superuser", ({ target }) => {
  const $form = $(target).closest("form");
  if (target.checked) {
    $form.find("#id_is_staff").prop("checked", true);
  }
  $form.find(".superuser-notice").toggleClass("d-none", !target.checked);
});

const refreshInheritedPermissions = (form) => {
  const mapNode = form.querySelector("#user-group-permissions");
  if (!mapNode) return;
  const groupPermissions = JSON.parse(mapNode.textContent);
  const $groups = $(form).find("#id_groups");
  const inherited = new Set(($groups.val() || []).flatMap((id) => groupPermissions[id] || []));
  const locked = $groups.prop("disabled");
  form.querySelectorAll(".permission-checkbox").forEach((checkbox) => {
    const isInherited = inherited.has(Number(checkbox.value));
    checkbox.checked = isInherited || checkbox.dataset.direct === "1";
    checkbox.disabled = isInherited || locked;
    checkbox.parentElement.querySelector(".inherited-label").classList.toggle("d-none", !isInherited);
  });
};

$(document).on("change", ".modal #id_groups", ({ target }) =>
  refreshInheritedPermissions(target.closest("form"))
);

$(document).on("change", ".modal .permission-checkbox", function () {
  this.dataset.direct = this.checked ? "1" : "0";
});

const initializeUserEditModal = (modalID, { onSaved = () => {} } = {}) => {
  $(modalID).on("show.bs.modal", ({ target }) => {
    const submitBtn = target.querySelector("#user_update_submit_btn");
    if (!submitBtn) return;
    $(submitBtn).click(async () => {
      submitBtn.disabled = true;
      const modalForm = target.querySelector("#user-edit-form-modal");
      const [response, statusCode] = await submitSerializedBSModal(modalForm);
      showOkInBSModal(modalForm);
      if (statusCode === 400) {
        showErrorsInBSModal(modalForm, response?.errors || []);
        showTabsWithErrors(modalForm);
      }
      notifyAlert(response || {}, statusCode);
      if (statusCode === 200) {
        $(modalID).modal("hide");
        onSaved(response);
      }
      submitBtn.disabled = statusCode === 200;
    });
  });
};

const initializeBusinessActionModal = (modalID) => {
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
