(function (window, $) {
  "use strict";

  const CREATED_EVENT = "appointment:created";
  const CHANGED_EVENT = "appointment:changed";
  const ALL_CATEGORIES = "";
  const NOTES_MAX = 250;
  const REQUIRED = "Este campo es obligatorio.";

  const fmtMonth = new Intl.DateTimeFormat("es-CL", { month: "long" });
  const fmtWeekday = new Intl.DateTimeFormat("es-CL", { weekday: "long" });
  const fmtMoney = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });

  const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);
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

  const icon = (name) => {
    const node = el("span", "material-symbols-outlined icon--small", name);
    node.setAttribute("aria-hidden", "true");
    return node;
  };

  const parseDate = (value) => {
    const [year, month, day] = (value || "").split("-").map(Number);
    return year ? new Date(year, month - 1, day) : null;
  };

  const longDate = (date) =>
    capitalize(`${fmtWeekday.format(date)} ${date.getDate()} ${fmtMonth.format(date)} ${date.getFullYear()}`);

  const parseAmount = (text) => parseInt(String(text).replace(/\D/g, ""), 10) || 0;
  const amountText = (value) => (value ? value.toLocaleString("es-CL") : "");

  const field = (labelText, control) => {
    const label = el("label", "calendar-new__field");
    label.append(el("span", "", labelText), control);
    return label;
  };

  class AdvanceList {
    constructor(form, config, onChange) {
      const find = (name) => form.querySelector(`[data-${name}]`);
      this.config = config;
      this.onChange = onChange;
      this.methodLabels = Object.fromEntries(config.methods);
      this.rows = (config.rows || []).map((row) => ({
        ...row,
        removed: false,
        editable: config.canChangeSaved && !row.locked,
      }));
      this.touched = false;
      this.total = 0;
      this.ui = {
        switchLabel: find("advance-switch-label"),
        toggle: find("advance-switch"),
        body: find("advance-body"),
        list: find("advance-list"),
        add: find("advance-add"),
        error: find("advance-error"),
        summary: find("advance-summary"),
        bar: find("advance-bar"),
        paid: find("advance-paid"),
        balance: find("advance-balance"),
        field: form.querySelector("#id_advances"),
      };
      this.bind();
      this.render();
    }

    newRow() {
      return { id: null, amount: 0, method: this.config.cash, reference: "", removed: false, editable: true };
    }

    hasSaved() {
      return this.rows.some((row) => row.id);
    }

    activeRows() {
      return this.rows.filter((row) => !row.removed);
    }

    paid() {
      return this.activeRows().reduce((sum, row) => sum + row.amount, 0);
    }

    errorMessage() {
      if (this.activeRows().some((row) => row.editable && !row.amount)) {
        return "Ingresa el monto de cada anticipo.";
      }
      const paid = this.paid();
      if (paid > this.total) {
        return `Los anticipos suman ${money(paid)} y no pueden superar el total de los servicios (${money(this.total)}).`;
      }
      return "";
    }

    isValid() {
      return !this.errorMessage();
    }

    removedElement(row) {
      const wrapper = el("div", "calendar-advance__removed");
      const method = this.methodLabels[row.method].toLowerCase();
      const undo = el("button", "btn btn-link btn-sm p-0", "Deshacer");
      undo.type = "button";
      undo.addEventListener("click", () => {
        row.removed = false;
        this.render();
      });
      wrapper.append(el("span", "", `El anticipo de ${money(row.amount)} en ${method} del ${row.date} se quitará al guardar.`), undo);
      return wrapper;
    }

    rowElement(row, index) {
      if (row.removed) {
        return this.removedElement(row);
      }
      const wrapper = el("div", row.id ? "calendar-advance__row is-saved" : "calendar-advance__row");
      const title = row.id ? el("p", "calendar-advance__row-title") : null;
      const syncTitle = () => {
        if (title) {
          title.textContent = `${this.methodLabels[row.method]} - ${row.date}`;
        }
      };
      syncTitle();

      const amount = el("input", "form-control form-control--custom");
      amount.type = "text";
      amount.inputMode = "numeric";
      amount.placeholder = "0";
      amount.value = amountText(row.amount);
      amount.disabled = !row.editable;
      amount.setAttribute("aria-label", `Monto del anticipo ${index + 1}`);
      amount.addEventListener("input", () => {
        row.amount = parseAmount(amount.value);
        amount.value = amountText(row.amount);
        this.onChange();
      });
      amount.addEventListener("blur", () => {
        this.touched = true;
        this.onChange();
      });
      const currency = el("span", "", "$");
      currency.setAttribute("aria-hidden", "true");
      const amountBox = el("span", "calendar-new__money");
      amountBox.append(currency, amount);
      row.input = amount;

      const method = el("select", "form-select form-select--custom");
      method.disabled = !row.editable;
      this.config.methods.forEach(([value, label]) => {
        const option = el("option", "", label);
        option.value = value;
        option.selected = value === row.method;
        method.append(option);
      });

      const reference = el("input", "form-control form-control--custom");
      reference.type = "text";
      reference.maxLength = this.config.referenceMaxLength;
      reference.value = row.reference;
      reference.disabled = !row.editable;
      reference.addEventListener("input", () => {
        row.reference = reference.value;
      });
      const referenceField = field("Referencia (opcional)", reference);
      referenceField.classList.add("calendar-advance__reference");
      const syncReference = () => referenceField.classList.toggle("is-hidden", row.method === this.config.cash);
      method.addEventListener("change", () => {
        row.method = method.value;
        syncReference();
        syncTitle();
      });
      syncReference();

      const fields = el("div", "calendar-advance__fields");
      const required = row.editable ? " *" : "";
      fields.append(field(`Monto${required}`, amountBox), field(`Método de pago${required}`, method), referenceField);
      if (row.editable) {
        const remove = el("button", "calendar-new__line-remove");
        remove.type = "button";
        remove.setAttribute("aria-label", `Quitar anticipo ${index + 1}`);
        remove.append(icon("close"));
        remove.addEventListener("click", () => this.remove(row));
        fields.append(remove);
      } else {
        fields.append(el("span"));
      }
      if (title) {
        wrapper.append(title);
      }
      wrapper.append(fields);
      return wrapper;
    }

    remove(row) {
      if (row.id) {
        row.removed = true;
      } else {
        this.rows.splice(this.rows.indexOf(row), 1);
      }
      if (!this.rows.length) {
        this.ui.toggle.checked = false;
        this.touched = false;
      }
      this.render();
    }

    render() {
      const hasSaved = this.hasSaved();
      this.ui.switchLabel.hidden = hasSaved;
      this.ui.body.hidden = !hasSaved && !this.ui.toggle.checked;
      this.ui.list.replaceChildren(...this.rows.map((row, index) => this.rowElement(row, index)));
      this.onChange();
    }

    renderTotals(total) {
      this.total = total;
      const paid = this.paid();
      const message = this.errorMessage();
      this.showError(this.touched ? message : "");
      this.activeRows().forEach((row) => {
        const invalid = this.touched && row.editable && (!row.amount || paid > total);
        row.input.classList.toggle("is-invalid", invalid);
        row.input.setAttribute("aria-invalid", String(invalid));
      });
      this.ui.summary.hidden = !paid;
      this.ui.paid.textContent = `-${money(Math.min(paid, total))}`;
      this.ui.balance.textContent = money(Math.max(0, total - paid));
      this.ui.bar.style.width = `${total ? Math.min(100, (paid / total) * 100) : 0}%`;
    }

    showError(message) {
      this.ui.error.textContent = message || "";
    }

    reveal() {
      this.touched = true;
      this.onChange();
      const active = this.activeRows().filter((row) => row.editable);
      const invalid = active.find((row) => !row.amount) || (this.isValid() ? null : active[0]);
      if (invalid) {
        invalid.input.focus();
      }
      return this.isValid();
    }

    serialize() {
      const changes = this.rows
        .filter((row) => row.editable)
        .map((row) => {
          if (row.removed) {
            return { id: row.id, quitar: true };
          }
          const change = {
            monto: row.amount,
            metodo: row.method,
            referencia: row.method === this.config.cash ? "" : row.reference.trim(),
          };
          return row.id ? { id: row.id, ...change } : change;
        });
      this.ui.field.value = JSON.stringify(changes);
    }

    bind() {
      this.ui.toggle.addEventListener("change", () => {
        this.rows = this.ui.toggle.checked ? [this.newRow()] : [];
        this.touched = false;
        this.render();
        if (this.rows.length) {
          this.rows[0].input.focus();
        }
      });
      this.ui.add.addEventListener("click", () => {
        this.rows.push(this.newRow());
        this.render();
        this.rows[this.rows.length - 1].input.focus();
      });
    }
  }

  class AppointmentForm {
    constructor(form, config) {
      this.form = form;
      this.config = config;
      this.modal = $(form).closest(".modal");
      this.lines = (config.lines || []).map((line) => ({ ...line }));
      this.service = null;
      this.busyRequest = 0;

      const find = (name) => form.querySelector(`[data-${name}]`);
      this.fields = {
        client: form.querySelector("#id_client"),
        staff: form.querySelector("#id_assigned_to"),
        date: form.querySelector("#id_date"),
        time: form.querySelector("#id_time"),
        notes: form.querySelector("#id_observations"),
        services: form.querySelector("#id_services"),
      };
      this.ui = {
        category: find("category"),
        service: find("service"),
        editor: find("editor"),
        editorName: find("editor-name"),
        editorMeta: find("editor-meta"),
        quantity: find("quantity"),
        discount: find("discount"),
        lineTotal: find("line-total"),
        add: find("add"),
        discountError: find("discount-error"),
        serviceError: form.querySelector(".id_services"),
        busyTitle: find("busy-title"),
        busyList: find("busy-list"),
        notesCount: find("notes-count"),
        sumClient: find("sum-client"),
        sumStaff: find("sum-staff"),
        sumDate: find("sum-date"),
        sumTime: find("sum-time"),
        lines: find("lines"),
        subtotal: find("subtotal"),
        discounts: find("discounts"),
        total: find("total"),
        save: find("save"),
      };
      const advances = config.advances || {};
      this.advances = advances.enabled ? new AdvanceList(form, advances, () => this.renderSummary()) : null;

      this.markCurrentUser();
      this.renderCategories();
      this.renderServices();
      this.prepareModal();
      this.bind();
      this.updateNotesCounter();
      this.renderEditor();
      this.renderSummary();
      this.loadBusyHours();
    }

    prepareModal() {
      const dialog = this.modal.find(".modal-dialog");
      dialog.addClass("modal-dialog-scrollable");
      this.modal.one("hidden.bs.modal", () => {
        dialog.removeClass("modal-dialog-scrollable");
        this.modal.find(".modal-content").empty();
      });
    }

    markCurrentUser() {
      const option = [...this.fields.staff.options].find((item) => Number(item.value) === this.config.currentUser);
      if (option) {
        option.textContent = `${option.textContent} (tú)`;
      }
    }

    selectedText(select) {
      const option = select.options[select.selectedIndex];
      return option && option.value ? option.textContent : "";
    }

    renderCategories() {
      const select = this.ui.category;
      const all = el("option", "", "Todas las categorías");
      all.value = ALL_CATEGORIES;
      select.replaceChildren(all);
      this.config.categories.forEach((category) => {
        const option = el("option", "", category.nombre);
        option.value = String(category.id);
        select.append(option);
      });
    }

    renderServices() {
      const select = this.ui.service;
      const category = this.ui.category.value;
      const placeholder = el("option", "", "Selecciona un servicio");
      placeholder.value = "";
      select.replaceChildren(placeholder);
      this.config.services
        .filter((service) => category === ALL_CATEGORIES || String(service.categoria) === category)
        .forEach((service) => {
          const added = this.lines.some((line) => line.service.id === service.id);
          const option = el("option", "", `${service.nombre}${added ? " (añadido)" : ""}`);
          option.value = String(service.id);
          select.append(option);
        });
      select.value = this.service ? String(this.service.id) : "";
      $(select).trigger("change.select2");
    }

    editorLine() {
      const quantity = Math.min(this.config.maxQuantity, Math.max(1, parseInt(this.ui.quantity.value, 10) || 1));
      const discount = Math.max(0, parseInt(this.ui.discount.value, 10) || 0);
      return { service: this.service, quantity, discount };
    }

    lineTotal(line) {
      return Math.max(0, line.service.precio * line.quantity - line.discount);
    }

    renderEditor() {
      this.ui.editor.hidden = !this.service;
      if (!this.service) {
        this.ui.discountError.hidden = true;
        return;
      }
      const line = this.editorLine();
      const invalid = line.discount > line.service.precio * line.quantity;
      this.ui.editorName.textContent = line.service.nombre;
      this.ui.editorMeta.textContent = `${money(line.service.precio)} c/u · ${line.service.categoriaNombre}`;
      this.ui.lineTotal.textContent = money(this.lineTotal(line));
      this.ui.add.disabled = invalid;
      this.ui.discountError.hidden = !invalid;
    }

    renderSummary() {
      const date = parseDate(this.fields.date.value);
      this.ui.sumClient.textContent = this.selectedText(this.fields.client) || "—";
      this.ui.sumStaff.textContent = this.selectedText(this.fields.staff) || "—";
      this.ui.sumDate.textContent = date ? longDate(date) : "—";
      this.ui.sumTime.textContent = this.fields.time.value || "—";

      const list = this.ui.lines;
      list.replaceChildren();
      if (!this.lines.length) {
        list.append(el("li", "is-empty", "Todavía no agregas servicios."));
      }
      this.lines.forEach((line, index) => {
        const item = el("li");
        const name = el("span", "calendar-new__line-name", line.service.nombre);
        const extra = [];
        if (line.quantity > 1) {
          extra.push(`x${line.quantity}`);
        }
        if (line.discount) {
          extra.push(`-${money(line.discount)}`);
        }
        if (extra.length) {
          name.append(el("small", "", extra.join(" · ")));
        }
        const remove = el("button", "calendar-new__line-remove");
        remove.type = "button";
        remove.setAttribute("aria-label", `Quitar ${line.service.nombre}`);
        remove.append(icon("close"));
        remove.addEventListener("click", () => {
          this.lines.splice(index, 1);
          this.renderServices();
          this.renderSummary();
        });
        item.append(name, el("strong", "", money(this.lineTotal(line))), remove);
        list.append(item);
      });

      const subtotal = this.lines.reduce((sum, line) => sum + line.service.precio * line.quantity, 0);
      const discounts = this.lines.reduce((sum, line) => sum + line.discount, 0);
      this.ui.subtotal.textContent = money(subtotal);
      this.ui.discounts.textContent = discounts ? `-${money(discounts)}` : money(0);
      this.ui.total.textContent = money(subtotal - discounts);
      if (this.advances) {
        this.advances.renderTotals(subtotal - discounts);
      }
      this.ui.save.disabled = !this.isComplete();
    }

    isComplete() {
      const filled = Boolean(this.fields.client.value && this.fields.date.value && this.fields.time.value && this.lines.length);
      return filled && (!this.advances || this.advances.isValid());
    }

    loadBusyHours() {
      const requestId = ++this.busyRequest;
      const { busyTitle: title, busyList: list } = this.ui;
      list.replaceChildren();
      if (!this.fields.date.value) {
        title.textContent = "";
        return;
      }
      const params = new URLSearchParams({ fecha: this.fields.date.value, asignada: this.fields.staff.value });
      if (this.config.appointmentId) {
        params.set("excluir", this.config.appointmentId);
      }
      fetch(`${this.config.busyUrl}?${params}`, { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then((response) => (response.ok ? response.json() : { horas: [] }))
        .catch(() => ({ horas: [] }))
        .then(({ horas = [] }) => {
          if (requestId !== this.busyRequest) {
            return;
          }
          this.busyHours = horas;
          this.renderBusyHours();
        });
    }

    renderBusyHours() {
      const { busyTitle: title, busyList: list } = this.ui;
      const hours = this.busyHours || [];
      list.replaceChildren();
      if (hours.length) {
        title.replaceChildren(icon("warning"), el("span", "", "Horas ocupadas este día"));
      } else {
        title.textContent = "Este día no tiene horas ocupadas.";
      }
      const staff = this.selectedText(this.fields.staff).replace(/ \(tú\)$/, "");
      hours.forEach(({ hora, total, de_asignada: mine }) => {
        const note = mine ? `${staff} ya tiene cita` : `${total === 1 ? "1 cita" : `${total} citas`}`;
        const item = el("li", `calendar-new__busy-item${this.fields.time.value === hora ? " is-selected" : ""}`, hora);
        item.title = note;
        item.setAttribute("aria-label", `${hora}, ${note}`);
        list.append(item);
      });
    }

    updateNotesCounter() {
      const length = this.fields.notes.value.length;
      this.ui.notesCount.textContent = `${length}/${NOTES_MAX} caracteres`;
      this.ui.notesCount.classList.toggle("is-near", length >= NOTES_MAX - 20);
    }

    setError(field, message) {
      const input = this.fields[field] || this.ui.service;
      const feedback = this.form.querySelector(`.${input === this.ui.service ? "id_services" : input.id}`);
      input.classList.toggle("is-invalid", Boolean(message));
      input.setAttribute("aria-invalid", String(Boolean(message)));
      $(input).next(".select2-container").toggleClass("is-invalid", Boolean(message));
      if (feedback) {
        feedback.textContent = message || "";
      }
    }

    clearErrors() {
      ["client", "staff", "date", "time", "notes", "service"].forEach((field) => this.setError(field, ""));
      if (this.advances) {
        this.advances.showError("");
      }
    }

    validate() {
      const errors = {
        client: this.fields.client.value ? "" : REQUIRED,
        date: this.fields.date.value ? "" : REQUIRED,
        time: this.fields.time.value ? "" : REQUIRED,
        service: this.lines.length ? "" : "Agrega al menos un servicio.",
      };
      Object.entries(errors).forEach(([field, message]) => this.setError(field, message));
      const first = Object.keys(errors).find((field) => errors[field]);
      if (first) {
        (this.fields[first] || this.ui.service).focus();
        return false;
      }
      return !this.advances || this.advances.reveal();
    }

    serverErrors(errors) {
      const byId = {
        id_client: "client",
        id_assigned_to: "staff",
        id_date: "date",
        id_time: "time",
        id_observations: "notes",
        id_services: "service",
      };
      errors.forEach(({ id_element: id, error }) => {
        if (byId[id]) {
          this.setError(byId[id], error);
        } else if (id === "id_advances" && this.advances) {
          this.advances.showError(error);
        }
      });
    }

    async save() {
      if (!this.validate()) {
        return;
      }
      this.fields.services.value = JSON.stringify(
        this.lines.map((line) => ({
          ...(line.detalle ? { detalle: line.detalle } : { id: line.service.id }),
          cantidad: line.quantity,
          descuento: line.discount,
        })),
      );
      if (this.advances) {
        this.advances.serialize();
      }
      const data = Object.fromEntries(new FormData(this.form).entries());
      this.ui.save.disabled = true;
      const [response = {}, status] = await getResponseToRequest(this.form.action, data);
      if (status === 200) {
        notifyAlert(response, status);
        this.modal.modal("hide");
        const event = this.config.appointmentId ? CHANGED_EVENT : CREATED_EVENT;
        document.dispatchEvent(new CustomEvent(event, { detail: { fecha: response.fecha } }));
        return;
      }
      if (status === 401 && typeof redirectToLogin === "function") {
        redirectToLogin(response.redirect);
        return;
      }
      if (status === 400) {
        this.clearErrors();
        this.serverErrors(response.errors || []);
      } else {
        notifyAlert(response, status);
      }
      this.ui.save.disabled = !this.isComplete();
    }

    bind() {
      const { fields, ui } = this;
      $(fields.client).on("change", () => {
        this.setError("client", "");
        this.renderSummary();
      });
      $(fields.staff).on("change", () => {
        this.renderSummary();
        this.loadBusyHours();
      });
      fields.date.addEventListener("change", () => {
        this.setError("date", "");
        this.renderSummary();
        this.loadBusyHours();
      });
      fields.time.addEventListener("input", () => {
        this.setError("time", "");
        this.renderSummary();
        this.renderBusyHours();
      });
      fields.notes.addEventListener("input", () => this.updateNotesCounter());
      [ui.quantity, ui.discount].forEach((input) => input.addEventListener("input", () => this.renderEditor()));
      $(ui.category).on("change", () => {
        const category = ui.category.value;
        if (this.service && category !== ALL_CATEGORIES && String(this.service.categoria) !== category) {
          this.service = null;
        }
        this.renderServices();
        this.renderEditor();
      });
      $(ui.service).on("change", () => {
        this.service = this.config.services.find((service) => String(service.id) === ui.service.value) || null;
        const existing = this.lines.find((line) => this.service && line.service.id === this.service.id);
        if (existing) {
          this.service = existing.service;
        }
        ui.quantity.value = existing ? existing.quantity : 1;
        ui.discount.value = existing ? existing.discount : 0;
        this.renderEditor();
      });
      ui.add.addEventListener("click", () => {
        const line = this.editorLine();
        const existing = this.lines.find((item) => item.service.id === line.service.id);
        if (existing) {
          Object.assign(existing, { quantity: line.quantity, discount: line.discount });
        } else {
          this.lines.push(line);
        }
        this.service = null;
        this.setError("service", "");
        this.renderServices();
        this.renderEditor();
        this.renderSummary();
      });
      ui.save.addEventListener("click", () => this.save());
    }
  }

  window.AppointmentForm = AppointmentForm;
  window.APPOINTMENT_CREATED_EVENT = CREATED_EVENT;
  window.APPOINTMENT_CHANGED_EVENT = CHANGED_EVENT;
  window.initAppointmentForm = (form, config) => new AppointmentForm(form, config);
})(window, jQuery);
