"""Annual risk and registered tests (design §5, §6): python run_risk.py RUN_ID.

Reads results/RUN_ID/cuts/*.json, writes results/RUN_ID/risk.json. Rates are fitted to
policy onsets 2012-2024; durations are binned onto (3, 6, 12) months and truncated at D_J.
For D_J < 12 the cut list is the subset with every duration <= D_J: a state of the
restricted lattice is minimal there iff it is minimal in the full lattice.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from chokepoint.events import YEARS, node_years
from chokepoint.fetch import sampled, stamp
from chokepoint.net import build, model, reexport_flags
from chokepoint.rates import duration_weights, fit_rates, prequential
from chokepoint.recourse import solve
from chokepoint.risk import bracket, exact_union, importance_sampling, residual_sampling
from chokepoint.sweep import DURATIONS, K, dense, truncate

MIDSTREAM = ("pcam", "cam", "aam")                   # design §3: the midstream layer
REFINED = ("li_carbonate", "refined_co", "refined_ni")
NAMES = ("mine_co", "refined_co", "mine_ni", "refined_ni", "mine_mn", "pcam")


def label(cut, V):
    return sorted(f"{V[v][0]} {V[v][1]} {d}" for v, d in cut)


def hazards(N, root):
    """Natural-hazard scenario (design §5 fallback): country-wide loss fraction f for D."""
    E = json.loads((root / "data/events/natural_events.json").read_text(encoding="utf-8"))
    years = defaultdict(set)
    for e in E["events"]:
        if e["onset_in_window"]:
            for c in e["affected_countries"]:
                years[c].add(int(e["from_date"][:4]))
    M = model(N, durations=DURATIONS)
    V, theta, out = M["V"], 0.25*M["total"], []
    for c in sorted({v[0] for v in V}):
        I = [i for i, v in enumerate(V) if v[0] == c]
        row = {"country": c, "nodes": len(I),
               "alert_years": len(years[c] & set(map(int, YEARS))), "years": len(YEARS)}
        for f in (0.1, 0.25, 0.5, 1.0):
            for D in DURATIONS:
                Dv, fv = np.zeros(len(V)), np.ones(len(V))
                Dv[I], fv[I] = D, f
                row[f"phi_f{f}_D{D}"] = solve(M, Dv, dual=False, f=fv)["phi"]/M["total"]
        row["fails_at"] = [[f, D] for f in (0.1, 0.25, 0.5, 1.0) for D in DURATIONS
                           if row[f"phi_f{f}_D{D}"]*M["total"] > theta + 1e-7]
        out.append(row)
    return out


class _Risk:
    """The registered risk quantities of one run under its fitted onset law.

    V: nodes (country, product); p: onset rate per node; rho: country shock share;
    law: duration law with its weights over DURATIONS; n = |V|.
    configs: bracket of each base certificate's cuts, per D_J; head: the headline configuration
    (alpha = 0.25, D_J = 12, h = sigma = 0); cuts: head's cuts as dense outage states.
    """

    def __init__(self, C, V, p, rho, law):
        self.V, self.p, self.rho, self.law, self.n = V, p, rho, law, len(V)
        self.configs = {}
        for key, R in C.items():
            if not key.startswith("base"):
                continue
            assert R["complete"] and all(x["certified"] for x in R["certificates"]), key
            for DJ in DURATIONS:
                cuts = [S for S in R["cuts"] if max(d for _, d in S) <= DJ]
                Dl, w = truncate(law["weights"], DJ)
                B = bracket(V, p, rho, Dl, w, [dense(S, self.n) for S in cuts], k=K, complete=True)
                self.configs[f"{key}_D{DJ}"] = {
                    **R["config"], "DJ": DJ, "cuts": cuts, "L": B["L"], "U": B["U"],
                    "tail": B["tail"], "attribution": B["attribution"],
                    "certified": all(x["certified"] for x in R["certificates"])}
        self.head = self.configs["base_a0.25_h0_s0_L6_D12"]
        self.cuts = [dense(S, self.n) for S in self.head["cuts"]]

    def sampling(self, M):
        """Importance-sampling, crude Monte Carlo and residual estimates at each alpha whose
        D_J = 12 base configuration exists."""
        p, rho, w = self.p, self.rho, self.law["weights"]
        IS, MC, residual = {}, {}, {}
        for a in (a for a in (0.10, 0.25, 0.50) if f"base_a{a}_h0_s0_L6_D12" in self.configs):
            S = [dense(x, self.n) for x in self.configs[f"base_a{a}_h0_s0_L6_D12"]["cuts"]]
            IS[a] = sampled(importance_sampling(
                M, p, rho, DURATIONS, w, S, alpha=a,
                n=20000, pilot=2000, seed=1, complete=True, k=K))
            MC[a] = sampled(importance_sampling(
                M, p, rho, DURATIONS, w, S, alpha=a,
                n=20000, seed=2, complete=True, k=K, crude=True))
            residual[a] = sampled(residual_sampling(
                M, p, rho, DURATIONS, w, S,
                alpha=a, n=20000, seed=4, complete=True, k=K))
        return IS, MC, residual

    def attribution(self):
        """Headline L attributed to products and countries, with each country's exact union
        share."""
        V, L = self.V, self.head["L"]
        attr = dict(zip((tuple(map(tuple, S)) for S in self.head["cuts"]),
                        self.head["attribution"], strict=True))
        by_product, by_country = defaultdict(float), defaultdict(float)
        for S, x in attr.items():
            for q in {V[v][1] for v, _ in S}:
                by_product[q] += x
            for c in {V[v][0] for v, _ in S}:
                by_country[c] += x
        out = {"product": dict(by_product), "country": dict(by_country)}
        out["country_union"] = {     # P(∪ cut sets containing c)/L, exact
            c: exact_union(V, self.p, self.rho, list(DURATIONS), self.law["weights"],
                           [S for S in self.cuts if any(d and V[v][0] == c
                                                        for v, d in enumerate(S))])/L
            for c in by_country} if L else {}
        return out

    def headline(self, N, out):
        """Registered tests H1-H3 and A1 at the headline configuration; out is the run's result
        so far, with its attribution, IS and residual estimates."""
        V, head, L = self.V, self.head, self.head["L"]
        graphite = [S for S in head["cuts"] if len(S) == 1 and V[S[0][0]] == ("CHN", "graphite")]

        def share(P):
            if not L:
                return None
            S = [S for S in self.cuts if any(d and V[v][0] == "CHN" and V[v][1] in P
                                             for v, d in enumerate(S))]
            return exact_union(V, self.p, self.rho, list(DURATIONS), self.law["weights"], S)/L
        products = sorted(N["hhi"])
        a = [out["attribution"]["product"].get(q, 0.0) for q in products]
        rank = {m: (None if np.ptp(a) == 0 else float(spearmanr(a, [N[m][q] for q in products])
                                                    .statistic)) for m in ("hhi", "top_share")}
        return {
            "H1_china_graphite_singleton": {"durations": [S[0][1] for S in graphite],
                                            "six_month_possible": False},
            "H2_china_midstream_share_of_L": {
                "midstream": share(MIDSTREAM), "with_refined": share(MIDSTREAM + REFINED),
                "with_refined_and_graphite": share(MIDSTREAM + REFINED + ("graphite",)),
                "threshold": 0.8},
            "H3_annual_failure": {"L": L, "U": head["U"], "IS": out["IS"][0.25],
                                  "residual": out["residual"][0.25],
                                  "interval": [0.01, 0.10]},
            "A1_spearman": {"products": products, "attribution": a, **rank, "threshold": 0.9},
        }


def _robustness(N, C, configs, D1):
    """Registered tests B1, B2, C1, D1 and E1: cut lists that vanish or appear under the
    re-export, capacity-basis and chemistry variants, and the one-at-a-time tornado."""
    flagged = {tuple(x[:2]) for x in reexport_flags(N)}

    def names(key):
        R = C[key]
        return {tuple(label(S, R["nodes"])) for S in R["cuts"]}

    base = {a: names(f"base_a{a}_h0_s0_L6") for a in (0.1, 0.25)}
    return {
        "B1_reexport": {"flagged": sorted(map(list, flagged)),
                        "demand_ratio": build(exclude=flagged)["requirement"]["cell"]
                        / N["requirement"]["cell"],
                        "withdrawn": sorted(list(x) for x in base[0.25] if any(
                            " ".join(f.split()[:2]) in {" ".join(y) for y in flagged}
                            for f in x)),
                        **{f"a{a}": {"vanish": sorted(map(list, base[a] - names(f"B1_a{a}"))),
                                     "appear": sorted(map(list, names(f"B1_a{a}") - base[a]))}
                           for a in (0.1, 0.25)}},
        "B2_capacity_basis": {f"a{a}": {"vanish": sorted(map(list, base[a] - names(f"B2_a{a}"))),
                                        "appear": sorted(map(list, names(f"B2_a{a}") - base[a]))}
                              for a in (0.1, 0.25)},
        "C1_chemistry": {f"ncm{x}_a{a}": {
            "vanish_co_ni": sorted(list(S) for S in base[a] - names(f"C1_ncm{x}_a{a}")
                                   if any(f.split()[1] in NAMES for f in S)),
            "appear": sorted(map(list, names(f"C1_ncm{x}_a{a}") - base[a]))}
            for x in (0.0, 0.25, 0.75, 1.0) for a in (0.1, 0.25)},
        "robust_singletons": sorted(set.intersection(*(
            {S[0] for S in names(k) if len(S) == 1} for k in
            ["base_a0.25_h0_s0_L6", "B1_a0.25", "B2_a0.25",
             *(f"C1_ncm{x}_a0.25" for x in (0.0, 0.25, 0.75, 1.0))]))),
        "D1_prequential": D1,
        "E1_tornado": {k: {"L": x["L"], "cuts": len(x["cuts"])} for k, x in configs.items()
                       if sum([x["alpha"] != 0.25, x["h"] != 0, x["sigma"] != 0,
                               x["DJ"] != 12]) <= 1},
    }


def _hard(V, root, cuts, M):
    """Post hoc, not registered: rates, bracket and estimates when only quotas and
    prohibitions count as onsets."""
    Yh, ids_h, used_h = node_years(V, root, hard=True)
    rh = fit_rates(V, Yh)
    lh = duration_weights(used_h, DURATIONS)
    Bh = bracket(V, rh["p"], rh["rho"], list(DURATIONS), lh["weights"], cuts, k=K, complete=True)
    return {"rates": rh, "onsets": ids_h, "durations": lh, "L": Bh["L"], "U": Bh["U"],
            "IS": sampled(importance_sampling(
                M, rh["p"], rh["rho"], DURATIONS, lh["weights"], cuts, alpha=0.25,
                n=20000, pilot=2000, seed=3, complete=True, k=K)),
            "residual": sampled(residual_sampling(
                M, rh["p"], rh["rho"], DURATIONS, lh["weights"], cuts, alpha=0.25,
                n=20000, seed=5, complete=True, k=K)),
            "registered": False}


def main():
    root, run = Path("."), Path("results") / sys.argv[1]
    C = {x.stem: json.loads(x.read_text(encoding="utf-8")) for x in sorted((run / "cuts")
                                                                            .glob("*.json"))}
    sector = next(iter(C.values()))["network"]["sector"]
    N = build(sector=sector)
    V = [(x["country"], x["product"]) for x in N["nodes"]]
    assert all(R["nodes"] == [list(v) for v in V] for k, R in C.items() if k.startswith("base"))
    # PV has exposure only for polysilicon: fit on the joint node set so its pool is the
    # all-product pool of the Li-ion fit plus polysilicon; Li-ion keeps the registered fit.
    W = V if sector == "liion" else [(x["country"], x["product"])
                                     for x in build(sector="joint")["nodes"]]
    Y, onsets, used = node_years(W, root)
    rates = fit_rates(W, Y)
    I = [W.index(v) for v in V]
    rates.update({k: [rates[k][i] for i in I] for k in ("p", "exposure", "onsets", "basis")})
    p, rho = np.array(rates["p"]), rates["rho"]
    law = duration_weights(used, DURATIONS)
    D1 = prequential(W, Y, YEARS, train_end=2019)
    risk = _Risk(C, V, p, rho, law)
    out = {"stamp": stamp(root), "sector": sector, "nodes": [list(v) for v in V], "rates": rates,
           "onsets": onsets, "durations": law, "D1": D1, "configs": risk.configs}
    head, L = risk.head, risk.head["L"]
    M = model(N, durations=DURATIONS)
    out["IS"], out["MC"], out["residual"] = risk.sampling(M)
    out["attribution"] = risk.attribution()
    if sector != "liion":                    # the registered tests concern Li-ion (v0.1.0)
        (run / "risk.json").write_text(json.dumps(out, indent=1, default=float),
                                       encoding="utf-8")
        print(sector, "L", L, "U", head["U"], "residual", out["residual"][0.25]["estimate"])
        return
    tests = {**risk.headline(N, out), **_robustness(N, C, out["configs"], D1)}
    out["hard"] = _hard(V, root, risk.cuts, M)
    out.update(tests=tests, hazards=hazards(N, root))
    (run / "risk.json").write_text(json.dumps(out, indent=1, default=float) + "\n",
                                   encoding="utf-8")
    print("L", L, "U", head["U"], "residual", out["residual"][0.25]["estimate"],
          out["residual"][0.25]["ci95"])


if __name__ == "__main__":
    main()
