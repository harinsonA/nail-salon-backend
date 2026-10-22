(function (window, $) {
  "use strict";

  const PANEL_CLASS = "cal2-detail";

  const initAppointmentPanel = (form) => {
    const modal = $(form).closest(".modal");
    modal.addClass(PANEL_CLASS);
    modal.one("hidden.bs.modal", () => {
      modal.removeClass(PANEL_CLASS);
      modal.find(".modal-content").empty();
    });

    const confirm = form.querySelector("[data-panel-confirm]");
    if (!confirm) {
      return;
    }
    confirm.addEventListener("click", async () => {
      confirm.disabled = true;
      const data = Object.fromEntries(new FormData(form).entries());
      const [response = {}, status] = await getResponseToRequest(form.action, data);
      if (status === 401 && typeof redirectToLogin === "function") {
        redirectToLogin(response.redirect);
        return;
      }
      notifyAlert(response, status);
      if (status === 200) {
        modal.modal("hide");
        document.dispatchEvent(new CustomEvent(window.APPOINTMENT_CHANGED_EVENT));
        return;
      }
      confirm.disabled = false;
    });
  };

  window.initAppointmentPanel = initAppointmentPanel;
})(window, jQuery);
