const initializeMonthPickers = (settings = {}) => {
  const { selector = ".monthpicker" } = settings;
  $(selector).datepicker({
    language: "es",
    minViewMode: 1, // o "months"
    startView: 1, // o "months"
    format: "MM yyyy", // o "mm/yyyy"
    autoclose: true,
  });
};

const initializeDatePickers = (settings = {}) => {
  const { selector = ".datepicker" } = settings;
  $(selector).datepicker({
    language: "es",
    format: "dd/mm/yyyy",
    autoclose: true,
  });
};
