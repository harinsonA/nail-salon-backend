(function (window, $) {
  "use strict";

  const HiCalendar = (window.HiCalendar = window.HiCalendar || {});

  const CHANGED_EVENT = "calendar:preferences";
  const MODAL_CLASS = "calendar-config";

  const initCalendarPreferences = (form) => {
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

  HiCalendar.PREFERENCES_EVENT = CHANGED_EVENT;
  window.initCalendarPreferences = initCalendarPreferences;
})(window, jQuery);
