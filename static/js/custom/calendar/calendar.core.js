(function (window) {
  "use strict";

  const HiCalendar = (window.HiCalendar = window.HiCalendar || {});

  const fmtMonth = new Intl.DateTimeFormat("es-CL", { month: "long" });
  const fmtWeekday = new Intl.DateTimeFormat("es-CL", { weekday: "long" });
  const fmtWeekdayShort = new Intl.DateTimeFormat("es-CL", { weekday: "short" });

  const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);

  const dates = {
    parse(value) {
      const [year, month, day] = value.split("-").map(Number);
      return new Date(year, month - 1, day);
    },
    toISO(date) {
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${date.getFullYear()}-${month}-${day}`;
    },
    toMonthParam(date) {
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    },
    fromMonthParam(value) {
      const match = /^(\d{4})-(\d{2})$/.exec(value || "");
      if (!match || Number(match[2]) < 1 || Number(match[2]) > 12) {
        return null;
      }
      return new Date(Number(match[1]), Number(match[2]) - 1, 1);
    },
    addDays(date, days) {
      return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
    },
    sameDayInMonth(day, monthStart) {
      const last = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0).getDate();
      return new Date(monthStart.getFullYear(), monthStart.getMonth(), Math.min(day, last));
    },
    addMonths(date, months) {
      return new Date(date.getFullYear(), date.getMonth() + months, 1);
    },
    startOfWeek(date) {
      return dates.addDays(date, -((date.getDay() + 6) % 7));
    },
    sameDay(a, b) {
      return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
    },
    monthDays(monthStart) {
      const first = dates.startOfWeek(monthStart);
      const last = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0);
      const weeks = Math.ceil((Math.round((last - first) / 86400000) + 1) / 7);
      return Array.from({ length: weeks * 7 }, (_, index) => dates.addDays(first, index));
    },
    monthTitle(date) {
      return `${capitalize(fmtMonth.format(date))} ${date.getFullYear()}`;
    },
    weekdayName(date) {
      return fmtWeekday.format(date);
    },
    weekdayShort(date) {
      return fmtWeekdayShort.format(date).replace(".", "");
    },
  };

  const dom = {
    el(tag, className, text) {
      const node = document.createElement(tag);
      if (className) {
        node.className = className;
      }
      if (text !== undefined) {
        node.textContent = text;
      }
      return node;
    },
    icon(name, className) {
      const node = dom.el("span", `material-symbols-outlined ${className || ""}`.trim(), name);
      node.setAttribute("aria-hidden", "true");
      return node;
    },
  };

  const debounce = (callback, wait) => {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => callback(...args), wait);
    };
  };

  HiCalendar.dates = dates;
  HiCalendar.dom = dom;
  HiCalendar.debounce = debounce;
})(window);
