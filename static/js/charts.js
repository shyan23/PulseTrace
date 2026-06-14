/* sentiment timeline chart */
function renderSentChart(cs) {
  const labels = cs.map(c => String(c.label || "?").slice(0, 18));
  const pos = cs.map(c => Math.round((c.sentiment && c.sentiment.pos || 0) * 100));
  const neu = cs.map(c => Math.round((c.sentiment && c.sentiment.neu || 0) * 100));
  const neg = cs.map(c => Math.round((c.sentiment && c.sentiment.neg || 0) * 100));
  const ctx = $("#sentChart");
  if (sentChart) sentChart.destroy();
  // Sentiment is semantic, not branding: positive=green, neutral=gray, negative=red.
  const text = cssVar("--text"), muted = cssVar("--muted"), grid = cssVar("--border");
  sentChart = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets: [
      { label: "Positive", data: pos, backgroundColor: cssVar("--pos") },
      { label: "Neutral", data: neu, backgroundColor: cssVar("--neu") },
      { label: "Negative", data: neg, backgroundColor: cssVar("--neg") },
    ]},
    options: {
      responsive: true,
      // Click a colored segment → open that cluster's posts filtered to that
      // sentiment (e.g. the green slice = read the positive posts).
      onClick: (_e, els) => {
        if (!els.length) return;
        const el = els[0];
        const c = cs[el.index];
        if (!c) return;
        const stance = ["pos", "neu", "neg"][el.datasetIndex] || "all";
        openClusterDrawer(c.id, stance);
      },
      onHover: (e, els) => {
        if (e.native && e.native.target) e.native.target.style.cursor = els.length ? "pointer" : "default";
      },
      plugins: {
        legend: { labels: { color: text } },
        tooltip: { callbacks: {
          label: (i) => i.dataset.label + ": " + i.parsed.y + "% (click to read)",
        } },
      },
      scales: {
        x: { stacked: true, ticks: { color: muted }, grid: { color: grid } },
        y: { stacked: true, ticks: { color: muted }, grid: { color: grid }, max: 100 },
      },
    },
  });
}
