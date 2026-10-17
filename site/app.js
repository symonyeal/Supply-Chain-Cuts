// Draws site/data.js (written by analysis/build_site.py). Each section draws when it comes into
// view and redraws when a control it reads changes. Colours are the theme tokens in style.css.
"use strict";

const D = window.DATA, $ = (id) => document.getElementById(id);
const css = getComputedStyle(document.documentElement), tok = (k) => css.getPropertyValue("--" + k).trim();
const T = Object.fromEntries(["bg", "text", "text-2", "muted", "border", "context", "accent", "negative", "font"].map((k) => [k, tok(k)]));
const CAT = [1, 2, 3, 4, 5, 6].map((i) => tok("c" + i));
const AX = { gridcolor: T.border, zerolinecolor: T.muted, linecolor: T.muted, automargin: true, tickfont: { color: T["text-2"] } };
const pct = (x, d = 1) => x == null ? "–" : (100 * x).toFixed(d) + "%";
const fmt = (x, d = 3) => x == null ? "–" : (+x).toFixed(d);
const N = D.nodes, name = (v) => `${N.country[v]} ${N.product[v]}`;

function plot(id, data, layout = {}) {
  const narrow = innerWidth < 700;
  Plotly.react($(id), data, {
    height: layout.height || (narrow ? 360 : 460), paper_bgcolor: T.bg, plot_bgcolor: T.bg, colorway: CAT, showlegend: false,
    font: { family: T.font, color: T.text, size: 13 }, margin: { t: 16, r: narrow ? 24 : 48, b: 48, l: 56 },
    hoverlabel: { bgcolor: T.bg, bordercolor: T.border, font: { color: T.text } },
    ...layout, xaxis: { ...AX, ...layout.xaxis }, yaxis: { ...AX, ...layout.yaxis },
  }, { responsive: true, displaylogo: false });
}

// Published values; every control writes S and marks the sections that read it.
const PUB = { alpha: "0.25", DJ: "12", h: "0", sigma: "0", L: "6" };
const S = { ...PUB, q: "" };
const key = () => `a${S.alpha}_h${S.h}_s${S.sigma}_L${S.sigma === "0" ? "6" : S.L}_D${S.DJ}`;
const cfg = () => D.configs[key()];

function seg(id, k, values, label, after) {
  const el = $(id);
  el.innerHTML = values.map((v) => `<button data-v="${v}">${label(v)}</button>`).join("");
  const sync = () => el.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.v === S[k]));
  el.onclick = (e) => { if (e.target.dataset.v == null) return; S[k] = e.target.dataset.v; sync(); after(); };
  el.sync = sync; sync();
}

const cutText = (cut, B = D) => cut.map(([v, d]) => `${B.nodes.country[v]} ${B.nodes.product[v]} <span class="tag ${B.nodes.basis[v]}">${B.nodes.basis[v]}</span> ${d} mo`).join(" + ");
function cutRows(B, c, q = "") {
  return c.cuts.map((cut, i) => ({ cut, phi: c.phi[i], a: c.attribution[i], pred: c.predecessors[i] }))
    .filter((r) => !q || r.cut.some(([v]) => `${B.nodes.country[v]} ${B.nodes.product[v]}`.toLowerCase().includes(q)))
    .sort((x, y) => y.a - x.a || x.cut.length - y.cut.length);
}
function cutTable(B, rows) {
  return `<thead><tr><th>Losses (node, basis, minimum duration)</th><th class="num">Shortfall φ/Σd</th>` +
    `<th>Shorter-outage witnesses</th><th class="num">P(S ⊆ Z)/L</th></tr></thead><tbody>` + rows.map((r) =>
      `<tr><td class="wrap">${cutText(r.cut, B)}</td><td class="num">${pct(r.phi)}</td><td class="wrap">` +
      r.pred.map(([v, d, phi]) => `${B.nodes.country[v]} ${B.nodes.product[v]} → ${d} mo: ${pct(phi, 4)}`).join("<br>") +
      `</td><td class="num">${pct(r.a)}</td></tr>`).join("") + `</tbody>`;
}

