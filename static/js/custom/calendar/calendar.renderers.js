(function (window) {
  "use strict";

  const HiCalendar = (window.HiCalendar = window.HiCalendar || {});
  const { dates, dom } = HiCalendar;

  const STATUS_LABEL = { pendiente: "Pendiente", completada: "Completada", cancelada: "Cancelada" };

  class CalendarRenderer {
    constructor({ container, today, hours, dayUrl, datePlaceholder, onAppointment }) {
      this.container = container;
      this.hours = hours;
      this.today = today;
      this.dayUrl = dayUrl;
      this.datePlaceholder = datePlaceholder;
      this.onAppointment = onAppointment;
    }

    visualStatus(appointment) {
      return appointment.sin_cerrar ? "vencida" : appointment.estado;
    }

    statusLabel(appointment) {
      return appointment.sin_cerrar ? "Pendiente sin cerrar" : STATUS_LABEL[appointment.estado];
    }

    dayLink(date) {
      return this.dayUrl.replace(this.datePlaceholder, dates.toISO(date));
    }

    name(appointment, className) {
      const wrap = dom.el("span", `${className} cal2-name`);
      wrap.append(dom.el("span", "cal2-name__text", appointment.cliente));
      if (appointment.con_saldo) {
        const icon = dom.icon("info", "cal2-debt");
        icon.title = "Tiene saldo pendiente";
        wrap.append(icon);
      }
      return wrap;
    }

    label(appointment) {
      const debt = appointment.con_saldo ? ", con saldo pendiente" : "";
      return `${appointment.cliente}, a las ${appointment.hora}, ${this.statusLabel(appointment)}${debt}`;
    }

    board() {
      return this.container.querySelector("[data-cal2-board]");
    }

    appointmentButton(appointment, className) {
      const button = dom.el("button", className);
      button.type = "button";
      button.setAttribute("aria-label", this.label(appointment));
      button.setAttribute("aria-haspopup", "menu");
      button.setAttribute("aria-expanded", "false");
      button.addEventListener("click", () => this.onAppointment(appointment, button));
      return button;
    }

    renderError(message, onRetry) {
      const box = dom.el("div", "cal2-feedback cal2-feedback--error");
      box.setAttribute("role", "alert");
      box.append(dom.icon("error", "icon--action"), dom.el("p", "", message));
      const retry = dom.el("button", "btn btn-sm btn-outline-secondary", "Reintentar");
      retry.type = "button";
      retry.addEventListener("click", onRetry);
      box.append(retry);
      this.container.querySelector("[data-cal2-feedback]").replaceChildren(box);
    }

    clearFeedback() {
      this.container.querySelector("[data-cal2-feedback]").replaceChildren();
    }
  }

  class MonthRenderer extends CalendarRenderer {
    monthStart(cursor) {
      return new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    }

    range(cursor) {
      const days = dates.monthDays(this.monthStart(cursor));
      return { days, start: days[0], end: days[days.length - 1] };
    }

    title(cursor) {
      return dates.monthTitle(cursor);
    }

    move(cursor, step) {
      return dates.shiftMonths(cursor, step);
    }

    renderSkeleton(cursor) {
      const { days } = this.range(cursor);
      const grid = dom.el("div", "cal2-month");
      days.slice(0, 7).forEach((date) => {
        const head = dom.el("div", "cal2-month__dow");
        head.append(
          dom.el("span", "cal2-dname__full", dates.weekdayName(date)),
          dom.el("span", "cal2-dname__short", dates.weekdayShort(date)),
        );
        grid.append(head);
      });
      this.cells = new Map();
      days.forEach((date) => {
        const inMonth = date.getMonth() === cursor.getMonth();
        const cell = dom.el("div", `cal2-month__cell${inMonth ? "" : " is-out"}${dates.sameDay(date, this.today) ? " is-today" : ""}`);
        const number = dom.el("a", "cal2-month__num", String(date.getDate()));
        number.href = this.dayLink(date);
        number.setAttribute("aria-label", `Ver el ${dates.weekdayName(date)} ${date.getDate()}`);
        const events = dom.el("div", "cal2-month__events");
        cell.append(number, events);
        grid.append(cell);
        this.cells.set(dates.toISO(date), { cell, events, date });
      });
      this.board().replaceChildren(grid);
    }

    renderContent(data) {
      this.clearFeedback();
      this.cells.forEach(({ cell, events, date }, key) => {
        events.replaceChildren();
        const more = cell.querySelector(".cal2-more");
        if (more) {
          more.remove();
        }
        const day = (data.dias || {})[key];
        if (!day) {
          return;
        }
        day.citas.forEach((appointment) => events.append(this.chip(appointment)));
        if (day.mas) {
          const link = dom.el("a", "cal2-more", `+${day.mas} más`);
          link.href = this.dayLink(date);
          link.setAttribute("aria-label", `Ver las ${day.total} citas del ${dates.weekdayName(date)} ${date.getDate()}`);
          cell.append(link);
        }
      });
    }

    chip(appointment) {
      const status = this.visualStatus(appointment);
      const chip = this.appointmentButton(appointment, `cal2-chip is-${status}`);
      chip.append(
        dom.el("span", `cal2-dot cal2-dot--${status}`),
        dom.el("span", "cal2-chip__time", appointment.hora),
        this.name(appointment, "cal2-chip__label"),
      );
      return chip;
    }
  }

  class WeekRenderer extends CalendarRenderer {
    range(cursor) {
      const days = dates.weekDays(cursor);
      return { days, start: days[0], end: days[days.length - 1] };
    }

    title(cursor) {
      return dates.weekTitle(this.range(cursor).days);
    }

    move(cursor, step) {
      return dates.addDays(cursor, step * 7);
    }

    hourHeight() {
      const value = parseFloat(window.getComputedStyle(this.container).getPropertyValue("--cal2-hour"));
      return value || 76;
    }

    renderSkeleton(cursor) {
      const { days } = this.range(cursor);
      const hour = this.hourHeight();
      const scroll = dom.el("div", "cal2-scroll");
      const grid = dom.el("div", "cal2-grid");
      grid.style.setProperty("--cal2-cols", days.length);
      grid.style.setProperty("--cal2-hours", this.hours.hasta - this.hours.desde);
      grid.append(dom.el("div", "cal2-grid__corner"));
      days.forEach((date) => {
        const head = dom.el("div", `cal2-grid__head${dates.sameDay(date, this.today) ? " is-today" : ""}`);
        const name = dom.el("span", "cal2-dname");
        name.append(
          dom.el("span", "cal2-dname__full", dates.weekdayName(date)),
          dom.el("span", "cal2-dname__short", dates.weekdayShort(date)),
        );
        head.append(name, dom.el("span", "cal2-grid__head-num", String(date.getDate())));
        grid.append(head);
      });
      const gutter = dom.el("div", "cal2-gutter");
      for (let h = this.hours.desde + 1; h < this.hours.hasta; h += 1) {
        const label = dom.el("span", "cal2-gutter__label", `${String(h).padStart(2, "0")}:00`);
        label.style.top = `${(h - this.hours.desde) * hour}px`;
        gutter.append(label);
      }
      grid.append(gutter);
      this.columns = new Map();
      days.forEach((date) => {
        const isToday = dates.sameDay(date, this.today);
        const column = dom.el("div", `cal2-col${isToday ? " is-today" : ""}`);
        if (isToday) {
          column.append(this.nowLine(hour));
        }
        grid.append(column);
        this.columns.set(dates.toISO(date), column);
      });
      scroll.append(grid);
      this.board().replaceChildren(scroll);
      const containsToday = days.some((date) => dates.sameDay(date, this.today));
      const focusHour = containsToday ? new Date().getHours() - 1 : 9;
      const clamped = Math.min(Math.max(focusHour, this.hours.desde), this.hours.hasta);
      scroll.scrollTop = (clamped - this.hours.desde) * hour;
    }

    nowLine(hour) {
      const line = dom.el("div", "cal2-now");
      line.setAttribute("aria-hidden", "true");
      const now = new Date();
      const minutes = now.getHours() * 60 + now.getMinutes();
      line.style.top = `${((minutes - this.hours.desde * 60) / 60) * hour}px`;
      return line;
    }

    renderContent(data) {
      this.clearFeedback();
      const hour = this.hourHeight();
      this.columns.forEach((column, key) => {
        column.querySelectorAll(".cal2-event").forEach((block) => block.remove());
        const day = (data.dias || {})[key];
        if (!day) {
          return;
        }
        day.bloques
          .filter((block) => block.hora >= this.hours.desde && block.hora < this.hours.hasta)
          .forEach((block) => column.append(this.block(block, hour)));
      });
    }

    block(block, hour) {
      const single = block.citas.length === 1;
      const element = single
        ? this.appointmentButton(block.citas[0], `cal2-event cal2-event--${block.estado}`)
        : dom.el("div", `cal2-event cal2-event--${block.estado} cal2-event--group`);
      element.style.top = `${(block.hora - this.hours.desde) * hour + 1}px`;
      element.style.height = `${hour - 3}px`;
      if (single) {
        const [appointment] = block.citas;
        element.append(dom.el("span", "cal2-event__time", appointment.hora), this.name(appointment, "cal2-event__client"));
        return element;
      }
      element.setAttribute("role", "group");
      element.setAttribute("aria-label", `${block.citas.length} citas a las ${String(block.hora).padStart(2, "0")}:00`);
      block.citas.forEach((appointment) => {
        const status = this.visualStatus(appointment);
        const entry = this.appointmentButton(appointment, `cal2-entry is-${status}`);
        const text = dom.el("span", "cal2-entry__text");
        text.append(dom.el("span", "cal2-entry__time", appointment.hora), this.name(appointment, "cal2-entry__client"));
        entry.append(dom.el("span", `cal2-dot cal2-dot--${status}`), text);
        element.append(entry);
      });
      return element;
    }
  }

  HiCalendar.CalendarRenderer = CalendarRenderer;
  HiCalendar.MonthRenderer = MonthRenderer;
  HiCalendar.WeekRenderer = WeekRenderer;
})(window);
