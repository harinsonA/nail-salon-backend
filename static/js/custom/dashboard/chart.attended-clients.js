/* Gráfico "Clientes atendidos" — line, últimos 6 meses.
   2 series: citas atendidas y clientes únicos. La URL del endpoint se lee
   desde data-url del canvas (resuelta con {% url %} en el template). */
$(function () {
  DashboardCore.loadChart("chart-attended-clients", "line");
});
