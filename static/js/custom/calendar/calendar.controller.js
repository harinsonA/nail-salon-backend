(function (window) {
  "use strict";

  const HiCalendar = (window.HiCalendar = window.HiCalendar || {});
  const {
    dates,
    CalendarApi,
    MonthRenderer,
    WeekRenderer,
    DayRenderer,
    AppointmentMenu,
    PeriodNavigator,
    TodayButton,
    ViewSwitch,
    SearchBox,
  } = HiCalendar;

  const LOADER_DELAY = 150;
  const RENDERERS = { dia: DayRenderer, semana: WeekRenderer, mes: MonthRenderer };

  class CalendarController {
    constructor(root, config) {
      this.root = root;
      this.config = config;
      this.today = dates.parse(config.today);
      this.settings = { visible: config.visible, showDebt: config.showDebt };
      this.search = "";
      this.requestId = 0;
      this.loaderTimer = null;

      const find = (name) => root.querySelector(`[data-calendar-${name}]`);
      this.status = find("status");
      this.newButton = find("new");
      const showDate = ({ detail }) => {
        this.api.clear();
        if (detail && detail.fecha) {
          this.go(dates.parse(detail.fecha));
        } else {
          this.load();
        }
      };
      document.addEventListener(window.APPOINTMENT_CHANGED_EVENT, showDate);
      document.addEventListener(window.APPOINTMENT_CREATED_EVENT, showDate);
      this.settingsButton = find("settings");
      initializeCanvasBSModals(this.settingsButton);
      document.addEventListener(HiCalendar.PREFERENCES_EVENT, ({ detail }) => this.applySettings(detail));
      this.loader = find("loader");
      if (typeof processingLoaderTemplate === "function") {
        this.loader.innerHTML = processingLoaderTemplate("Cargando citas…");
      }

      this.api = new CalendarApi(config.dataUrl);
      this.menu = new AppointmentMenu();
      this.renderers = {};
      Object.entries(RENDERERS).forEach(([view, Renderer]) => {
        this.renderers[view] = new Renderer({
          container: root,
          today: this.today,
          hours: config.hours,
          settings: this.settings,
          onDay: (date) => this.openDay(date),
          onAppointment: (appointment, trigger) => this.menu.open(appointment, trigger),
        });
      });
      this.navigator = new PeriodNavigator({
        prevButton: find("prev"),
        nextButton: find("next"),
        title: find("title"),
        onMove: (step) => this.go(this.renderer.move(this.cursor, step)),
      });
      this.todayButton = new TodayButton({ button: find("today"), onToday: () => this.go(this.today) });
      this.viewSwitch = new ViewSwitch({
        buttons: [...root.querySelectorAll("[data-calendar-view]")],
        onChange: (view) => this.setView(view),
      });
      this.searchBox = new SearchBox({
        input: find("search"),
        onSearch: (value) => {
          this.search = value;
          this.load();
        },
      });

      const query = new URLSearchParams(window.location.search);
      this.view = RENDERERS[query.get("vista")] ? query.get("vista") : config.view;
      this.viewSwitch.setActive(this.view);
      this.go(dates.fromParam(query.get("fecha")) || this.today);
    }

    applySettings({ view, visible, showDebt, filtered }) {
      Object.assign(this.settings, { visible, showDebt });
      this.settingsButton.classList.toggle("is-filtered", filtered);
      this.settingsButton.setAttribute(
        "aria-label",
        filtered ? "Configurar el calendario (hay estados ocultos)" : "Configurar el calendario",
      );
      this.api.clear();
      if (view !== this.view && RENDERERS[view]) {
        this.setView(view);
        return;
      }
      this.load();
    }

    get renderer() {
      return this.renderers[this.view];
    }

    params(cursor = this.cursor) {
      const { start, end } = this.renderer.range(cursor);
      const params = { vista: this.view, desde: dates.toISO(start), hasta: dates.toISO(end) };
      if (this.search) {
        params.buscar = this.search;
      }
      return params;
    }

    setView(view) {
      if (view === this.view || !RENDERERS[view]) {
        return;
      }
      this.view = view;
      this.viewSwitch.setActive(view);
      this.go(this.cursor);
    }

    openDay(date) {
      this.view = "dia";
      this.viewSwitch.setActive(this.view);
      this.go(date);
    }

    go(cursor) {
      this.cursor = cursor;
      this.navigator.setTitle(this.renderer.title(cursor));
      const url = new URL(window.location.href);
      url.searchParams.set("vista", this.view);
      url.searchParams.set("fecha", dates.toISO(cursor));
      window.history.replaceState(null, "", url);
      this.setNewAppointmentUrl(this.config.newAppointmentUrl.replace(this.config.datePlaceholder, dates.toISO(cursor)));
      this.renderer.renderSkeleton(cursor);
      this.load();
    }

    setNewAppointmentUrl(url) {
      this.newButton.dataset.formUrl = url;
      window.jQuery(this.newButton).off("click");
      initializeBSXLModals(this.newButton, { formURL: url });
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
      [-1, 1].forEach((step) => this.api.prefetch(this.params(this.renderer.move(this.cursor, step))));
    }

    setBusy(busy, cached = false) {
      this.root.setAttribute("aria-busy", String(busy));
      this.navigator.setDisabled(busy);
      this.todayButton.setDisabled(busy);
      this.viewSwitch.setDisabled(busy);
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
