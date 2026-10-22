(function (window, $) {
  "use strict";

  const CREATED_EVENT = "appointment:created";
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

  class AppointmentForm {
    constructor(form, config) {
      this.form = form;
      this.config = config;
      this.modal = $(form).closest(".modal");
      this.lines = [];
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
        const name = el("span", "cal2-new__line-name", line.service.nombre);
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
        const remove = el("button", "cal2-new__line-remove");
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
      this.ui.save.disabled = !this.isComplete();
    }

    isComplete() {
      return Boolean(this.fields.client.value && this.fields.date.value && this.fields.time.value && this.lines.length);
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
        const item = el("li", `cal2-new__busy-item${this.fields.time.value === hora ? " is-selected" : ""}`, hora);
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
      }
      return !first;
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
        }
      });
    }

    async save() {
      if (!this.validate()) {
        return;
      }
      this.fields.services.value = JSON.stringify(
        this.lines.map((line) => ({ id: line.service.id, cantidad: line.quantity, descuento: line.discount })),
      );
      const data = Object.fromEntries(new FormData(this.form).entries());
      this.ui.save.disabled = true;
      const [response = {}, status] = await getResponseToRequest(this.form.action, data);
      if (status === 200) {
        notifyAlert(response, status);
        this.modal.modal("hide");
        document.dispatchEvent(new CustomEvent(CREATED_EVENT, { detail: { fecha: response.fecha } }));
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
        ui.quantity.value = existing ? existing.quantity : 1;
        ui.discount.value = existing ? existing.discount : 0;
        this.renderEditor();
      });
      ui.add.addEventListener("click", () => {
        const line = this.editorLine();
        const existing = this.lines.find((item) => item.service.id === line.service.id);
        if (existing) {
          Object.assign(existing, line);
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
  window.initAppointmentForm = (form, config) => new AppointmentForm(form, config);
})(window, jQuery);
