/* Gráfico "Ingresos por categoría" — bar vertical multicolor. */
$(function () {
  DashboardCore.loadChart("chart-income-by-category", "bar", null, {
    plugins: { legend: { display: false } },
  });
});
