const FORMSET_MAIN_FIELD = "es_principal";

const initializeFormsets = (container) => {
  container.querySelectorAll("[data-formset]").forEach((section) => {
    const prefix = section.dataset.formset;
    const totalForms = section.querySelector(`#id_${prefix}-TOTAL_FORMS`);
    const rows = section.querySelector(".formset-rows");
    const template = section.querySelector(".formset-template");
    const emptyMessage = section.querySelector(".formset-empty-message");

    const visibleRows = () => [...rows.querySelectorAll(".formset-row:not(.d-none)")];
    const mainInputs = () =>
      visibleRows()
        .map((row) => row.querySelector(`input[name$="-${FORMSET_MAIN_FIELD}"]`))
        .filter(Boolean);
    const refresh = () => {
      const inputs = mainInputs();
      if (inputs.length && !inputs.some((input) => input.checked)) {
        inputs[0].checked = true;
      }
      emptyMessage?.classList.toggle("d-none", visibleRows().length > 0);
    };

    section.addEventListener("change", ({ target }) => {
      if (!target.matches(`input[name$="-${FORMSET_MAIN_FIELD}"]`)) return;
      if (!target.checked) {
        target.checked = true;
        return;
      }
      mainInputs().forEach((input) => {
        if (input !== target) input.checked = false;
      });
    });

    section.addEventListener("click", ({ target }) => {
      const removeButton = target.closest(".formset-remove");
      if (removeButton) {
        const row = removeButton.closest(".formset-row");
        row.querySelector('input[name$="-DELETE"]').checked = true;
        const main = row.querySelector(`input[name$="-${FORMSET_MAIN_FIELD}"]`);
        if (main) main.checked = false;
        row.classList.add("d-none");
        refresh();
        return;
      }
      if (target.closest(".formset-add")) {
        const index = Number(totalForms.value);
        rows.insertAdjacentHTML("beforeend", template.innerHTML.replaceAll("__prefix__", index));
        totalForms.value = index + 1;
        refresh();
        rows.lastElementChild.querySelector("input[type=text], input[type=email]")?.focus();
      }
    });

    refresh();
  });
};
