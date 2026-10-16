"""Build site/data.js: python analysis/build_site.py LIION_RUN [PV_RUN JOINT_RUN].

The page filters and draws; it computes nothing the model computes. Certificates are
asserted before anything is written: every cut certified (zero gap, predecessors below the
threshold), L <= estimate interval overlap checked and reported, U >= L.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def plain(o, nd=5):
    """JSON-native copy: floats to nd significant digits, NaN to None."""
    if isinstance(o, dict):
        return {str(k): plain(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [plain(v, nd) for v in o]
    if isinstance(o, float):
        return None if math.isnan(o) else float(f"{o:.{nd}g}")
    return o


def pc(x, d=1):
    return "–" if x is None else f"{100*x:.{d}f}%"


def test_rows(t):
    """Registered tests (docs/HYPOTHESES.md): leaf, kill condition, result, verdict."""
    h1, h2, h3, a1, d1 = (t[k] for k in ("H1_china_graphite_singleton",
                                         "H2_china_midstream_share_of_L", "H3_annual_failure",
                                         "A1_spearman", "D1_prequential"))
    est, b2 = h3["IS"], t["B2_capacity_basis"]["a0.25"]
    r = {k: (None if a1[k] is None else round(a1[k], 2)) for k in ("hhi", "top_share")}
    single = ", ".join(map(str, h1["durations"])) or "no"
    c1 = "; ".join(f"NCM {k.split('_')[0][3:]}: {len(v['vanish_co_ni'])} vanish"
                   for k, v in t["C1_chemistry"].items() if k.endswith("a0.25"))
    res = {
        "h1": f"singleton at {single} months; a 6-month loss cannot exceed 25% of 24 months",
        "h2": f"{pc(h2['without_graphite'])} (with graphite {pc(h2['with_graphite'])})",
        "h3": (f"L = {pc(h3['L'])}, U = {pc(h3['U'])}, IS {pc(est['estimate'])} "
               f"[{pc(est['ci95'][0])}, {pc(est['ci95'][1])}]"),
        "a1": f"ρ_S = {r['hhi']} with HHI, {r['top_share']} with top share",
        "b2": f"α = 25%: {len(b2['vanish'])} vanish, {len(b2['appear'])} appear",
        "d1": (f"model {d1['model_log_loss']:.3f} vs constant {d1['constant_log_loss']:.3f} "
               f"on {d1['test_node_years']} node-years, 2020–2024"),
    }
    mid = ("holds" if h2["without_graphite"] >= 0.8 else
           "holds only with graphite" if h2["with_graphite"] >= 0.8 else "killed")
    conc = max(a1["hhi"] or 0, a1["top_share"] or 0) >= 0.9
    return [
        ["Day-1 (i)", "China graphite is a singleton cut at α = 25%, D ≥ 6 months", res["h1"],
         "6-month part rejected; 12-month part holds" if h1["durations"] == [12] else "killed"],
        ["Day-1 (ii)", "cut sets with a Chinese midstream node carry ≥ 80% of L", res["h2"], mid],
        ["Day-1 (iii)", "annual P(fail) in [1%, 10%]", res["h3"],
         "killed" if h3["L"] > 0.10 or est["ci95"][1] < 0.01 else "holds"],
        ["A1", "Spearman(attribution, concentration) ≥ 0.9 ⇒ concentration suffices", res["a1"],
         "killed: concentration suffices" if conc else "survives: the network adds information"],
        ["B1", "a cut set resting on a re-export node is withdrawn",
         f"{len(t['B1_reexport']['withdrawn'])} cut sets withdrawn at α = 25%", "applied"],
        ["B2", "cut sets that change on the trade basis are basis-dependent", res["b2"],
         "applied"],
        ["C1", "Co/Ni cut sets that vanish at some NCM share are conditional on the mix", c1,
         "applied"],
        ["D1", "no out-of-sample log-loss gain ⇒ probabilities are scenarios", res["d1"],
         "survives: rates predict" if d1["improves"] else "killed: probabilities are scenarios"],
        ["E1", "tornado over α, D, h, σ, L", "see the controls above", "no kill condition"],
    ]


def load(run):
    d = ROOT / "results" / run
    cuts = {x.stem: json.loads(x.read_text(encoding="utf-8")) for x in (d / "cuts").glob("*.json")}
    return (json.loads((d / "network.json").read_text(encoding="utf-8")),
            json.loads((d / "data_checks.json").read_text(encoding="utf-8")),
            json.loads((d / "risk.json").read_text(encoding="utf-8")), cuts)


def block(run):
    """Nodes, certified cut lists with L, U and shortfalls, estimates and attribution."""
    net, checks, risk, cuts = load(run)
    N = net[risk["sector"]]
    V = risk["nodes"]
    assert V == [[x["country"], x["product"]] for x in N["nodes"]]
    for R in cuts.values():
        assert all(c["certified"] for c in R["certificates"]), R["task"]
        P, F, B = (R.get(k) for k in ("pruned", "milp_full", "brute_full"))
        assert not P or P["brute_equals_lattice"] and (P["milp_equals_brute"]
                                                       or not P["milp_complete"]), R["task"]
        assert not F or F["equals_lattice"] or not F["complete"], R["task"]
        assert not B or B["equals_lattice"], R["task"]
    configs = {}
    for k, x in risk["configs"].items():
        assert 0 <= x["L"] <= x["U"] <= 1
        R = cuts["_".join(k.split("_")[:-1])]
        phi = {json.dumps(S): c["phi"]/R["total"] for S, c in zip(R["cuts"], R["certificates"],
                                                                  strict=True)}
        configs[k.replace("base_", "")] = {
            "L": x["L"], "U": x["U"], "cuts": x["cuts"], "attribution": x["attribution"],
            "phi": [phi[json.dumps(S)] for S in x["cuts"]]}
    nodes = {"country": [v[0] for v in V], "product": [v[1] for v in V],
             "basis": [x["basis"] for x in N["nodes"]], "share": [x["share"] for x in N["nodes"]],
             "years": [12*x["capacity"] for x in N["nodes"]],
             "annual": [x["annual"] for x in N["nodes"]], "unit": [x["unit"] for x in N["nodes"]],
             "source": [x["source"] for x in N["nodes"]], "p": risk["rates"]["p"],
             "exposure": risk["rates"]["exposure"], "onsets": risk["rates"]["onsets"]}
    est = {f"{float(a)}": {"IS": risk["IS"][a], "MC": risk["MC"][a]} for a in risk["IS"]}
    out = {"meta": {"run": run, "revision": risk["stamp"]["revision"],
                    "lock": risk["stamp"]["lock_sha256"], "rho": risk["rates"]["rho"],
                    "durations": risk["durations"], "D1": risk["D1"]},
           "nodes": nodes, "configs": configs, "estimates": est,
           "attribution": risk["attribution"]}
    return out, N, risk, checks


def build(run, pv_run=None, joint_run=None):
    data, N, risk, checks = block(run)
    layers = sorted(N["supply_ratio"], key=lambda p: -N["hhi"].get(p, 0))
    data.update({
        "layers": {"product": layers, "S": [N["supply_ratio"][p] for p in layers],
                   "hhi": [N["hhi"].get(p) for p in layers],
                   "top": [N["top_share"].get(p) for p in layers]},
        "tests": risk["tests"], "testRows": test_rows(risk["tests"]),
        "hard": {k: risk["hard"][k] for k in ("L", "U", "IS")}, "hazards": risk["hazards"],
        "checks": {k: checks[k] for k in ("exports_vs_production", "reexport_flags",
                                          "site_coverage")}})
    for name, r in (("pv", pv_run), ("joint", joint_run)):
        if r:
            data[name] = block(r)[0]
    return data


def main():
    out = ROOT / "site" / "data.js"
    data = plain(build(*sys.argv[1:4]))
    out.write_text("window.DATA = " + json.dumps(data, separators=(",", ":"), ensure_ascii=False,
                                                 allow_nan=False) + ";\n", encoding="utf-8")
    print(f"{out}  {out.stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    main()
