(function (window) {
  "use strict";

  const HiCalendar = (window.HiCalendar = window.HiCalendar || {});
  const { dates, CalendarApi, MonthRenderer, AppointmentMenu, PeriodNavigator, TodayButton, SearchBox } = HiCalendar;

  const LOADER_DELAY = 150;

  class CalendarController {
    constructor(root, config) {
      this.root = root;
      this.config = config;
      this.today = dates.parse(config.today);
      this.search = "";
      this.requestId = 0;
      this.loaderTimer = null;

      const find = (name) => root.querySelector(`[data-cal2-${name}]`);
      this.status = find("status");
      this.newButton = find("new");
      this.loader = find("loader");
      if (typeof processingLoaderTemplate === "function") {
        this.loader.innerHTML = processingLoaderTemplate("Cargando citas…");
      }

      this.api = new CalendarApi(config.dataUrl);
      this.menu = new AppointmentMenu({ onChange: () => this.refresh() });
      this.renderer = new MonthRenderer({
        container: root,
        today: this.today,
        dayUrl: config.dayUrl,
        datePlaceholder: config.datePlaceholder,
        onAppointment: (appointment, trigger) => this.menu.open(appointment, trigger),
      });
      this.navigator = new PeriodNavigator({
        prevButton: find("prev"),
        nextButton: find("next"),
        title: find("title"),
        onMove: (step) => this.go(dates.addMonths(this.cursor, step)),
      });
      this.todayButton = new TodayButton({
        button: find("today"),
        onToday: () => this.go(new Date(this.today.getFullYear(), this.today.getMonth(), 1)),
      });
      this.searchBox = new SearchBox({
        input: find("search"),
        onSearch: (value) => {
          this.search = value;
          this.load();
        },
      });

      const requested = dates.fromMonthParam(new URLSearchParams(window.location.search).get("fecha"));
      this.go(requested || new Date(this.today.getFullYear(), this.today.getMonth(), 1));
    }

    params(cursor = this.cursor) {
      const { start, end } = this.renderer.range(cursor);
      const params = { vista: this.config.view, desde: dates.toISO(start), hasta: dates.toISO(end) };
      if (this.search) {
        params.buscar = this.search;
      }
      return params;
    }

    go(cursor) {
      this.cursor = cursor;
      this.navigator.setTitle(dates.monthTitle(cursor));
      const url = new URL(window.location.href);
      url.searchParams.set("fecha", dates.toMonthParam(cursor));
      window.history.replaceState(null, "", url);
      const appointmentDate = dates.sameDayInMonth(this.today.getDate(), cursor);
      this.newButton.href = this.config.newAppointmentUrl.replace(this.config.datePlaceholder, dates.toISO(appointmentDate));
      this.renderer.renderSkeleton(cursor);
      this.load();
    }

    load() {
      const params = this.params();
      const requestId = ++this.requestId;
      this.setBusy(true, this.api.has(params));
      this.api
        .load(params)
        .then((data) => {
          if (requestId !== this.requestId) {
            return;
          }
          this.renderer.renderContent(data);
          this.updateStatus(data);
          this.setBusy(false);
          this.prefetch();
        })
        .catch((error) => {
          if (error.name === "AbortError" || requestId !== this.requestId) {
            return;
          }
          this.setBusy(false);
          this.renderer.renderError(error.message, () => this.load());
        });
    }

    refresh() {
      this.api.clear();
      this.load();
    }

    prefetch() {
      if (this.search) {
        return;
      }
      [-1, 1].forEach((step) => this.api.prefetch(this.params(dates.addMonths(this.cursor, step))));
    }

    setBusy(busy, cached = false) {
      this.root.setAttribute("aria-busy", String(busy));
      this.navigator.setDisabled(busy);
      this.todayButton.setDisabled(busy);
      clearTimeout(this.loaderTimer);
      if (busy && !cached) {
        this.loaderTimer = setTimeout(() => {
          this.loader.hidden = false;
        }, LOADER_DELAY);
      } else {
        this.loader.hidden = true;
      }
    }

    updateStatus(data) {
      if (!this.search) {
        this.status.hidden = true;
        this.status.textContent = "";
        return;
      }
      const total = Object.values(data.dias || {}).reduce((sum, day) => sum + day.total, 0);
      this.status.hidden = false;
      this.status.textContent = total
        ? `${total} ${total === 1 ? "cita coincide" : "citas coinciden"} con «${this.search}»`
        : `Ninguna cita coincide con «${this.search}»`;
    }
  }

  HiCalendar.CalendarController = CalendarController;
  window.initCalendar = (root, config) => new CalendarController(root, config);
})(window);
