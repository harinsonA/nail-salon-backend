/* Gráfico "Servicios más solicitados" — bar horizontal (indexAxis: y). */
$(function () {
  DashboardCore.loadChart("chart-top-services", "bar", null, {
    indexAxis: "y",
    scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
    plugins: { legend: { display: false } },
  });
});
