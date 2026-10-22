(function (window, $) {
  "use strict";

  const PANEL_CLASS = "calendar-detail";

  const initAppointmentPanel = (form) => {
    const modal = $(form).closest(".modal");
    modal.addClass(PANEL_CLASS);
    modal.one("hidden.bs.modal", () => {
      modal.removeClass(PANEL_CLASS);
      modal.find(".modal-content").empty();
    });

    const payButton = form.querySelector("[data-panel-payment]");
    if (payButton) {
      payButton.addEventListener("click", () => {
        const url = payButton.dataset.panelPayment;
        modal.one("hidden.bs.modal", () => {
          const trigger = $("<a>").attr("data-form-url", url).appendTo(document.body);
          initializeBSModals(trigger, { formURL: url });
          trigger.trigger("click");
          trigger.remove();
        });
        modal.modal("hide");
      });
    }

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
