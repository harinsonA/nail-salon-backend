(function (window, $) {
  "use strict";

  const PANEL_CLASS = "calendar-detail";

  const fmtMoney = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
  const money = (value) => fmtMoney.format(value);

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  };

  const field = (labelText, control) => {
    const label = el("label", "calendar-new__field");
    label.append(el("span", "", labelText), control);
    return label;
  };

  const initCancelAdvances = (form) => {
    const configNode = form.querySelector("#cancel-advances-config");
    if (!configNode) {
      return;
    }
    const config = JSON.parse(configNode.textContent);
    const find = (name) => form.querySelector(`[data-cancel-${name}]`);
    const ui = { list: find("list"), retained: find("retained"), refunded: find("refunded"), field: find("refunds") };
    const rows = config.rows.map((row) => ({
      ...row,
      refund: false,
      refundMethod: row.method === config.transfer ? config.transfer : config.cash,
      reference: "",
    }));

    const serialize = () => {
      ui.field.value = JSON.stringify(
        rows
          .filter((row) => row.refund)
          .map((row) => ({
            id: row.id,
            metodo: row.refundMethod,
            referencia: row.refundMethod === config.cash ? "" : row.reference.trim(),
          })),
      );
      const refunded = rows.filter((row) => row.refund).reduce((sum, row) => sum + row.amount, 0);
      const total = rows.reduce((sum, row) => sum + row.amount, 0);
      ui.refunded.textContent = money(refunded);
      ui.retained.textContent = money(total - refunded);
    };

    const rowElement = (row) => {
      const wrapper = el("div", `calendar-cancel__row${row.refund ? " is-refund" : ""}`);
      const head = el("div", "calendar-cancel__head");
      head.append(el("span", "", `${row.methodLabel} - ${row.date}`), el("strong", "", money(row.amount)));

      const note = el(
        "p",
        `calendar-cancel__note${row.refund ? " is-refund" : ""}`,
        row.refund ? "Se le reembolsa a la clienta." : "El negocio se queda con este dinero.",
      );

      const toggle = el("label", "form-check form-switch calendar-pay__full calendar-cancel__toggle");
      const input = el("input", "form-check-input");
      input.type = "checkbox";
      input.setAttribute("role", "switch");
      input.checked = row.refund;
      input.addEventListener("change", () => {
        row.refund = input.checked;
        render();
      });
      toggle.append(input, el("span", "", "Reembolsar"));

      const refund = el("div", "calendar-cancel__refund");
      refund.hidden = !row.refund;
      const method = el("select", "form-select form-select--custom");
      config.refundMethods.forEach(([value, label]) => {
        const option = el("option", "", label);
        option.value = value;
        option.selected = value === row.refundMethod;
        method.append(option);
      });
      const reference = el("input", "form-control form-control--custom");
      reference.type = "text";
      reference.maxLength = config.referenceMaxLength;
      reference.value = row.reference;
      reference.addEventListener("input", () => {
        row.reference = reference.value;
        serialize();
      });
      const referenceField = field("Referencia (opcional)", reference);
      referenceField.classList.add("calendar-cancel__reference");
      referenceField.hidden = row.refundMethod === config.cash;
      method.addEventListener("change", () => {
        row.refundMethod = method.value;
        referenceField.hidden = row.refundMethod === config.cash;
        serialize();
      });
      refund.append(field("Reembolsar por *", method), referenceField);

      wrapper.append(head, note, toggle, refund);
      return wrapper;
    };

    const render = () => {
      ui.list.replaceChildren(...rows.map(rowElement));
      serialize();
    };

    render();
  };

  const initRestoreAdvances = (form) => {
    const configNode = form.querySelector("#restore-advances-config");
    if (!configNode) {
      return;
    }
    const config = JSON.parse(configNode.textContent);
    const find = (name) => form.querySelector(`[data-restore-${name}]`);
    const ui = {
      list: find("list"),
      services: find("services"),
      backRow: find("back-row"),
      back: find("back"),
      keptRow: find("kept-row"),
      kept: find("kept"),
      remaining: find("remaining"),
      field: find("restored"),
    };
    const rows = config.rows.map((row) => ({ ...row, restore: false }));

    const serialize = () => {
      ui.field.value = JSON.stringify(rows.filter((row) => row.restore).map((row) => row.id));
      const back = rows.filter((row) => row.restore).reduce((sum, row) => sum + row.amount, 0);
      const kept = rows.reduce((sum, row) => sum + row.amount, 0) - back;
      ui.services.textContent = money(config.servicesTotal);
      ui.backRow.hidden = !back;
      ui.back.textContent = `-${money(back)}`;
      ui.keptRow.hidden = !kept;
      ui.kept.textContent = money(kept);
      ui.remaining.textContent = money(Math.max(0, config.servicesTotal - config.prepaid - back));
    };

    const rowElement = (row) => {
      const wrapper = el("div", `calendar-cancel__row calendar-restore__row${row.restore ? "" : " is-kept"}`);
      const head = el("div", "calendar-cancel__head");
      head.append(el("span", "", `${row.methodLabel} - ${row.date}`), el("strong", "", money(row.amount)));

      const note = el(
        "p",
        `calendar-restore__note${row.restore ? "" : " is-kept"}`,
        row.restore ? "Se descuenta al completar la cita." : "El negocio se queda con este dinero.",
      );

      const toggle = el("label", "form-check form-switch calendar-pay__full calendar-cancel__toggle");
      const input = el("input", "form-check-input");
      input.type = "checkbox";
      input.setAttribute("role", "switch");
      input.checked = row.restore;
      input.addEventListener("change", () => {
        row.restore = input.checked;
        render();
      });
      toggle.append(input, el("span", "", "Restaurar anticipo"));

      wrapper.append(head, note, toggle);
      return wrapper;
    };

    const render = () => {
      ui.list.replaceChildren(...rows.map(rowElement));
      serialize();
    };

    render();
  };

  const initAppointmentPanel = (form) => {
    const modal = $(form).closest(".modal");
    modal.addClass(PANEL_CLASS);
    modal.one("hidden.bs.modal", () => {
      modal.removeClass(PANEL_CLASS);
      modal.find(".modal-content").empty();
    });

    initCancelAdvances(form);
    initRestoreAdvances(form);

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
