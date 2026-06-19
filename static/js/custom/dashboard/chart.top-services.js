/* Gráfico "Servicios más solicitados" — bar horizontal (indexAxis: y). */
DashboardCore.register("chart-top-services", "bar", {
  indexAxis: "y",
  scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
  plugins: { legend: { display: false } },
});
