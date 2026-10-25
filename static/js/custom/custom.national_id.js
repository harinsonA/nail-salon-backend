$(document).on("change", ".modal select[data-national-id-types]", ({ target }) => {
  const typeSelect = target.closest("form").querySelector(target.dataset.nationalIdTypeField);
  const types = JSON.parse(target.dataset.nationalIdTypes)[target.value] || [];
  const emptyOption = typeSelect.options[0];
  typeSelect.replaceChildren(emptyOption, ...types.map(([value, label]) => new Option(label, value)));
  typeSelect.value = "";
  typeSelect.disabled = types.length === 0;
});
