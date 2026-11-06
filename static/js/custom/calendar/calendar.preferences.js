(function (window, $) {
  "use strict";

  const HiCalendar = (window.HiCalendar = window.HiCalendar || {});

  const CHANGED_EVENT = "calendar:preferences";
  const MODAL_CLASS = "calendar-config";

  const prepareModal = (form) => {
    const modal = $(form).closest(".modal");
    const help = form.querySelector(".calendar-settings__help");
    const tooltip = help && window.bootstrap ? new window.bootstrap.Tooltip(help, { container: "body" }) : null;
    modal.addClass(MODAL_CLASS);
    modal.one("hidden.bs.modal", () => {
      if (tooltip) {
        tooltip.dispose();
      }
      modal.removeClass(MODAL_CLASS);
      modal.find(".modal-content").empty();
    });
    return modal;
  };

  const initCalendarPreferences = (form) => {
    prepareModal(form);

    const save = async () => {
      const data = Object.fromEntries(new FormData(form).entries());
      const [response = {}, status] = await getResponseToRequest(form.action, data);
      if (status === 401 && typeof redirectToLogin === "function") {
        redirectToLogin(response.redirect);
        return;
      }
      if (status !== 200) {
        notifyAlert(response, status);
        return;
      }
      document.dispatchEvent(new CustomEvent(CHANGED_EVENT, { detail: response.settings }));
    };

    form.querySelectorAll("input").forEach((input) => input.addEventListener("change", save));
  };

  const initAppointmentPreferences = (form) => {
    const modal = prepareModal(form);
    const enabled = form.querySelector("[data-reservation-enabled] input");
    const details = form.querySelector("[data-reservation-details]");

    enabled.addEventListener("change", () => {
      details.hidden = !enabled.checked;
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      const [, status] = await submitRequestBSModal(form);
      if (status === 200) {
        modal.modal("hide");
      }
    });
  };

  HiCalendar.PREFERENCES_EVENT = CHANGED_EVENT;
  window.initCalendarPreferences = initCalendarPreferences;
  window.initAppointmentPreferences = initAppointmentPreferences;
})(window, jQuery);
