(function (window) {
  "use strict";

  const HiCalendar = (window.HiCalendar = window.HiCalendar || {});
  const { debounce } = HiCalendar;

  class PeriodNavigator {
    constructor({ prevButton, nextButton, title, onMove }) {
      this.prevButton = prevButton;
      this.nextButton = nextButton;
      this.title = title;
      prevButton.addEventListener("click", () => onMove(-1));
      nextButton.addEventListener("click", () => onMove(1));
    }

    setTitle(text) {
      this.title.textContent = text;
    }

    setDisabled(disabled) {
      this.prevButton.disabled = disabled;
      this.nextButton.disabled = disabled;
    }
  }

  class TodayButton {
    constructor({ button, onToday }) {
      this.button = button;
      button.addEventListener("click", onToday);
    }

    setDisabled(disabled) {
      this.button.disabled = disabled;
    }
  }

  class ViewSwitch {
    constructor({ buttons, onChange }) {
      this.buttons = buttons;
      buttons.forEach((button) => {
        button.addEventListener("click", () => onChange(button.dataset.cal2View));
      });
    }

    setActive(view) {
      this.buttons.forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.cal2View === view));
      });
    }

    setDisabled(disabled) {
      this.buttons.forEach((button) => {
        button.disabled = disabled;
      });
    }
  }

  class SearchBox {
    constructor({ input, onSearch, delay = 250 }) {
      this.input = input;
      const notify = debounce(() => onSearch(this.value()), delay);
      input.addEventListener("input", notify);
    }

    value() {
      return this.input.value.trim();
    }
  }

  HiCalendar.PeriodNavigator = PeriodNavigator;
  HiCalendar.TodayButton = TodayButton;
  HiCalendar.SearchBox = SearchBox;
  HiCalendar.ViewSwitch = ViewSwitch;
})(window);
