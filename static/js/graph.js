/* cytoscape topic graph + color helpers + orbital spin */
if (window.cytoscapeFcose) cytoscape.use(window.cytoscapeFcose);

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
function hexToRgb(h) {
  h = h.replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
function sentimentColor(s) {
  s = s || {};
  const pos = +s.pos || 0, neu = +s.neu || 0, neg = +s.neg || 0;
  const total = pos + neu + neg || 1;
  const [cp, cu, cn] = [cssVar("--pos"), cssVar("--neu"), cssVar("--neg")].map(hexToRgb);
  const mix = [0, 1, 2].map((i) =>
    Math.round((cp[i] * pos + cu[i] * neu + cn[i] * neg) / total));
  return `rgb(${mix[0]},${mix[1]},${mix[2]})`;
}

function sizeOf(ele) { return 26 + Math.sqrt(ele.data("size") || 0) * 10; }

function sentParts(s) {
  s = s || {};
  const pos = +s.pos || 0, neu = +s.neu || 0, neg = +s.neg || 0;
  const total = pos + neu + neg || 1;
  return { pos, neu, neg,
    pPos: Math.round((pos / total) * 100),
    pNeu: Math.round((neu / total) * 100),
    pNeg: Math.round((neg / total) * 100) };
}
function dominantMood(s) {
  const p = sentParts(s), m = Math.max(p.pos, p.neu, p.neg);
  if (m === p.pos && p.pos > p.neg) return "mostly positive";
  if (m === p.neg && p.neg > p.pos) return "mostly negative";
  return "mixed / neutral";
}

let _graphTip = null;
function tipEl() { return _graphTip || (_graphTip = document.getElementById("graphTip")); }
function gtRow(...kids) { return elem("div", { class: "gt-row" }, ...kids); }
function showTip(node, x, y) {
  const t = tipEl(); if (!t) return;
  clearNode(t); t.appendChild(node);
  t.style.left = x + "px"; t.style.top = y + "px"; t.hidden = false;
}
function hideTip() { const t = tipEl(); if (t) t.hidden = true; }

function nodeTip(d) {
  const p = sentParts(d.sentiment);
  return elem("div", null,
    elem("div", { class: "gt-title" }, d.label),
    gtRow(elem("span", null, "Posts"), elem("b", null, String(d.size))),
    gtRow(elem("span", null, "Mood"), elem("b", null, dominantMood(d.sentiment))),
    gtRow(elem("span", null, `😊 ${p.pPos}%`),
          elem("span", null, `😐 ${p.pNeu}%`),
          elem("span", null, `😞 ${p.pNeg}%`)));
}
function edgeTip(a, b, w) {
  return elem("div", null,
    elem("div", { class: "gt-title" }, "Related talking points"),
    gtRow(elem("span", null, a)),
    gtRow(elem("span", null, b)),
    gtRow(elem("span", null, "Similarity"), elem("b", null, Math.round(w * 100) + "%")));
}

// Screen-reader summary only: a network graph is opaque to assistive tech, so
// we restate its gist as text (WCAG screen-reader-summary). No visual list.
function buildGraphAux(rawNodes, edges) {
  const sumEl = document.getElementById("graphSummary");
  if (!sumEl) return;
  if (!rawNodes.length) {
    sumEl.textContent = "No talking points yet. Run a topic to build the graph.";
    return;
  }
  const top = rawNodes.slice().sort((a, b) => (b.data.size || 0) - (a.data.size || 0))[0].data;
  sumEl.textContent = `Topic graph with ${rawNodes.length} talking points and `
    + `${edges.length} connection${edges.length === 1 ? "" : "s"} between related ones. `
    + `Largest: "${top.label}", ${top.size} posts, ${dominantMood(top.sentiment)}.`;
}

function lightenRgb(rgb, amt) {
  const m = /rgb\((\d+),\s*(\d+),\s*(\d+)\)/.exec(rgb || "");
  if (!m) return rgb;
  const mix = [1, 2, 3].map((i) => Math.round(+m[i] + (255 - +m[i]) * amt));
  return `rgb(${mix[0]},${mix[1]},${mix[2]})`;
}

let graphSpin = null;
function stopGraphSpin() {
  if (graphSpin) { cancelAnimationFrame(graphSpin.raf); graphSpin = null; }
}
// Subtle, continuous orbital rotation so the topic graph reads as "alive".
// Operates on model positions (cheap for a handful of nodes), pauses during
// interaction, and bails out under prefers-reduced-motion.
function startGraphSpin() {
  stopGraphSpin();
  if (!cy || cy.nodes().length < 2) return;
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const nodes = cy.nodes();
  let cx = 0, cyc = 0;
  nodes.forEach((n) => { const p = n.position(); cx += p.x; cyc += p.y; });
  cx /= nodes.length; cyc /= nodes.length;
  const base = nodes.map((n) => {
    const p = n.position(), dx = p.x - cx, dy = p.y - cyc;
    return { n, r: Math.hypot(dx, dy), theta: Math.atan2(dy, dx) };
  });
  const SPEED = 0.00005; // rad/ms -> ~one revolution per ~125s
  const state = { paused: false, raf: 0, angle: 0, last: performance.now() };
  graphSpin = state;
  function frame(now) {
    if (graphSpin !== state || !cy) return;
    const dt = now - state.last; state.last = now;
    if (!state.paused) {
      state.angle += SPEED * dt;
      const a = state.angle;
      cy.batch(() => base.forEach((b) => {
        const t = b.theta + a;
        b.n.position({ x: cx + b.r * Math.cos(t), y: cyc + b.r * Math.sin(t) });
      }));
    }
    state.raf = requestAnimationFrame(frame);
  }
  state.raf = requestAnimationFrame(frame);
}

// A run's clusters.json may not be flushed (or the request may transiently fail
// /401) at the instant the "done" curtain lifts. The backend always returns the
// nodes once they exist, so a draw that comes back empty is retried a few times
// before we accept it as a genuinely empty run and clear the canvas.
async function drawGraph(rid, _attempt = 0) {
  if (_attempt === 0) window._graphRid = rid;       // newest request wins
  let j = { nodes: [], edges: [] };
  try {
    const r = await fetch("/graph?run_id=" + encodeURIComponent(rid),
                          { credentials: "same-origin" });
    if (r.ok) j = await r.json();
  } catch (e) { /* network hiccup → treated as empty, retried below */ }

  if (window._graphRid !== rid) return;             // superseded by a newer run
  const incoming = j.nodes || [];
  { const g = document.getElementById("graph");
    console.log("[graph] rid=" + rid + " attempt=" + _attempt
      + " nodes=" + incoming.length
      + " box=" + (g ? g.clientWidth + "x" + g.clientHeight : "no-el")); }
  if (!incoming.length && _attempt < 6) {
    setTimeout(() => { drawGraph(rid, _attempt + 1).catch(() => {}); }, 800);
    return;
  }

  const nodes = incoming.map((n) => {
    const color = sentimentColor(n.data.sentiment);
    return { data: { ...n.data, _color: color, _hi: lightenRgb(color, 0.55) } };
  });
  const edges = j.edges || [];
  const hint = $("#graphHint");
  if (hint) hint.classList.toggle("hidden", nodes.length > 0);
  buildGraphAux(nodes, edges);
  hideTip();
  const labelById = {};
  nodes.forEach((n) => (labelById[n.data.id] = n.data.label));
  stopGraphSpin();
  if (cy) cy.destroy();
  if (!nodes.length) {
    cy = null;
    if (window._graphRO) { window._graphRO.disconnect(); window._graphRO = null; }
    return;
  }

  const txt = cssVar("--text"), muted = cssVar("--muted"),
        accent = cssVar("--accent2"), panel = cssVar("--panel");

  cy = cytoscape({
    container: $("#graph"),
    elements: [...nodes, ...edges],
    minZoom: 0.2, maxZoom: 3, pixelRatio: "auto",
    style: [
      { selector: "node", style: {
          "label": "data(label)", "color": txt, "font-size": "12px",
          "font-weight": 600, "font-family": "Inter, sans-serif",
          "background-color": "data(_color)",
          "background-fill": "radial-gradient",
          "background-gradient-stop-colors": (ele) => ele.data("_hi") + " " + ele.data("_color"),
          "background-gradient-stop-positions": "0% 100%",
          "border-width": 2, "border-color": panel, "border-opacity": 0.9,
          "width": sizeOf, "height": sizeOf,
          "text-valign": "bottom", "text-margin-y": 6,
          "text-max-width": "120px", "text-wrap": "ellipsis",
          "text-background-color": panel, "text-background-opacity": 0.55,
          "text-background-padding": "2px", "text-background-shape": "roundrectangle",
          "overlay-opacity": 0, "transition-property": "opacity border-color border-width",
          "transition-duration": "0.18s",
      }},
      { selector: "edge", style: {
          "width": (ele) => 1.2 + (ele.data("weight") || 0) * 5,
          "line-color": muted, "opacity": (ele) => 0.15 + (ele.data("weight") || 0) * 0.45,
          "curve-style": "straight",
      }},
      { selector: "node.faded", style: { "opacity": 0.18 } },
      { selector: "edge.faded", style: { "opacity": 0.04 } },
      { selector: "node.hl", style: { "border-color": accent, "border-width": 3 } },
      { selector: "edge.hl", style: { "line-color": accent, "opacity": 0.85 } },
      { selector: "node:selected", style: { "border-color": accent, "border-width": 4 } },
    ],
    layout: {
      name: window.cytoscapeFcose ? "fcose" : "cose",
      animate: true, animationDuration: 600, padding: 40,
      nodeSeparation: 140, idealEdgeLength: 130, nodeRepulsion: 9000,
    },
  });

  cy.on("mouseover", "node", (e) => {
    const nb = e.target.closedNeighborhood();
    cy.elements().addClass("faded");
    nb.removeClass("faded").addClass("hl");
    if (graphSpin) graphSpin.paused = true;
    const p = e.target.renderedPosition();
    showTip(nodeTip(e.target.data()), p.x, p.y - sizeOf(e.target) / 2);
  });
  cy.on("mouseout", "node", () => {
    cy.elements().removeClass("faded hl");
    if (graphSpin) { graphSpin.last = performance.now(); graphSpin.paused = false; }
    hideTip();
  });
  cy.on("mouseover", "edge", (e) => {
    e.target.addClass("hl");
    const d = e.target.data(), m = e.target.midpoint(), z = cy.zoom(), pan = cy.pan();
    showTip(edgeTip(labelById[d.source], labelById[d.target], d.weight || 0),
            m.x * z + pan.x, m.y * z + pan.y);
  });
  cy.on("mouseout", "edge", (e) => { e.target.removeClass("hl"); hideTip(); });
  cy.on("grab", "node", () => { if (graphSpin) graphSpin.paused = true; hideTip(); });
  // Dragging reseats nodes, so rebuild the orbit from their new positions.
  cy.on("free", "node", () => startGraphSpin());
  cy.on("layoutstop", () => { cy.fit(undefined, 40); startGraphSpin(); });

  $("#gZoomIn").onclick = () => cy && cy.zoom({ level: cy.zoom() * 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  $("#gZoomOut").onclick = () => cy && cy.zoom({ level: cy.zoom() / 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  $("#gFit").onclick = () => cy && cy.fit(undefined, 40);

  // Cytoscape measures its container at init. When the panel is hidden or not yet
  // laid out (live dashboard reveal, SPA view switch), it renders blank until the
  // viewport is recomputed. Resize + refit whenever #graph actually gains size.
  const gc = $("#graph");
  if (window._graphRO) window._graphRO.disconnect();
  window._graphRO = new ResizeObserver(() => {
    if (cy && gc.clientWidth > 0 && gc.clientHeight > 0) { cy.resize(); cy.fit(undefined, 40); }
  });
  window._graphRO.observe(gc);
}
