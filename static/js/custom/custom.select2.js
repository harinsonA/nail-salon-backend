/**
 * Custom Select2 Components
 * Funciones específicas para inicialización de Select2 con estilos personalizados
 * Depende de: select2.min.js, i18n/es.min.js
 */

const initializeSelect2 = (scope) => {
  const $scope = scope ? $(scope) : $(document);

  $scope.find(".form-select-2--custom").each(function () {
    const $el = $(this);

    if ($el.data("select2")) {
      $el.select2("destroy");
    }

    const $modal = $el.closest(".modal");

    $el.select2({
      language: "es",
      width: "100%",
      dropdownParent: $modal.length ? $modal : $(document.body),
    });
  });
};

$(() => {
  initializeSelect2(document);
  $(document).on("show.bs.modal", ".modal", function () {
    initializeSelect2(this);
  });
});

const initializeSelect2Ajax = (element, config = {}) => {
  const { ajax: ajaxConfig = {}, ...settings } = config;
  $(element).select2({
    language: "es",
    width: "100%",
    placeholder: "Seleccione una opción",
    ajax: {
      dataType: "json",
      processResults: (data) => data,
      ...ajaxConfig,
    },
    ...settings,
  });
};