const SECTIONS = {
  cuts() {
    const c = cfg(), q = S.q.trim().toLowerCase();
    $("cuts-summary").textContent = `${c.cuts.length} minimal cut sets of at most three losses; ` +
      `${c.cuts.filter((x) => x.length === 1).length} singletons. L = ${pct(c.L)}, U = ${pct(c.U)}.` +
      (c.U === 1 ? " U reaches 100% because the bound adds every state with more than three losses; it does not assert certain failure." : "");
    $("cuts-table").innerHTML = cutTable(D, cutRows(D, c, q));
  },
  layers() {
    const P = D.layers.product, x = [], base = {};
    const traces = ["production", "trade", "imputed"].map((b, j) => {
      const xs = [], ys = [], txt = [];
      P.forEach((p) => N.product.forEach((q, v) => {
        if (q === p && N.basis[v] === b) { xs.push(p); ys.push(N.years[v]); txt.push(`${N.country[v]}: ${fmt(N.years[v], 3)} y/y, ${pct(N.share[v])} of layer, ${N.source[v]}`); }
      }));
      return { type: "bar", x: xs, y: ys, name: b, marker: { color: CAT[j], line: { color: T.bg, width: 0.5 } }, text: txt,
        hovertemplate: "%{text}<extra>" + b + "</extra>", textposition: "none" };
    });
    plot("layers-chart", traces, { barmode: "stack", showlegend: true, legend: { orientation: "h", y: 1.08 },
      yaxis: { type: "log", title: { text: "supply, years of requirement per year (log)" }, range: [Math.log10(0.5), Math.log10(200)] },
      shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 1, y1: 1, line: { color: T.negative, dash: "dot", width: 1.5 } }],
      annotations: [{ xref: "paper", x: 1, y: Math.log10(1), yanchor: "bottom", xanchor: "right", text: "requirement = 1", showarrow: false, font: { color: T.negative, size: 11 } }] });
  },
  risk() {
    const A = ["0.1", "0.25"], E = D.estimates;
    const xs = A.map((a) => "α = " + a);
    const tr = [
      { type: "scatter", mode: "markers", x: xs, y: A.map((a) => D.configs[`a${a}_h0_s0_L6_D12`].L), name: "L (exact)",
        marker: { color: T.text, symbol: "line-ew-open", size: 28, line: { width: 3 } }, hovertemplate: "L = %{y:.3f}<extra></extra>" },
      { type: "scatter", mode: "markers", x: xs, y: A.map((a) => E[a].residual.estimate), name: "L + residual",
        error_y: { type: "data", symmetric: false, array: A.map((a) => E[a].residual.ci95[1] - E[a].residual.estimate), arrayminus: A.map((a) => E[a].residual.estimate - E[a].residual.ci95[0]), color: T.accent },
        customdata: A.map((a) => E[a].residual.L),
        marker: { color: T.accent, size: 10 }, hovertemplate: "L + residual = %{y:.3f}; L = %{customdata:.3f}<extra></extra>" },
      { type: "scatter", mode: "markers", x: xs, y: A.map((a) => E[a].MC.estimate), name: "crude Monte Carlo",
        error_y: { type: "data", symmetric: false, array: A.map((a) => E[a].MC.ci95[1] - E[a].MC.estimate), arrayminus: A.map((a) => E[a].MC.estimate - E[a].MC.ci95[0]), color: T.context },
        marker: { color: T.context, size: 9, symbol: "diamond" }, hovertemplate: "MC = %{y:.3f}<extra></extra>" },
      { type: "scatter", mode: "markers", x: ["α = 0.25, quotas and bans only"], y: [D.hard.residual.estimate], name: "quotas and bans only",
        error_y: { type: "data", symmetric: false, array: [D.hard.residual.ci95[1] - D.hard.residual.estimate], arrayminus: [D.hard.residual.estimate - D.hard.residual.ci95[0]], color: CAT[2] },
        marker: { color: CAT[2], size: 10 }, hovertemplate: "%{y:.3f}, L = " + fmt(D.hard.L) + "<extra>post hoc; L + residual</extra>" },
    ];
    plot("risk-chart", tr, { showlegend: true, legend: { orientation: "h", y: 1.1 }, yaxis: { title: { text: "annual P(failure), scenario" }, range: [0, 1], tickformat: ".0%" } });
  },
  pv() {
    if (!D.pv) return;
    const k = key(), c = D.pv.configs[k], j = D.joint && D.joint.configs[k];
    const e = S.h === "0" && S.sigma === "0" && S.DJ === "12" && D.pv.estimates[S.alpha];
    $("pv-summary").textContent = `PV alone: ${c.cuts.length} minimal cut sets, ${c.cuts.filter((x) => x.length === 1).length} singletons; ` +
      `L = ${pct(c.L)}, U = ${pct(c.U)}.` + (e ? ` L + residual ${pct(e.residual.estimate)} [${pct(e.residual.ci95[0])}, ${pct(e.residual.ci95[1])}].` : "") +
      (j ? ` Shared Li-ion and PV network: ${j.cuts.length} cut sets, ${j.cuts.filter((x) => x.length === 1).length} singletons, L = ${pct(j.L)}.` :
        " Shared-network calculations are available only for α = 10% or 25%, h = σ = 0.");
    $("pv-table").innerHTML = cutTable(D.pv, cutRows(D.pv, c));
  },
  attribution() {
    const by = cfg().country_union, ks = Object.keys(by).sort((a, b) => by[a] - by[b]);
    $("attr-summary").textContent = `Selected configuration: α = ${S.alpha}, D ≤ ${S.DJ} months, h = ${S.h}, σ = ${S.sigma}, ramp ${S.L} months. ` +
      (ks.length ? `L = ${pct(cfg().L)}; country shares overlap.` : "No enumerated cut occurs, so L = 0 and attribution is undefined.");
    plot("attr-chart", [{ type: "bar", orientation: "h", y: ks, x: ks.map((k) => by[k]), marker: { color: ks.map((k) => k === "CHN" ? T.accent : T.context) },
      hovertemplate: "%{y}: %{x:.1%} of L<extra></extra>" }], { height: 120 + 26 * ks.length, xaxis: { tickformat: ".0%", range: [0, 1], title: { text: "P(a cut set with the country occurs)/L (shares overlap)" } } });
  },
  sensitivity() {
    const rows = D.sensitivity, x = [], y = [];
    rows.forEach((r) => { x.push(Math.min(...r.values), Math.max(...r.values), null); y.push(r.label, r.label, null); });
    plot("sens-chart", [{ type: "scatter", mode: "lines+markers", x, y,
      line: { color: T.accent, width: 3 }, marker: { color: T.accent, size: 8 },
      hovertemplate: "%{y}: L = %{x:.3%}<extra></extra>" }], {
      height: 390, margin: { t: 16, r: 24, b: 56, l: innerWidth < 700 ? 186 : 224 },
      xaxis: { range: [0, 0.65], tickformat: ".0%", title: { text: "annual L<br>scenario" } },
      yaxis: { autorange: "reversed" },
      shapes: [{ type: "line", x0: head.L, x1: head.L, yref: "paper", y0: 0, y1: 1, line: { color: T.context, dash: "dot", width: 1 } }],
    });
  },
};

