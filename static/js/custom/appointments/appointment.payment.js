(function (window, $) {
  "use strict";

  $(() => {
    $("#modal").on("show.bs.modal", function ({ currentTarget }) {
      $("#add_payment_btn").off("click").on("click", async () => {
        const form = $(currentTarget).find("form");
        const [, status] = await submitRequestBSModal(form[0]);
        if (status === 200) {
          $(currentTarget).modal("hide");
          document.dispatchEvent(new CustomEvent(window.APPOINTMENT_CHANGED_EVENT));
        }
      });
    });
  });
})(window, jQuery);
