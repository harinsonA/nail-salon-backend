(function (window) {
  "use strict";

  const HiCalendar = (window.HiCalendar = window.HiCalendar || {});
  const { dates, dom } = HiCalendar;

  const STATUS_LABEL = { pendiente: "Pendiente", completada: "Completada", cancelada: "Cancelada" };

  class CalendarRenderer {
    constructor({ container, today, dayUrl, datePlaceholder, onAppointment }) {
      this.container = container;
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
    range(cursor) {
      const days = dates.monthDays(cursor);
      return { days, start: days[0], end: days[days.length - 1] };
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
      const board = this.container.querySelector("[data-cal2-board]");
      board.replaceChildren(grid);
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
      const chip = dom.el("button", `cal2-chip is-${status}`);
      chip.type = "button";
      chip.setAttribute("aria-label", this.label(appointment));
      chip.setAttribute("aria-haspopup", "menu");
      chip.setAttribute("aria-expanded", "false");
      chip.append(
        dom.el("span", `cal2-dot cal2-dot--${status}`),
        dom.el("span", "cal2-chip__time", appointment.hora),
        this.name(appointment, "cal2-chip__label"),
      );
      chip.addEventListener("click", () => this.onAppointment(appointment, chip));
      return chip;
    }
  }

  HiCalendar.CalendarRenderer = CalendarRenderer;
  HiCalendar.MonthRenderer = MonthRenderer;
})(window);
