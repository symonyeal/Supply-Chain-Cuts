/* Plain-language overview of the saved model results.
   D: saved results; C: 2025 mineral context; B: network block; c: configuration; v: node index.
   R: reference settings (25% shortfall, outages up to 12 months, no stock, no spare capacity, flexible battery recipes).
   The page selects saved results and states them; it computes nothing the model computes. */
"use strict";
(() => {
  const D = window.DATA, C = window.CONTEXT, $ = id => document.getElementById(id);
  const esc = x => String(x ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const pct = x => `${Math.round(100 * x)}%`;
  const place = c => window.LABELS.place(c, C.meta.countries[c]), product = window.LABELS.product;
  const words = ["no","one","two","three","four","five","six","seven","eight","nine","ten"], word = n => words[n] ?? String(n);
  const R = "a0.25_h0_s0_L6_D12", alpha = 0.25;
  const sectors = {
    liion: {name:"Batteries", B:D.choice, chain:[["Mining",["mine_li","mine_co","mine_ni","graphite"]],["Refining",["li_carbonate","refined_co"]],
      ["Battery parts",["pcam","cam","aam"]],["Finished product",["cell"]]]},
    pv: {name:"Solar panels", B:D.pv, chain:[["Refining",["polysilicon"]],["Parts",["wafer","pv_cell"]],["Finished product",["module"]]]},
  };
  const hints = {mine_li:"dug from the ground",mine_co:"dug from the ground",mine_ni:"dug from the ground",graphite:"mined and synthetic",
    li_carbonate:"refined lithium",refined_co:"chemical-grade cobalt",pcam:"metal mix for the cathode",cam:"the battery's positive side",
    aam:"the battery's negative side",cell:"finished cells",polysilicon:"purified silicon",wafer:"thin silicon slices",pv_cell:"cells before assembly",module:"finished panels"};

  // Single-loss failures in configuration `key`: node, duration, shortfall, and its shorter-outage check.
  const singles = (B, key) => { const c = B.configs[key];
    return c.cuts.flatMap((cut, i) => cut.length === 1 ? [{v:cut[0][0], d:cut[0][1], phi:c.phi[i], shorter:c.predecessors[i][0]}] : []); };
  const leader = (N, p) => N.product.map((q, v) => q === p ? v : -1).filter(v => v >= 0).reduce((a, b) => N.share[b] > N.share[a] ? b : a);
  const W = Object.fromEntries(Object.entries(sectors).map(([id, s]) => [id, singles(s.B, R)]));
  const all = Object.values(W).flat();
  const home = id => [...new Set(W[id].map(w => sectors[id].B.nodes.country[w.v]))];
  const nations = [...new Set([...home("liion"), ...home("pv")])];

  const row = (label, sub, track, value, cls = "") =>
    `<div class="row ${cls}"><span class="row-label">${esc(label)}${sub ? `<small>${esc(sub)}</small>` : ""}</span><span class="row-track">${track}</span><span class="row-value">${value}</span></div>`;

  function hero() {
    const short = Object.values(sectors).every(s => s.B.configs["a0.25_h0_s0_L6_D6"].cuts.length === 0);
    const count = word(all.length);
    $("facts").innerHTML = [
      [all.length, `single losses would each cause a major shortfall: ${word(W.liion.length)} for batteries, ${word(W.pv.length)} for solar`],
      [nations.length === 1 ? place(nations[0]) : `${nations.length} countries`, nations.length === 1 ? "is where all of them are. No other country's output matters this much on its own." : "hold these weak points"],
      [short ? "1 year" : "6 months", short ? "is how long an outage must last. Losses of six months or less, even three at once, never cause a major shortfall." : "outages can already cause a major shortfall"],
    ].map(([n, text]) => `<div class="fact"><b>${esc(n)}</b><span>${esc(text)}</span></div>`).join("");
    document.querySelector('[data-fact="lede"]').textContent = `${count[0].toUpperCase() + count.slice(1)} single losses would, and all of them are year-long losses of production in ${nations.map(place).join(" and ")}.`;
  }

  function chain(id) {
    const {B, chain: stages} = sectors[id], N = B.nodes, weak = new Set(W[id].map(w => N.product[w.v]));
    $(`chain-${id}`).innerHTML = stages.map(([stage, products]) => `<p class="row-group">${esc(stage)}</p>` + products.map(p => {
      const v = leader(N, p), hot = weak.has(p);
      return row(product(p), hints[p], `<i class="bar${hot ? " hot" : ""}" style="width:${100 * N.share[v]}%"></i>`,
        `${esc(place(N.country[v]))} <b>${pct(N.share[v])}</b>`, hot ? "weak" : "");
    }).join("")).join("");
  }

  function cobalt() {
    const N = sectors.liion.B.nodes, v = leader(N, "mine_co"), weak = W.liion.some(w => N.product[w.v] === "mine_co");
    $("cobalt-note").textContent = weak ? "" : `Concentration alone does not make a weak point. ${place(N.country[v])} mines ${pct(N.share[v])} of the world's cobalt, but battery makers can shift toward cobalt-free LFP batteries, so losing it does not cause a major shortfall.`;
  }

  function duration() {
    const scale = 0.6, mark = x => `left:${100 * x / scale}%`;
    $("duration").innerHTML = `<div class="row axis"><span class="row-label"></span><span class="row-track"><span class="threshold-label" style="${mark(alpha)}">Major shortfall</span></span><span class="row-value"></span></div>` +
      Object.entries(sectors).map(([id, s]) => `<p class="row-group">${esc(s.name)}</p>` + [...W[id]].sort((a, b) => b.phi - a.phi).map(w => {
        const N = s.B.nodes, [, ds, short] = w.shorter;
        return row(`${place(N.country[w.v])} · ${product(N.product[w.v])}`, "",
          `<i class="threshold" style="${mark(alpha)}"></i><i class="span" style="left:${100 * short / scale}%;width:${100 * (w.phi - short) / scale}%"></i>` +
          `<i class="dot short" style="${mark(short)}" title="${ds}-month loss: ${pct(short)}"></i><i class="dot long" style="${mark(w.phi)}" title="${w.d}-month loss: ${pct(w.phi)}"></i>`,
          `${pct(short)} → <b>${pct(w.phi)}</b>`);
      }).join("")).join("") +
      `<div class="row axis"><span class="row-label"></span><span class="row-track ticks">${[0, .2, .4, .6].map(x => `<span style="${mark(x)}">${pct(x)}</span>`).join("")}</span><span class="row-value"></span></div>`;
    const top = all.reduce((a, b) => b.phi > a.phi ? b : a), Bt = W.liion.includes(top) ? sectors.liion.B : sectors.pv.B;
    $("duration-note").textContent = `The worst single loss, ${place(Bt.nodes.country[top.v])}'s ${product(Bt.nodes.product[top.v]).toLowerCase()}, removes ${pct(top.phi)} of two years' supply. Nobody else has the spare capacity to cover a gap that size, so the shortfall grows with every month the outage lasts.`;
  }

  function policies() {
    const options = [[R,"As modelled (no stockpile, no spare capacity)"],["a0.25_h1_s0_L6_D12","1 month of stockpiled inputs"],["a0.25_h3_s0_L6_D12","3 months of stockpiled inputs"],
      ["a0.25_h0_s0.1_L6_D12","10% spare factory capacity"],["a0.25_h0_s0.5_L6_D12","50% spare factory capacity"]];
    const cell = (id, key) => { const {B} = sectors[id], N = B.nodes, now = new Set(singles(B, key).map(w => w.v)), c = B.configs[key];
      const squares = W[id].map(w => `<i class="unit${now.has(w.v) ? "" : " gone"}" title="${esc(`${place(N.country[w.v])} · ${product(N.product[w.v])}: ${now.has(w.v) ? "still a weak point" : "no longer a weak point"}`)}"></i>`).join("");
      return `<span role="cell" class="policy-cell"><span class="units" aria-hidden="true">${squares}</span><span>${now.size} of ${W[id].length} remain · odds ${pct(c.L)} a year</span></span>`; };
    $("policies").innerHTML = `<div role="row" class="policy-row head"><span role="columnheader">Policy</span><span role="columnheader">Batteries</span><span role="columnheader">Solar panels</span></div>` +
      options.map(([key, label]) => `<div role="row" class="policy-row"><span role="rowheader">${esc(label)}</span>${cell("liion", key)}${cell("pv", key)}</div>`).join("");
    const left = (id, key) => singles(sectors[id].B, key).length;
    $("policy-note").textContent = `Three months of stock cuts battery weak points from ${word(W.liion.length)} to ${word(left("liion","a0.25_h3_s0_L6_D12"))} and solar from ${word(W.pv.length)} to ${word(left("pv","a0.25_h3_s0_L6_D12"))}. Even 50% extra factory capacity leaves ${word(left("liion","a0.25_h0_s0.5_L6_D12"))} battery and ${word(left("pv","a0.25_h0_s0.5_L6_D12"))} solar weak points. The extra output comes from producers outside China, which are small to begin with: half as much again of a 10% share adds only 5% of world supply.`;
  }

  function minerals() {
    const pairs = [["Lithium","Lithium"],["Cobalt","Cobalt"],["Nickel","Nickel"],["Copper","Copper"]];
    const mine = m => C.summaries.find(s => s.commodity === m && s.stage === "mine" && s.year === 2025);
    const refine = m => C.refining.find(r => r.name === m && r.year === 2025);
    const mark = x => `left:${100 * x}%`;
    $("mine-refine").innerHTML = pairs.map(([m, r]) => [mine(m), refine(r), m]).filter(([a, b]) => a && b).map(([a, b, m]) => {
      const lo = Math.min(a.named_top_share, b.top_share), hi = Math.max(a.named_top_share, b.top_share);
      return row(m, `mined most in ${place(a.named_top_country)}`, `<i class="span" style="left:${100 * lo}%;width:${100 * (hi - lo)}%"></i><i class="dot short" style="${mark(a.named_top_share)}" title="Largest miner: ${esc(place(a.named_top_country))}, ${pct(a.named_top_share)}"></i><i class="dot long" style="${mark(b.top_share)}" title="Largest refiner: ${pct(b.top_share)}"></i>`,
        `${pct(a.named_top_share)} → <b>${pct(b.top_share)}</b>`);
    }).join("") + `<div class="row axis"><span class="row-label"></span><span class="row-track ticks">${[0, .25, .5, .75, 1].map(x => `<span style="${mark(x)}">${pct(x)}</span>`).join("")}</span><span class="row-value"></span></div>`;
  }

  function odds() {
    const fixed = D.configs[R];
    $("odds-figures").innerHTML = Object.values(sectors).map(s => `<div class="fact"><b>${pct(s.B.configs[R].L)}</b><span>${esc(s.name)}: chance per year of a major shortfall in the stress test</span></div>`).join("");
    const extra = singles(D, R).filter(w => !W.liion.some(x => x.v === w.v)).map(w => product(D.nodes.product[w.v]).toLowerCase());
    $("recipe-note").textContent = `This assumes battery makers can switch between the two main recipes. If they cannot, ${word(extra.length)} more Chinese parts become weak points (${extra.join(" and ")}) and the battery figure rises from ${pct(D.choice.configs[R].L)} to ${pct(fixed.L)}.`;
  }

  function theme() {
    const mode = matchMedia("(prefers-color-scheme: dark)"), root = document.documentElement;
    let stored; try { stored = localStorage.getItem("supply-theme"); } catch { /* Storage can be disabled. */ }
    if (["light","dark"].includes(stored)) root.dataset.theme = stored;
    const dark = () => root.dataset.theme ? root.dataset.theme === "dark" : mode.matches;
    const label = () => { $("theme").textContent = dark() ? "Light view" : "Dark view"; $("theme").setAttribute("aria-label", `Switch to ${dark() ? "light" : "dark"} theme`); };
    $("theme").onclick = () => { root.dataset.theme = dark() ? "light" : "dark"; try { localStorage.setItem("supply-theme", root.dataset.theme); } catch { /* Theme still works for this page. */ } label(); };
    mode.addEventListener("change", label); label();
  }

  theme(); hero(); chain("liion"); chain("pv"); cobalt(); duration(); policies(); minerals(); odds();
})();
