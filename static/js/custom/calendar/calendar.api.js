(function (window) {
  "use strict";

  const HiCalendar = (window.HiCalendar = window.HiCalendar || {});

  class CalendarApi {
    constructor(url) {
      this.url = url;
      this.cache = new Map();
      this.controller = null;
    }

    key(params) {
      return new URLSearchParams(params).toString();
    }

    has(params) {
      return this.cache.has(this.key(params));
    }

    clear() {
      this.cache.clear();
    }

    request(params, signal) {
      const query = this.key(params);
      return fetch(`${this.url}?${query}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        signal,
      }).then((response) =>
        response
          .json()
          .catch(() => ({}))
          .then((body) => {
            if (response.ok) {
              this.cache.set(query, body);
              return body;
            }
            if (response.status === 401 && typeof redirectToLogin === "function") {
              redirectToLogin(body.redirect);
            }
            const error = new Error(body.message || "No se pudo cargar el calendario.");
            error.status = response.status;
            throw error;
          }),
      );
    }

    load(params) {
      const query = this.key(params);
      if (this.cache.has(query)) {
        return Promise.resolve(this.cache.get(query));
      }
      if (this.controller) {
        this.controller.abort();
      }
      this.controller = new AbortController();
      return this.request(params, this.controller.signal);
    }

    prefetch(params) {
      if (this.has(params)) {
        return;
      }
      this.request(params).catch(() => {});
    }
  }

  HiCalendar.CalendarApi = CalendarApi;
})(window);
