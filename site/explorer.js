/* D: saved certified results; C: observational context; S: selected scenario; P: defaults.
   k: saved configuration key; B: network block; c: configuration; v: node index.
   The browser selects saved results. It never solves an LP or interpolates a missing run. */
"use strict";
(() => {
  const D = window.DATA, C = window.CONTEXT, $ = id => document.getElementById(id);
  const esc = x => String(x ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const pct = (x, d = 1) => x == null ? "Not available" : `${(100 * x).toFixed(d)}%`;
  const num = (x, d = 0) => x == null ? "Withheld / unavailable" : Number(x).toLocaleString("en", {maximumFractionDigits: d});
  const country = c => window.LABELS.place(c, C.meta.countries[c]), product = window.LABELS.product;
  const sectors = {liion:"Batteries",pv:"Solar",joint:"Batteries + solar"};
  const P = {sector:"liion",chemistry:"choice",alpha:"0.25",DJ:"12",h:"0",sigma:"0",L:"6"};
  const allowed = {sector:["liion","pv","joint"],chemistry:["choice","fixed"],alpha:["0.1","0.25","0.5"],DJ:["3","6","12"],h:["0","1","3"],sigma:["0","0.1","0.5"],L:["6","24"]};
  const read = raw => Object.fromEntries(Object.entries(P).map(([k,v]) => [k,allowed[k].includes(raw[k]) ? raw[k] : v]));
  const S = read(Object.fromEntries(new URLSearchParams(location.search)));
  let pin = null, cutRows = [], nodeRows = [];
  const k = s => `a${s.alpha}_h${s.h}_s${s.sigma}_L${s.sigma === "0" ? "6" : s.L}_D${s.DJ}`;
  const block = s => s.sector === "pv" ? D.pv : s.sector === "joint" ? (s.chemistry === "choice" ? D.joint_choice : D.joint) : s.chemistry === "choice" ? D.choice : D;
  const config = s => block(s).configs[k(s)];
  const normalise = s => {
    if (s.sector === "joint") { s.h = "0"; s.sigma = "0"; if (s.alpha === "0.5") s.alpha = "0.25"; }
    if (s.sigma === "0") s.L = "6";
    return s;
  };
  normalise(S);
  const rawPin = new URLSearchParams(location.search).get("pin");
  if (rawPin) { const p = rawPin.split(","); if (p.length === 7 && p.every((v,i) => allowed[Object.keys(P)[i]].includes(v))) pin = normalise(read(Object.fromEntries(Object.keys(P).map((key,i) => [key,p[i]])))); }

  function url() {
    const u = new URL(location.href);
    Object.entries(S).forEach(([key,value]) => u.searchParams.set(key,value));
    if (pin) u.searchParams.set("pin",Object.keys(P).map(key => pin[key]).join(",")); else u.searchParams.delete("pin");
    return u;
  }
  function save() { history.replaceState(null,"",url()); $("share-status").textContent = ""; }
  const table = (head, rows) => `<thead><tr>${head.map(x => `<th scope="col">${esc(x)}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(x => `<td>${x}</td>`).join("")}</tr>`).join("")}</tbody>`;
  const metric = (value,label) => `<div class="metric"><b>${esc(value)}</b><span>${esc(label)}</span></div>`;
  const duration = (v,d,N) => `${country(N.country[v])} · ${product(N.product[v])} · ${d} months`;
  function csv(file, header, rows) {
    const quote = x => `"${String(x ?? "").replaceAll('"','""')}"`;
    const blob = new Blob(["\ufeff" + [header,...rows].map(row => row.map(quote).join(",")).join("\r\n")],{type:"text/csv;charset=utf-8"});
    const href = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = href; a.download = file; a.click(); setTimeout(() => URL.revokeObjectURL(href),1000);
  }
  function controls() {
    Object.keys(P).forEach(key => { $(key).value = S[key]; });
    const joint = S.sector === "joint";
    $("alpha").querySelector('[value="0.5"]').disabled = joint;
    $("h").disabled = joint; $("sigma").disabled = joint;
    $("L").disabled = S.sigma === "0" || joint;
    $("chemistry").disabled = S.sector === "pv";
    $("chemistry-note").textContent = S.sector === "pv" ? "Battery recipes do not apply to the solar chain." : "Flexibility is assumed; real plant switchability is unmeasured.";
    $("ramp-note").textContent = S.sigma === "0" ? "Ramp time has no effect without spare capacity." : "Additional capacity ramps linearly to the selected level.";
    $("availability").textContent = joint ? "Shared-network runs cover 10% or 25% thresholds, zero stock and zero spare capacity. Other settings are unavailable." : "";
  }
  function results() {
    const c = config(S), n = c.cuts.filter(cut => cut.length === 1).length;
    const B = block(S), ref = config({...P,sector:S.sector}), delta = c.L-ref.L;
    const est = S.h === "0" && S.sigma === "0" && S.DJ === "12" ? (B.residual?.[S.alpha] || B.estimates?.[S.alpha]?.residual) : null;
    const headline = c.cuts.length === 0 ? `No cut with up to three losses exceeds <em>${pct(+S.alpha,0)}</em> shortfall.` :
      n ? `<em>${n} single ${n === 1 ? "loss" : "losses"}</em> can each exceed ${pct(+S.alpha,0)} shortfall.` : `<em>${c.cuts.length} combinations</em> exceed ${pct(+S.alpha,0)} shortfall. No single loss does.`;
    $("result").innerHTML = `<p class="eyebrow">${esc(sectors[S.sector])} · ${S.sector === "pv" ? "Four-stage solar chain" : S.chemistry === "choice" ? "Flexible battery recipes" : "Fixed 50/50 battery recipes"}</p><h3 class="result-title">${headline}</h3>` +
      `<p class="scenario-caption">Cumulative unmet demand over 24 months, after recourse. Outages last at most ${S.DJ} months; stock ${S.h} months; spare capacity ${pct(+S.sigma,0)}.</p>` +
      `<div class="metrics">${metric(c.cuts.length,"Failing combinations of up to three losses")}${metric(n,"Single losses that fail on their own")}${metric(pct(c.L),"Stress-test odds per year (lower bound)")}${metric(`${delta > 0 ? "+" : ""}${(delta*100).toFixed(1)} pp`,"Change from the default settings")}</div>` +
      `<p class="scenario-caption">Probability assumes the saved policy-onset and outage law. It is a conditional scenario, not a forecast.</p>` +
      `<details class="result-method"><summary>Probability estimate, sampling interval & bounds</summary><p class="scenario-caption">${est ? `Saved L + residual estimate: ${pct(est.estimate,3)}; 95% sampling interval ${pct(est.ci95[0],3)}–${pct(est.ci95[1],3)}.` : "No residual simulation was saved for this configuration."} Exact scenario bracket: L ${pct(c.L,3)} ≤ failure probability ≤ U ${pct(c.U,3)}.${c.U === 1 ? " U counts all states with more than three losses; it does not assert certain failure." : ""}</p></details>`;
  }
  function chain() {
    const B = block(S), N = B.nodes, c = config(S), singles = new Set(c.cuts.filter(s => s.length === 1).map(s => N.product[s[0][0]]));
    const groups = S.sector === "pv" ? [["01 · Feedstock",["polysilicon"]],["02 · Wafers",["wafer"]],["03 · Cells",["pv_cell"]],["04 · Modules",["module"]]] :
      [["01 · Minerals",["mine_li","mine_co","mine_ni","mine_mn","graphite"]],["02 · Refining",["li_carbonate","refined_co","refined_ni","refined_cu","aluminium","polysilicon"]],["03 · Materials",["pcam","cam","aam","wafer"]],["04 · Cells & modules",["cell","pv_cell","module"]]];
    $("chain").innerHTML = groups.map(([label,products]) => `<div class="chain-group"><h4>${esc(label)}</h4>${products.filter(p => N.product.includes(p)).map(p => {
      const indices = N.product.map((q,v) => q === p ? v : -1).filter(v => v >= 0).sort((a,b) => N.share[b]-N.share[a]), v = indices[0];
      return `<button type="button" class="stage ${singles.has(p) ? "critical" : ""}" data-product="${esc(p)}" aria-label="Inspect ${esc(product(p))}: ${esc(country(N.country[v]))}, ${pct(N.share[v])} of reference layer${singles.has(p) ? "; a single-loss cut exists" : ""}"><span class="stage-title">${esc(product(p))}${singles.has(p) ? " ·" : ""}</span><span class="track"><span style="width:${100*N.share[v]}%"></span></span><span class="stage-caption"><span>${esc(country(N.country[v]))}</span><span>${pct(N.share[v],0)}</span></span></button>`;
    }).join("")}</div>`).join("");
    $("chain").querySelectorAll("button").forEach(b => b.onclick = () => { $("node-product").value = b.dataset.product; nodes(); $("evidence").scrollIntoView(); $("node-product").focus({preventScroll:true}); });
  }
  function cuts() {
    const B = block(S), N = B.nodes, c = config(S), q = $("cut-query").value.toLowerCase().trim(), size = $("cut-size").value, order = $("cut-sort").value;
    cutRows = c.cuts.map((cut,i) => ({cut,phi:c.phi[i],risk:c.attribution[i],pred:c.predecessors[i],id:i+1})).filter(r => (size === "all" || r.cut.length === +size) && (!q || r.cut.some(([v]) => `${country(N.country[v])} ${N.country[v]} ${product(N.product[v])} ${N.product[v]}`.toLowerCase().includes(q))));
    cutRows.sort((a,b) => order === "risk" ? b.risk-a.risk : order === "size" ? a.cut.length-b.cut.length || b.phi-a.phi : b.phi-a.phi || a.cut.length-b.cut.length);
    $("cut-count").textContent = `Showing ${cutRows.length} of ${c.cuts.length} minimal combinations. Bars show shortfall on a 0–100% scale.`;
    $("cut-list").innerHTML = cutRows.length ? cutRows.map(r => `<article class="cut-row"><div>${r.cut.map(([v,d]) => `<div class="loss">${esc(country(N.country[v]))} · ${esc(product(N.product[v]))}<br><span class="subtle">${d} months · ${esc(N.basis[v])}</span></div>`).join("") || "No outage: baseline failure"}</div><div class="cut-value">${pct(r.phi)}<span class="track"><span style="width:${100*r.phi}%"></span></span><span class="basis">shortfall</span></div><details><summary>Shorter-outage checks & probability contribution</summary>${r.pred.map(([v,d,phi]) => `<p>${esc(duration(v,d,N))} → ${pct(phi,4)} shortfall; all other losses unchanged.</p>`).join("")}<p>Occurrence probability / L: ${pct(r.risk,2)}. Contributions overlap. Cut ID ${r.id}.</p></details></article>`).join("") : `<p class="empty">${c.cuts.length ? "No combinations match these filters. Clear the search or choose all combination sizes." : "No minimal cut of up to three losses exists for this saved configuration. Larger combinations can still fail."}</p>`;
    $("download-cuts").disabled = !cutRows.length;
  }
  function nodeOptions() {
    const old = $("node-product").value, products = [...new Set(block(S).nodes.product)].sort();
    $("node-product").innerHTML = `<option value="all">All products</option>` + products.map(p => `<option value="${esc(p)}">${esc(product(p))}</option>`).join("");
    $("node-product").value = products.includes(old) ? old : "all";
  }
  function nodes() {
    const N = block(S).nodes, q = $("node-query").value.toLowerCase().trim(), p = $("node-product").value, basis = $("node-basis").value;
    nodeRows = N.country.map((_,v) => v).filter(v => (p === "all" || p === N.product[v]) && (basis === "all" || basis === N.basis[v]) && (!q || `${country(N.country[v])} ${N.country[v]} ${product(N.product[v])} ${N.source[v]}`.toLowerCase().includes(q)));
    $("node-count").textContent = `${nodeRows.length} of ${N.country.length} reference nodes. Annual output is in the stated unit; products have different units and cannot be summed.`;
    $("node-table").innerHTML = table(["Country","Product","Annual output","Unit","Layer share","Basis","Source"], nodeRows.map(v => [esc(country(N.country[v])),esc(product(N.product[v])),num(N.annual[v],3),esc(N.unit[v]),pct(N.share[v]),esc(N.basis[v]),esc(N.source[v])]));
    if (!nodeRows.length) $("node-table").innerHTML += '<caption class="empty">No suppliers match these filters.</caption>';
    $("download-nodes").disabled = !nodeRows.length;
  }
  function comparison() {
    const same = pin?.sector === S.sector, ref = same ? pin : {...P,sector:S.sector}, a = config(ref), b = config(S);
    const describe = s => `${sectors[s.sector]}, ${s.sector === "pv" ? "solar" : s.chemistry === "choice" ? "flexible recipes" : "fixed recipes"}, threshold ${pct(+s.alpha,0)}, outage ≤ ${s.DJ} mo, stock ${s.h} mo, spare ${pct(+s.sigma,0)}, ramp ${s.L} mo`;
    $("comparison-note").textContent = `${same ? "Pinned" : "Published reference"}: ${describe(ref)}.${pin && !same ? ` The pinned ${sectors[pin.sector]} scenario is in a different sector.` : ""}`;
    const count = c => c.cuts.filter(s => s.length === 1).length;
    $("comparison").innerHTML = `<div class="table-wrap"><table class="comparison-table">${table(["Measure",same ? "Pinned" : "Reference","Selected","Change"],[["Cut sets",a.cuts.length,b.cuts.length,b.cuts.length-a.cuts.length],["Single-loss cuts",count(a),count(b),count(b)-count(a)],["Scenario L",pct(a.L,3),pct(b.L,3),`${((b.L-a.L)*100).toFixed(2)} pp`],["Scenario U",pct(a.U,3),pct(b.U,3),`${((b.U-a.U)*100).toFixed(2)} pp`]])}</table></div>`;
    $("clear-pin").hidden = !pin;
    const saved = S.h === "0" && S.sigma === "0" && S.DJ === "12";
    let rows;
    if (S.sector === "pv") {
      $("risk-title").textContent = "Solar under the saved policy scenarios";
      rows = [["Full-outage law",saved ? D.pv.estimates[S.alpha]?.residual : null, config(S).L]];
      if (saved && S.alpha === "0.25") rows.push(["Quotas & bans only (post hoc)",D.severity.sectors.pv.hard.residual,D.severity.sectors.pv.hard.L]);
    } else {
      $("risk-title").textContent = "Recipe flexibility changes the failure scenario";
      rows = ["choice","fixed"].map(chemistry => {
        const s = {...S,chemistry}, B = block(s);
        return [chemistry === "choice" ? "Flexible recipes" : "Fixed 50/50 recipes", saved ? (B.residual?.[S.alpha] || B.estimates?.[S.alpha]?.residual) : null,config(s).L];
      });
    }
    $("risk-scope").textContent = `${sectors[S.sector]}; threshold ${pct(+S.alpha,0)}, stock ${S.h} months, spare ${pct(+S.sigma,0)}, outages ≤ ${S.DJ} months.${rows.some(r => r[1]) ? " L + residual estimates with 95% sampling intervals." : " Exact lower bounds L only; no residual simulation saved here."}`;
    $("risk-chart").innerHTML = rows.map(([label,e,L]) => { const x = e?.estimate ?? L; return `<div class="risk-row"><div class="risk-label"><span>${esc(label)}</span><b>${pct(x,2)}</b></div><div class="risk-track" role="img" aria-label="${esc(label)}: ${pct(x,3)}${e ? `, 95% interval ${pct(e.ci95[0],3)} to ${pct(e.ci95[1],3)}` : ", lower bound"}"><div class="risk-fill" style="width:${x*100}%"></div>${e ? `<span class="risk-ci" style="left:${e.ci95[0]*100}%;width:${(e.ci95[1]-e.ci95[0])*100}%"></span>` : ""}</div><p class="source-note">L = ${pct(L,3)}${e ? `; interval ${pct(e.ci95[0],3)}–${pct(e.ci95[1],3)}; ${num(e.n)} draws` : "; residual not measured"}.</p></div>`; }).join("") + '<div class="risk-axis"><span>0%</span><span>Annual conditional probability</span><span>100%</span></div>';
  }
  function minerals() {
    const [commodity,stage] = $("mineral").value.split("|"), year = +$("year").value, measure = $("measure").value;
    const rows = C.production.filter(r => r.commodity === commodity && r.stage === stage && r.year === year), summary = C.summaries.find(r => r.commodity === commodity && r.stage === stage && r.year === year);
    const named = rows.filter(r => !r.world && !r.aggregate && r.tonnes !== null).sort((a,b) => b.tonnes-a.tonnes), leader = named[0];
    $("production-title").textContent = `${country(leader.country)} supplied ${pct(leader.share)} of published ${commodity.toLowerCase()} ${stage} output`;
    $("production-scope").textContent = `${year} · ${num(summary.world_tonnes)} tonnes published world total · ${summary.coverage_note}`;
    const prior = C.summaries.find(r => r.commodity === commodity && r.stage === stage && r.year === year-1);
    $("production-change").textContent = prior ? `Published world output ${summary.world_tonnes >= prior.world_tonnes ? "rose" : "fell"} ${pct(Math.abs(summary.world_tonnes/prior.world_tonnes-1))} from 2024. The three largest named producers account for ${pct(summary.named_top3_share)} of this total; other-country aggregates and withheld output limit a complete concentration measure.` : "2024 is the reference year shown here. Select 2025 to compare world-output growth.";
    const plotted = [...named.slice(0,10),...rows.filter(r => r.aggregate && r.tonnes > 0)];
    $("production-chart").innerHTML = plotted.map(r => `<div class="bar-row"><span class="bar-label">${esc(country(r.country))}${r.estimated ? " *" : ""}</span><span class="track"><span style="width:${100*r.share}%"></span></span><span class="bar-value">${measure === "share" ? pct(r.share) : num(r.tonnes)}</span></div>`).join("");
    $("production-warning").textContent = `Bars use a 0–100% world-output scale; showing ${Math.min(10,named.length)} largest named producers${rows.some(r => r.aggregate && r.tonnes > 0) ? " plus the Other countries aggregate" : ""}. * Estimated. ${summary.coverage_note} Published totals are rounded; country values may not add to them.`;
    const previous = r => C.production.find(p => p.commodity === commodity && p.stage === stage && p.year === 2024 && p.country === r.country)?.tonnes;
    $("production-table").innerHTML = table(["Country / aggregate","Tonnes","World share","2025 vs 2024","Source flags"],rows.map(r => {
      const prev = previous(r), change = year === 2025 && prev > 0 && r.tonnes !== null ? `${((r.tonnes/prev-1)*100).toFixed(1)}%` : "—";
      return [esc(country(r.country)),num(r.tonnes),r.world ? "—" : pct(r.share),change,esc([r.missing,r.estimated ? "Estimated" : "",r.notes].filter(Boolean).join("; "))];
    }));
  }
  function refining() {
    const all = $("all-refining").checked, rows = C.refining.filter(r => all || r.group === "Battery materials").sort((a,b) => b.top_share-a.top_share);
    $("refining-chart").innerHTML = rows.map(r => `<div class="bar-row"><span class="bar-label">${esc(r.name)}${r.name === "Geranium" ? " †" : ""}</span><span class="track"><span style="width:${100*r.top_share}%"></span></span><span class="bar-value">${pct(r.top_share,0)}</span></div>`).join("") + (all ? '<p class="source-note">† “Geranium” is the source chart’s spelling, preserved here. Shares use a 0–100% scale.</p>' : '<p class="source-note">Shares use a 0–100% scale. Select All minerals for the full cross-section.</p>');
    $("refining-table").innerHTML = table(["Mineral (source label)","Group","Top country share","Market size, USD bn"],rows.map(r => [esc(r.name),esc(r.group),pct(r.top_share),num(r.market_usd_bn,2)]));
  }
  function render() { controls(); results(); chain(); cuts(); nodeOptions(); nodes(); comparison(); save(); }
  Object.keys(P).forEach(key => $(key).onchange = () => { S[key] = $(key).value; normalise(S); render(); });
  ["cut-query","cut-size","cut-sort"].forEach(id => $(id).addEventListener(id === "cut-query" ? "input" : "change",cuts));
  ["node-query","node-product","node-basis"].forEach(id => $(id).addEventListener(id === "node-query" ? "input" : "change",nodes));
  $("reset").onclick = () => { Object.assign(S,P); $("cut-query").value = ""; $("cut-size").value = "all"; $("cut-sort").value = "phi"; $("node-query").value = ""; $("node-basis").value = "all"; $("node-product").value = "all"; render(); };
  $("pin").onclick = () => { pin = {...S}; comparison(); save(); $("share-status").textContent = "Scenario pinned. Change a setting to compare below."; };
  $("clear-pin").onclick = () => { pin = null; comparison(); save(); };
  $("share").onclick = async () => { try { await navigator.clipboard.writeText(url().href); $("share-status").textContent = "Scenario link copied."; } catch { $("share-status").textContent = "Copy the current address from your browser; it contains these scenario settings."; } };
  $("download-cuts").onclick = () => { const N = block(S).nodes; csv(`supply-cuts-${S.sector}-${k(S)}.csv`,["sector","chemistry","configuration","cut_id","losses","shortfall_fraction","occurrence_probability_over_L","shorter_outage_checks"],cutRows.map(r => [S.sector,S.chemistry,k(S),r.id,r.cut.map(([v,d]) => `${duration(v,d,N)} (${N.basis[v]})`).join(" + "),r.phi,r.risk,r.pred.map(([v,d,phi]) => `${duration(v,d,N)}: ${phi}`).join("; ")])); };
  $("download-nodes").onclick = () => { const N = block(S).nodes; csv(`supply-nodes-${S.sector}.csv`,["country_iso3","country","product","annual_output","unit","layer_share","basis","source"],nodeRows.map(v => [N.country[v],country(N.country[v]),N.product[v],N.annual[v],N.unit[v],N.share[v],N.basis[v],N.source[v]])); };
  const pairs = [...new Set(C.production.map(r => `${r.commodity}|${r.stage}`))].sort();
  $("mineral").innerHTML = pairs.map(p => `<option value="${esc(p)}">${esc(p.replace("|"," · "))}</option>`).join(""); $("mineral").value = "Lithium|mine";
  ["mineral","year","measure"].forEach(id => $(id).onchange = minerals); $("all-refining").onchange = refining;
  $("capacity-table").innerHTML = table(["Capacity scenario","Recipes","Baseline shortfall","Cuts","Vanish / appear"],D.supply.cases.map(x => [esc(window.LABELS.capacityCase(x.case)),x.choice ? "Flexible" : "Fixed 50/50",pct(x.baseline,3),x.baseline > .25 ? "1 empty set (baseline fails)" : x.cuts,`${x.vanish} / ${x.appear}`]));
  $("provenance").textContent = `Reference result bundles: ${D.meta.run}, ${D.pv.meta.run}, ${D.joint.meta.run}. Flexible recipes: ${D.choice.meta.cut_run}, ${D.choice.meta.risk_run}. Capacity sensitivity: ${D.supply.run}. Source revisions: ${D.meta.revision.slice(0,7)} / ${D.choice.meta.revision.slice(0,7)}. Source lock at reference run: ${D.meta.lock}. Context: ${C.production.length} production observations and ${C.refining.length} refining points; hash-checked against the source lock. Explorer result payload uses five significant digits; full-precision results and certificates are in the repository.`;
  minerals(); refining(); render();
})();
