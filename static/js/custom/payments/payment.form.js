(function (window, $) {
  "use strict";

  const CASH = "EFECTIVO";
  const NOTES_MAX = 250;
  const DIALOG_CLASSES = "modal-lg modal-dialog-scrollable";

  const fmtMoney = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
  const money = (value) => fmtMoney.format(value);

  class PaymentForm {
    constructor(form, { total, paid, balance }) {
      this.form = form;
      this.total = total;
      this.paid = paid;
      this.balance = balance;
      this.modal = $(form).closest(".modal");

      const find = (name) => form.querySelector(`[data-${name}]`);
      this.fields = {
        full: form.querySelector("#id_full_payment"),
        amount: form.querySelector("#id_down_payment"),
        method: form.querySelector("#id_payment_method"),
        reference: form.querySelector("#id_payment_reference"),
        date: form.querySelector("#id_payment_date"),
        time: form.querySelector("#id_payment_time"),
        notes: form.querySelector("#id_observations"),
      };
      this.ui = {
        amountError: form.querySelector(".id_down_payment"),
        referenceWrap: find("reference"),
        notesCount: find("notes-count"),
        barPaid: find("bar-paid"),
        barNow: find("bar-now"),
        now: find("now"),
        after: find("after"),
        save: form.querySelector("#add_payment_btn"),
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
      return Math.max(0, parseInt(this.fields.amount.value, 10) || 0);
    }

    amountError(amount) {
      if (this.fields.amount.value !== "" && amount <= 0) {
        return "El monto debe ser mayor a $0.";
      }
      if (amount > this.balance) {
        return `No puede superar el saldo pendiente (${money(this.balance)}).`;
      }
      return "";
    }

    render() {
      const { fields, ui } = this;
      const full = fields.full.checked;
      if (full) {
        fields.amount.value = this.balance;
      }
      fields.amount.disabled = full;

      const amount = this.amount();
      const error = this.amountError(amount);
      ui.amountError.textContent = error;
      fields.amount.classList.toggle("is-invalid", Boolean(error));

      const needsReference = fields.method.value !== CASH;
      ui.referenceWrap.hidden = !needsReference;

      const counted = error ? 0 : amount;
      const after = this.balance - counted;
      ui.now.textContent = counted ? money(counted) : "—";
      ui.after.textContent = after === 0 ? "Queda pagada" : money(after);
      ui.after.classList.toggle("is-settled", after === 0);
      ui.barPaid.style.width = `${this.total ? (this.paid / this.total) * 100 : 0}%`;
      ui.barNow.style.width = `${this.total ? (counted / this.total) * 100 : 0}%`;

      const reference = fields.reference.value.trim();
      const ready = counted > 0 && (!needsReference || reference) && fields.date.value && fields.time.value;
      ui.save.disabled = !ready;
    }

    updateNotesCounter() {
      const length = this.fields.notes.value.length;
      this.ui.notesCount.textContent = `${length}/${NOTES_MAX} caracteres`;
      this.ui.notesCount.classList.toggle("is-near", length >= NOTES_MAX - 20);
    }

    bind() {
      const { fields } = this;
      [fields.full, fields.method].forEach((input) => input.addEventListener("change", () => this.render()));
      [fields.amount, fields.reference, fields.date, fields.time].forEach((input) =>
        input.addEventListener("input", () => this.render()),
      );
      fields.notes.addEventListener("input", () => this.updateNotesCounter());
    }
  }

  window.initPaymentForm = (form, config) => new PaymentForm(form, config);
})(window, jQuery);
