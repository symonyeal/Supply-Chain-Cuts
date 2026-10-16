"""W2 registered export event study and paired loss scenarios: python run_severity.py RUN.

Reads the immutable W1 bundles; writes a new bundle. Coefficients are export responses,
not production losses. The capacity conversion and unidentified-type fallbacks are scenarios.
"""
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from chokepoint.events import ALIAS, node_years
from chokepoint.fetch import stamp
from chokepoint.net import build, model
from chokepoint.rates import duration_weights, fit_rates
from chokepoint.risk import bracket, partial_sampling, residual_sampling
from chokepoint.severity import cohorts, estimate
from run_risk import dense

DURATIONS = (3, 6, 12)
BASE = {s: f"{s}-residual-2395a5c" for s in ("liion", "pv", "joint")}


def mixtures(V):
    """Measure marks, pooled by product over unique onset node-years; fallback all products."""
    _, _, records = node_years(V)
    groups, by_product, pooled = defaultdict(set), defaultdict(Counter), Counter()
    for e in records:
        m = e["measure"]
        m = "M4" if "prohibition" in m else "M6" if "licensing" in m else m
        for p in {ALIAS.get(p, p) for p in e["products"]}:
            groups[e["country"], p, e["year"]].add(m)
    for (_, p, _), kinds in groups.items():
        for m in kinds:
            by_product[p][m] += 1/len(kinds)
            pooled[m] += 1/len(kinds)
    out, fallback = [], []
    for _, p in V:
        counts = by_product[p] or pooled
        out.append({m: counts[m]/counts.total() for m in sorted(counts)})
        fallback.append(not bool(by_product[p]))
    return out, fallback


def job(sector, table, run):
    """Three severity assignments share draws and certify monotonicity against full loss."""
    root, path = Path("."), Path("results") / BASE[sector]
    base = json.loads((path / "risk.json").read_text(encoding="utf-8"))
    N = build(sector=sector)
    M = model(N, durations=DURATIONS)
    V = M["V"]
    assert list(map(list, V)) == base["nodes"]
    mixes, fallback = mixtures(V)
    losses = {name: {} for name in ("central", "low", "high")}
    for m, row in table.items():
        losses["central"][m] = row["f"]
        for name, j in (("low", 0), ("high", 1)):
            losses[name][m] = float(np.clip(row["loss_ci95"][j], 0, 1)) if (
                row["identified"]) else 1.0
    R = partial_sampling(M, base["rates"]["p"], base["rates"]["rho"], DURATIONS,
                         base["durations"]["weights"], mixes, losses)
    if R["status"] == "optimal":
        assert R["monotone"]
        full, previous = R["scenarios"]["full"], base["residual"]["0.25"]
        R["full_agrees_with_W1"] = abs(full["estimate"]-previous["estimate"]) <= (
            4*np.hypot(full["se"], previous["se"]))
        delta = R["scenarios"]["central"]["reduction_ci95"]
        R["S3"] = "supported" if delta[0] >= 0.05 else (
            "killed" if delta[1] < 0.05 else "inconclusive")
    if "hard" in base:
        hard = {k: base["hard"][k] for k in ("L", "U", "residual")}
    else:
        W = [(x["country"], x["product"]) for x in build(sector="joint")["nodes"]]
        Y, _, used = node_years(W, root, hard=True)
        rh, law = fit_rates(W, Y), duration_weights(used, DURATIONS)
        p = [rh["p"][W.index(v)] for v in V]
        C = [dense(S, len(V)) for S in base["configs"]["base_a0.25_h0_s0_L6_D12"]["cuts"]]
        B = bracket(V, p, rh["rho"], DURATIONS, law["weights"], C, complete=True)
        hard = {"L": B["L"], "U": B["U"], "residual": residual_sampling(
            M, p, rh["rho"], DURATIONS, law["weights"], C, n=20000, seed=5, complete=True)}
    R.update(sector=sector, base_bundle=BASE[sector], stamp=stamp(), mixtures=mixes,
             pooled_mixture_fallback_nodes=[list(v) for v, f in zip(V, fallback, strict=True) if f],
             assigned_fractions=losses, full_outage=previous if R["status"] == "optimal" else None,
             hard={**hard, "registered": False}, severity_registered=True)
    out = Path("results") / run / f"{sector}.json"
    out.write_text(json.dumps(R, indent=1) + "\n", encoding="utf-8")
    return sector, R["status"]


def main():
    run = sys.argv[1]
    out = Path("results") / run
    out.mkdir(parents=True, exist_ok=True)
    E, overlapping, excluded = cohorts()
    table = estimate(E)
    data = {"stamp": stamp(), "events": E, "overlapping": overlapping, "excluded": excluded,
            "table": table, "overlap_descriptive": estimate(overlapping),
            "method": "stacked_exporter_and_year_FE", "bootstrap": "country_cluster",
            "bootstrap_seed": 6, "bootstrap_draws": 2000, "registered": True}
    (out / "severity.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print("Export-response table written", flush=True)
    with ProcessPoolExecutor(3) as pool:
        for f in as_completed([pool.submit(job, s, table, run) for s in BASE]):
            print(*f.result(), flush=True)


if __name__ == "__main__":
    main()