const dirty = new Set(Object.keys(SECTIONS)), seen = new Set();
function flush() { for (const id of dirty) if (seen.has(id)) { dirty.delete(id); SECTIONS[id](); } }
function mark(...ids) { ids.forEach((id) => dirty.add(id)); flush(); }

function fill() {
  document.querySelectorAll("[data-f]").forEach((el) => { const f = FACT[el.dataset.f]; el.textContent = f == null ? "–" : f; });
}

const head = D.configs["a0.25_h0_s0_L6_D12"], t = D.tests;
const FACT = {
  ncuts: head.cuts.length, nsingle: head.cuts.filter((x) => x.length === 1).length,
  singles: head.cuts.filter((x) => x.length === 1).map(([[v]]) => N.product[v].replace("_", " ")).join(", "),
  L: pct(head.L), U: pct(head.U), estimate: pct(D.estimates["0.25"].residual.estimate), MC: pct(D.estimates["0.25"].MC.estimate),
  estimateLo: pct(D.estimates["0.25"].residual.ci95[0]), estimateHi: pct(D.estimates["0.25"].residual.ci95[1]),
  hard: pct(D.hard.residual.estimate), hardL: pct(D.hard.L), rho: fmt(D.meta.rho, 2),
  sump: fmt(N.p.reduce((a, b) => a + b, 0), 1), w12: pct(D.meta.durations.weights[2], 0),
  d1m: fmt(D.meta.D1.model_log_loss, 3), d1c: fmt(D.meta.D1.constant_log_loss, 3),
  mid: pct(t.H2_china_midstream_share_of_L.midstream),
  rhoHHI: fmt(t.A1_spearman.hhi, 2), rhoTop: fmt(t.A1_spearman.top_share, 2),
  revision: D.meta.revision.slice(0, 7), lock: D.meta.lock.slice(0, 12), run: D.meta.run,
  runs: [...[D, D.pv, D.joint].filter(Boolean).map((b) => b.meta.run), D.severity && D.severity.run].filter(Boolean).join(", "),
  L10: pct(D.configs["a0.1_h0_s0_L6_D12"].L), n10: D.configs["a0.1_h0_s0_L6_D12"].cuts.length,
  n6: D.configs["a0.25_h0_s0_L6_D6"].cuts.length,
  chnU: pct(D.attribution.country_union.CHN, 0), codU: pct(D.attribution.country_union.COD, 0),
};
fill();

