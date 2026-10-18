(() => {
  const home = document.querySelector(".error-btn--primary").href;
  const actions = {
    back: () => (history.length > 1 ? history.back() : location.assign(home)),
    reload: () => location.reload(),
  };

  document.querySelectorAll("[data-error-action]").forEach((button) => {
    button.addEventListener("click", () => actions[button.dataset.errorAction]?.());
  });

  const countdown = document.querySelector("[data-redirect-url]");
  if (!countdown) return;

  const { redirectUrl, destination } = countdown.dataset;
  const total = Number(countdown.dataset.seconds);
  const text = countdown.querySelector(".error-card__countdown-text");
  const fill = countdown.querySelector(".error-card__fill");
  let left = total;

  const tick = () => {
    left -= 1;
    fill.style.transition = "transform 1s linear";
    fill.style.transform = `scaleX(${Math.max(left, 0) / total})`;
    if (left > 0) {
      text.textContent = `Te llevamos ${destination} en ${left} s`;
      return;
    }
    clearInterval(timer);
    text.textContent = `Redirigiendo ${destination}…`;
    location.assign(redirectUrl);
  };

  const timer = setInterval(tick, 1000);
})();
