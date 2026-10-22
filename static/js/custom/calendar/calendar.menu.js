(function (window, $) {
  "use strict";

  const HiCalendar = (window.HiCalendar = window.HiCalendar || {});
  const { dom } = HiCalendar;

  const MENU_ID = "calendar-actions";

  class AppointmentMenu {
    constructor() {
      this.menu = null;
      this.trigger = null;
      this.onOutside = this.onOutside.bind(this);
      this.onKey = this.onKey.bind(this);
      this.onViewport = () => this.close(false);
    }

    open(appointment, trigger) {
      const sameTrigger = this.menu && this.trigger === trigger;
      this.close(false);
      if (sameTrigger || !appointment.acciones.length) {
        return;
      }
      this.trigger = trigger;
      const menu = dom.el("div", "dropdown-menu calendar-actions");
      menu.id = MENU_ID;
      menu.setAttribute("role", "menu");
      menu.setAttribute("aria-label", `Opciones de la cita de ${appointment.cliente}`);
      const head = dom.el("div", "calendar-actions__head");
      head.setAttribute("aria-hidden", "true");
      head.append(dom.el("span", "calendar-actions__client", appointment.cliente), dom.el("span", "calendar-actions__when", appointment.hora));
      menu.append(head);

      appointment.acciones.forEach(({ label, icon, iconImage, link, className = "" }) => {
        if (className.includes("is-danger")) {
          const divider = dom.el("hr", "dropdown-divider");
          divider.setAttribute("role", "separator");
          menu.append(divider);
        }
        const item = dom.el("a", `dropdown-item ${className}`);
        item.href = "#";
        item.dataset.formUrl = link;
        item.setAttribute("role", "menuitem");
        item.append(iconImage ? this.image(iconImage) : dom.icon(icon, "icon--menu"), dom.el("span", "", label));
        menu.append(item);
      });

      document.body.append(menu);
      this.position(menu, trigger);
      this.menu = menu;
      this.initializeModals();
      menu.querySelectorAll("[role='menuitem']").forEach((item) => {
        item.addEventListener("click", (event) => {
          event.preventDefault();
          setTimeout(() => this.close(false));
        });
      });
      trigger.setAttribute("aria-expanded", "true");
      document.addEventListener("pointerdown", this.onOutside, true);
      document.addEventListener("keydown", this.onKey, true);
      window.addEventListener("resize", this.onViewport);
      document.addEventListener("scroll", this.onViewport, true);
      menu.querySelector("[role='menuitem']").focus();
    }

    image(src) {
      const image = dom.el("img", "icon--menu");
      image.src = src;
      image.alt = "";
      image.width = 18;
      image.height = 18;
      return image;
    }

    position(menu, trigger) {
      const rect = trigger.getBoundingClientRect();
      const left = Math.min(rect.left, window.innerWidth - menu.offsetWidth - 8);
      let top = rect.bottom + 6;
      if (top + menu.offsetHeight > window.innerHeight - 8) {
        top = rect.top - menu.offsetHeight - 6;
      }
      menu.style.left = `${Math.max(8, left)}px`;
      menu.style.top = `${Math.max(8, top)}px`;
    }

    initializeModals() {
      initializeAllBSModals({ elementIDs: `#${MENU_ID} .bs-modal` });
      initializeAllBSXLModals({ elementIDs: `#${MENU_ID} .bs-xl-modal` });
      initializeAllCanvasBSModals(`#${MENU_ID} .canvas-modal`);
    }

    close(restoreFocus) {
      if (!this.menu) {
        return;
      }
      this.menu.remove();
      this.menu = null;
      document.removeEventListener("pointerdown", this.onOutside, true);
      document.removeEventListener("keydown", this.onKey, true);
      window.removeEventListener("resize", this.onViewport);
      document.removeEventListener("scroll", this.onViewport, true);
      if (this.trigger) {
        this.trigger.setAttribute("aria-expanded", "false");
        if (restoreFocus && document.body.contains(this.trigger)) {
          this.trigger.focus();
        }
      }
    }

    onOutside(event) {
      if (this.menu && !this.menu.contains(event.target) && !this.trigger.contains(event.target)) {
        this.close(false);
      }
    }

    onKey(event) {
      const items = [...this.menu.querySelectorAll("[role='menuitem']")];
      const index = items.indexOf(document.activeElement);
      if (event.key === "Escape") {
        event.preventDefault();
        this.close(true);
      } else if (event.key === "Tab") {
        this.close(false);
      } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        const step = event.key === "ArrowDown" ? 1 : -1;
        items[(index + step + items.length) % items.length].focus();
      }
    }
  }

  HiCalendar.AppointmentMenu = AppointmentMenu;
})(window, jQuery);