$("facts").innerHTML = [[FACT.nsingle, "single losses that each stop more than 25% of two years' cells, if they last a year"],
  [t.robust_singletons.length, "of them hold under every capacity-basis, re-export and chemistry test"],
  [FACT.ncuts, "minimal cut sets of up to three losses (α = 25%)"], [FACT.L, "exact lower bound L on annual failure, scenario"],
  [FACT.estimate, "L plus residual estimate, scenario"]].map(([v, l]) => `<div><b>${v}</b><span>${l}</span></div>`).join("");

const ctl = [["c-alpha", "alpha", ["0.1", "0.25", "0.5"], (v) => `α = ${v}`], ["c-dj", "DJ", ["3", "6", "12"], (v) => `D ≤ ${v} mo`],
  ["c-h", "h", ["0", "1", "3"], (v) => `h = ${v} mo`], ["c-sigma", "sigma", ["0", "0.1", "0.5"], (v) => `σ = ${v}`],
  ["c-L", "L", ["6", "24"], (v) => `L = ${v} mo`]];
ctl.forEach(([id, k, vs, lab]) => seg(id, k, vs, lab, () => mark("cuts", "pv", "attribution")));
$("c-reset").onclick = () => { Object.assign(S, PUB); ctl.forEach(([id]) => $(id).sync()); mark("cuts", "pv", "attribution"); };
$("c-q").oninput = (e) => { S.q = e.target.value; mark("cuts"); };

if (D.severity) {
  const interval = (e) => `${pct(e.estimate, 3)} [${pct(e.ci95[0], 3)}, ${pct(e.ci95[1], 3)}]`;
  $("scenario-table").innerHTML = `<thead><tr><th>Network</th><th>Full outage (registered)</th><th>Quotas and bans (post hoc)</th><th>Severity study (registered S3)</th></tr></thead><tbody>` +
    Object.entries(D.severity.sectors).map(([s, x]) => `<tr><td>${s}</td>` +
      `<td>${interval(x.full_outage)}; L = ${pct(x.full_outage.L, 3)}</td>` +
      `<td>${interval(x.hard.residual)}; L = ${pct(x.hard.L, 3)}</td>` +
      `<td>${x.same_as_full ? interval(x.full_outage) + "; same law and estimator as full outage" : interval(x.scenarios.central)}. ` +
      `${pct(x.unidentified_onset_share, 0)} of sampled onsets use unidentified full-loss fallbacks. ` +
      `Paired reduction ${pct(x.scenarios.central.reduction, 3)} [${pct(x.scenarios.central.reduction_ci95[0], 3)}, ${pct(x.scenarios.central.reduction_ci95[1], 3)}].</td></tr>`).join("") + `</tbody>`;
  $("severity-table").innerHTML = `<thead><tr><th>Measure</th><th class="num">Isolated events</th><th>Export loss, baseline-volume units (95% interval)</th><th>Identification</th></tr></thead><tbody>` +
    Object.entries(D.severity.table).map(([m, x]) => `<tr><td>${m}</td><td class="num">${x.events}</td>` +
      `<td>${x.loss == null ? "not estimable" : `${fmt(x.loss)} [${fmt(x.loss_ci95[0])}, ${fmt(x.loss_ci95[1])}]`}</td>` +
      `<td>${x.identified ? "identified under stated assumptions" : "insufficient isolated events"}${x.pretrend ? "; pretrend detected" : ""}</td></tr>`).join("") + `</tbody>`;
}

$("tests-table").innerHTML = `<thead><tr><th>Leaf</th><th>Kill condition</th><th>Result</th><th>Verdict</th></tr></thead><tbody>` +
  D.testRows.map((r) => `<tr><td>${r[0]}</td><td class="wrap">${r[1]}</td><td class="wrap">${r[2]}</td><td class="verdict ${r[3].startsWith("killed") ? "killed" : ""}">${r[3]}</td></tr>`).join("") + `</tbody>`;
$("haz-table").innerHTML = `<thead><tr><th>Country</th><th class="num">Nodes</th><th class="num">GDACS alert years / 13</th><th>Country-wide loss that fails (fraction, months)</th></tr></thead><tbody>` +
  D.hazards.filter((r) => r.fails_at.length).map((r) => `<tr><td>${r.country}</td><td class="num">${r.nodes}</td><td class="num">${r.alert_years}</td><td>${r.fails_at.map(([f, d]) => `${f} × ${d}`).join(", ")}</td></tr>`).join("") + `</tbody>`;

const io = new IntersectionObserver((es) => {
  es.forEach((e) => (e.isIntersecting ? seen.add(e.target.id) : seen.delete(e.target.id)));
  flush();
}, { rootMargin: "400px 0px" });
Object.keys(SECTIONS).forEach((id) => io.observe($(id)));
