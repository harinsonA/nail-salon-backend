/* Gráfico "Servicios más solicitados" — bar horizontal (indexAxis: y). */
(function () {
  var LABEL_GAP = 4;

  var labelsAboveBars = {
    id: "labelsAboveBars",
    afterDatasetsDraw: function (chart) {
      var ctx = chart.ctx;
      var meta = chart.getDatasetMeta(0);
      ctx.save();
      ctx.font = "12px " + Chart.defaults.font.family;
      ctx.fillStyle = Chart.defaults.color;
      ctx.textAlign = "left";
      ctx.textBaseline = "bottom";
      meta.data.forEach(function (bar, index) {
        var props = bar.getProps(["y", "height"], true);
        ctx.fillText(
          chart.data.labels[index],
          chart.chartArea.left,
          props.y - props.height / 2 - LABEL_GAP
        );
      });
      ctx.restore();
    },
  };

  DashboardCore.register(
    "chart-top-services",
    "bar",
    {
      indexAxis: "y",
      layout: { padding: { top: 8 } },
      datasets: { bar: { barPercentage: 0.45, categoryPercentage: 1, maxBarThickness: 18 } },
      scales: {
        x: { beginAtZero: true, ticks: { precision: 0 } },
        y: { ticks: { display: false }, grid: { display: false } },
      },
      plugins: { legend: { display: false } },
    },
    [labelsAboveBars]
  );
})();
