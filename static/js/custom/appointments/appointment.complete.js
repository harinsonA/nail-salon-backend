(function (window, $) {
  "use strict";

  const CASH = "EFECTIVO";
  const NOTES_MAX = 250;
  const DIALOG_CLASSES = "modal-lg modal-dialog-scrollable";

  const fmtMoney = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
  const money = (value) => fmtMoney.format(value);

  class AppointmentComplete {
    constructor(form, { total }) {
      this.form = form;
      this.total = total;
      this.modal = $(form).closest(".modal");

      const find = (name) => form.querySelector(`[data-${name}]`);
      this.fields = {
        full: form.querySelector("#id_full_payment"),
        amount: form.querySelector("#id_down_payment"),
        method: form.querySelector("#id_payment_method"),
        notes: form.querySelector("#id_observations"),
      };
      this.ui = {
        partial: find("partial"),
        methodCard: find("method-card"),
        referenceWrap: find("reference"),
        notesStep: find("notes-step"),
        notesCount: find("notes-count"),
        amountError: form.querySelector(".id_down_payment"),
        bar: find("bar"),
        now: find("now"),
        after: find("after"),
        save: find("save"),
      };

      this.prepareModal();
      this.bind();
      this.updateNotesCounter();
      this.render();
    }

    prepareModal() {
      const dialog = this.modal.find(".modal-dialog");
      dialog.addClass(DIALOG_CLASSES);
      this.modal.one("hidden.bs.modal", () => {
        dialog.removeClass(DIALOG_CLASSES);
        this.modal.find(".modal-content").empty();
      });
    }

    amount() {
      if (this.fields.full.checked) {
        return this.total;
      }
      return Math.max(0, parseInt(this.fields.amount.value, 10) || 0);
    }

    amountError() {
      if (this.fields.full.checked) {
        return "";
      }
      const raw = this.fields.amount.value;
      if (raw !== "" && Number(raw) < 0) {
        return "El monto no puede ser negativo.";
      }
      if (this.amount() >= this.total) {
        return `Si paga ${money(this.total)} o más, activa "Paga el total ahora".`;
      }
      return "";
    }

    render() {
      const { fields, ui } = this;
      const full = fields.full.checked;
      ui.partial.hidden = full;
      const error = this.amountError();
      ui.amountError.textContent = error;
      fields.amount.classList.toggle("is-invalid", Boolean(error));

      const amount = this.amount();
      const paying = amount > 0;
      ui.methodCard.hidden = !paying;
      ui.notesStep.textContent = paying ? "3" : "2";
      ui.referenceWrap.hidden = !paying || fields.method.value === CASH;

      const counted = error ? 0 : amount;
      const debt = this.total - counted;
      ui.now.textContent = money(counted);
      ui.after.textContent = debt === 0 ? "Nada" : money(debt);
      ui.after.classList.toggle("has-debt", debt > 0);
      ui.bar.style.width = `${this.total ? (counted / this.total) * 100 : 0}%`;

      ui.save.disabled = Boolean(error);
    }

    updateNotesCounter() {
      const length = this.fields.notes.value.length;
      this.ui.notesCount.textContent = `${length}/${NOTES_MAX} caracteres`;
      this.ui.notesCount.classList.toggle("is-near", length >= NOTES_MAX - 20);
    }

    async save() {
      this.ui.save.disabled = true;
      const [, status] = await submitRequestBSModal(this.form);
      if (status === 200) {
        this.modal.modal("hide");
        document.dispatchEvent(new CustomEvent(window.APPOINTMENT_CHANGED_EVENT));
        return;
      }
      this.render();
    }

    bind() {
      const { fields, ui } = this;
      fields.full.addEventListener("change", () => this.render());
      fields.method.addEventListener("change", () => this.render());
      fields.amount.addEventListener("input", () => this.render());
      fields.notes.addEventListener("input", () => this.updateNotesCounter());
      ui.save.addEventListener("click", () => this.save());
    }
  }

  window.initAppointmentComplete = (form, config) => new AppointmentComplete(form, config);
})(window, jQuery);
