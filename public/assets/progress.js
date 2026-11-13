(() => {
  if (typeof document === "undefined" || !window.ICCharts) return;
  const parse = (value) => {
    try { return JSON.parse(value || "[]"); } catch (_) { return []; }
  };
  document.querySelectorAll("[data-progress-chart]").forEach((canvas) => {
    const type = canvas.dataset.progressChart;
    const labels = parse(canvas.dataset.labels);
    const values = parse(canvas.dataset.values);
    if (!Array.isArray(labels) || !Array.isArray(values)) return;
    if (type === "radar") window.ICCharts.radar(canvas, labels, values);
    if (type === "line") window.ICCharts.line(canvas, labels, values, "%");
    if (type === "columns") window.ICCharts.columns(canvas, labels, values, "h");
  });
})();
