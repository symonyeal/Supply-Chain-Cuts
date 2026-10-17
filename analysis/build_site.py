"""Build site/data.js: python analysis/build_site.py LIION_RUN [PV_RUN JOINT_RUN SEVERITY_RUN].

The page filters and draws; it computes nothing the model computes. Certificates are
asserted before anything is written: every cut certified (zero gap, predecessors below the
threshold), L <= estimate interval overlap checked and reported, U >= L.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chokepoint.risk import exact_union


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
    est, b2, b1 = h3["residual"], t["B2_capacity_basis"]["a0.25"], t["B1_reexport"]
    r = {k: (None if a1[k] is None else round(a1[k], 2)) for k in ("hhi", "top_share")}
    single = ", ".join(map(str, h1["durations"])) or "no"
    c1 = "; ".join(f"NCM {k.split('_')[0][3:]}: {len(v['vanish_co_ni'])} vanish"
                   for k, v in t["C1_chemistry"].items() if k.endswith("a0.25"))
    res = {
        "h1": f"singleton at {single} months; a 6-month loss cannot exceed 25% of 24 months",
        "h2": (f"{pc(h2['midstream'])} (pCAM, CAM, AAM); secondary: with refined chemicals "
               f"{pc(h2['with_refined'])}, and graphite {pc(h2['with_refined_and_graphite'])}"),
        "h3": (f"L = {pc(h3['L'])}, U = {pc(h3['U'])}, L + residual {pc(est['estimate'])} "
               f"[{pc(est['ci95'][0])}, {pc(est['ci95'][1])}]"),
        "a1": f"ρ_S = {r['hhi']} with HHI, {r['top_share']} with top share",
        "b2": f"α = 25%: {len(b2['vanish'])} vanish, {len(b2['appear'])} appear",
        "b1": (f"{len(b1['withdrawn'])} cut set rests on a flagged node; in the rerun "
               f"{len(b1['a0.25']['vanish'])} vanish and {len(b1['a0.25']['appear'])} appear at "
               f"α = 25%, because removing flagged cells lowers demand by "
               f"{pc(1 - b1['demand_ratio'])} and moves near-threshold combinations"),
        "d1": (f"model {d1['model_log_loss']:.3f} vs constant {d1['constant_log_loss']:.3f} "
               f"on {d1['test_node_years']} node-years, 2020–2024"),
    }
    mid = "holds" if h2["midstream"] >= 0.8 else "killed"
    conc = max(a1["hhi"] or 0, a1["top_share"] or 0) >= 0.9
    return [
        ["Day-1 (i)", "China graphite is a singleton cut at α = 25%, D ≥ 6 months", res["h1"],
         "6-month part rejected; 12-month part holds" if h1["durations"] == [12] else "killed"],
        ["Day-1 (ii)", "cut sets with a Chinese midstream node carry ≥ 80% of L", res["h2"], mid],
        ["Day-1 (iii)", "annual P(fail) in [1%, 10%]", res["h3"],
         "killed" if h3["L"] > 0.10 or est["ci95"][1] < 0.01 else "holds"],
        ["A1", "Spearman(attribution, concentration) ≥ 0.9 ⇒ concentration suffices", res["a1"],
         "killed: concentration suffices" if conc else "survives: the network adds information"],
        ["B1", "cut sets that disappear without re-export nodes are withdrawn", res["b1"],
         "applied"],
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


def certificates(R):
    """Recover each cut from its predecessors; old bundles sorted cuts but not witnesses."""
    following = {0: 3, 3: 6, 6: 12}
    C = {json.dumps(sorted([[p["v"], following[p["D"]]] for p in c["predecessors"]])): c
         for c in R["certificates"]}
    assert set(C) == {json.dumps(S) for S in R["cuts"]}
    return C


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
        cert = certificates(R)
        witnesses = []
        for S in x["cuts"]:
            c = cert[json.dumps(S)]
            assert len(c["predecessors"]) == len(S)
            assert all(p["phi"] <= R["theta"] + 1e-7 for p in c["predecessors"])
            witnesses.append([[p["v"], p["D"], p["phi"]/R["total"]]
                              for p in c["predecessors"]])
        configs[k.replace("base_", "")] = {
            "L": x["L"], "U": x["U"], "cuts": x["cuts"], "attribution": x["attribution"],
            "phi": [cert[json.dumps(S)]["phi"]/R["total"] for S in x["cuts"]],
            "predecessors": witnesses}
        countries = sorted({V[v][0] for S in x["cuts"] for v, _ in S})
        D = [d for d in (3, 6, 12) if d <= x["DJ"]]
        w = [sum(z for d, z in zip((3, 6, 12), risk["durations"]["weights"], strict=True)
                 if min(d, x["DJ"]) == e) for e in D]
        by_country = {}
        for country in countries:
            C = [[dict(S).get(v, 0) for v in range(len(V))] for S in x["cuts"]
                 if any(V[v][0] == country for v, _ in S)]
            by_country[country] = exact_union(V, risk["rates"]["p"], risk["rates"]["rho"],
                                               D, w, C)/x["L"]
        assert all(0 <= z <= 1 + 1e-9 for z in by_country.values())
        configs[k.replace("base_", "")]["country_union"] = by_country
    head = configs["a0.25_h0_s0_L6_D12"]["country_union"]
    assert all(math.isclose(head[c], z) for c, z in risk["attribution"]["country_union"].items())
    nodes = {"country": [v[0] for v in V], "product": [v[1] for v in V],
             "basis": [x["basis"] for x in N["nodes"]], "share": [x["share"] for x in N["nodes"]],
             "years": [12*x["capacity"] for x in N["nodes"]],
             "annual": [x["annual"] for x in N["nodes"]], "unit": [x["unit"] for x in N["nodes"]],
             "source": [x["source"] for x in N["nodes"]], "p": risk["rates"]["p"],
             "exposure": risk["rates"]["exposure"], "onsets": risk["rates"]["onsets"]}
    for a, e in risk["residual"].items():
        c = risk["configs"][f"base_a{float(a)}_h0_s0_L6_D12"]
        assert e["method"] == "lower_bound_plus_residual"
        assert e["interval_method"] == "clopper_pearson_binomial"
        assert e["L"] == c["L"] and e["estimate"] >= c["L"]
        assert math.isclose(e["estimate"], e["L"] + e["residual_events"]/e["n"])
        assert e["ci95"][0] <= c["U"] and e["ci95"][1] >= c["L"]
        assert not e["zero_residuals"] or e["ci95"][1] > e["L"]
    est = {f"{float(a)}": {k: risk[k][a] for k in ("IS", "MC", "residual")}
           for a in risk["residual"]}
    out = {"meta": {"run": run, "revision": risk["stamp"]["revision"],
                    "lock": risk["stamp"]["lock_sha256"], "rho": risk["rates"]["rho"],
                    "durations": risk["durations"], "D1": risk["D1"]},
           "nodes": nodes, "configs": configs, "estimates": est,
           "attribution": risk["attribution"]}
    return out, N, risk, checks


def severity(run):
    """Forward identified responses and certified scenarios, without the unused trade panel."""
    d = ROOT / "results" / run
    t = json.loads((d / "severity.json").read_text(encoding="utf-8"))
    assert t["registered"] and not t["stamp"]["dirty"]
    out = {k: t[k] for k in ("table", "excluded", "method", "bootstrap_draws")}
    out["run"] = run
    out["sectors"] = {}
    for s in ("liion", "pv", "joint"):
        x = json.loads((d / f"{s}.json").read_text(encoding="utf-8"))
        assert x["status"] == "optimal" and not x["stamp"]["dirty"]
        assert x["monotone"] and x["full_agrees_with_W1"]
        assert x["max_monotonicity_violation"] <= 1e-7
        assert all(0 <= f <= 1 for a in x["assigned_fractions"].values() for f in a.values())
        # Unlisted marks also use f=1; equivalence permits reusing W1, without clipping MC.
        same = all(x["assigned_fractions"]["central"].get(m, 1) == 1
                   for m in x["onsets_by_measure"])
        assert not same or (x["scenarios"]["central"]["failures"] ==
                            x["scenarios"]["full"]["failures"])
        out["sectors"][s] = {k: x[k] for k in ("scenarios", "full_outage", "hard", "S3",
                                               "unidentified_onset_share", "n")}
        out["sectors"][s]["same_as_full"] = same
    return out


def chemistry(cut_run, risk_run, sector, reference, law):
    """Certified recipe-choice cuts and exact country unions under the frozen onset law."""
    d = ROOT / "results"
    risk = json.loads((d / risk_run / f"{sector}.json").read_text())
    assert not risk["stamp"]["dirty"] and risk["network_unchanged"] and risk["rates_unchanged"]
    V, configs = law["nodes"], {}
    for key, x in risk["configs"].items():
        task, DJ = key.rsplit("_D", 1)
        R = json.loads((d / cut_run / "cuts" / f"{sector}_free_{task}.json").read_text())
        B = json.loads((d / cut_run / "cuts" / f"{sector}_bounded_{task}.json").read_text())
        assert R["complete"] and B["complete"] and R["cuts"] == B["cuts"]
        assert not R["stamp"]["dirty"] and R["nodes"] == V
        C = certificates(R)
        S = [s for s in R["cuts"] if all(t <= int(DJ) for _, t in s)]
        assert len(S) == len(x["attribution"])
        for s in S:
            c = C[json.dumps(s)]
            assert c["certified"] and c["gap"] <= 1e-6
            assert c["phi"] > R["config"]["alpha"]*R["total"] + 1e-7
            assert all(p["phi"] <= R["config"]["alpha"]*R["total"] + 1e-7
                       for p in c["predecessors"])
        D = [t for t in (3, 6, 12) if t <= int(DJ)]
        w = [sum(z for t, z in zip((3, 6, 12), law["durations"]["weights"], strict=True)
                 if min(t, int(DJ)) == e) for e in D]
        countries = sorted({V[v][0] for s in S for v, _ in s})
        by_country = {}
        for country in countries:
            cuts = [[dict(s).get(v, 0) for v in range(len(V))] for s in S
                    if any(V[v][0] == country for v, _ in s)]
            by_country[country] = exact_union(V, law["rates"]["p"], law["rates"]["rho"],
                                               D, w, cuts)/x["L"]
        configs[key] = {**x, "cuts": S, "country_union": by_country,
                        "phi": [C[json.dumps(s)]["phi"]/R["total"] for s in S],
                        "predecessors": [[[p["v"], p["D"], p["phi"]/R["total"]]
                                          for p in C[json.dumps(s)]["predecessors"]] for s in S]}
    for a, e in risk["residual"].items():
        assert e["L"] == configs[f"a{a}_h0_s0_L6_D12"]["L"] <= e["estimate"]
        assert e["ci95"][0] <= e["estimate"] <= e["ci95"][1]
    return {"nodes": reference["nodes"], "configs": configs, "residual": risk["residual"],
            "meta": {"cut_run": cut_run, "risk_run": risk_run,
                     "revision": risk["stamp"]["revision"]}}


def supply(run):
    """Read certified capacity sensitivities; these contain no probability refit."""
    out, revisions = [], set()
    for p in sorted((ROOT / 'results' / run).glob('*.json')):
        x = json.loads(p.read_text())
        assert x['complete'] and not x['stamp']['dirty']
        assert all(c['certified'] and c['gap'] <= 1e-6 for c in x['certificates'])
        assert x['baseline']['status'] == 'optimal' and x['baseline']['gap'] <= 1e-6
        revisions.add(x['stamp']['revision'])
        assert x['baseline_share'] <= 0.25 or x['cuts'] == [[]]
        out.append({'case': x['case'], 'choice': x['flexible'],
                    'nodes': len(x['network']['nodes']), 'cuts': len(x['cuts']),
                    'singletons': sum(len(s) == 1 for s in x['cuts']),
                    'baseline': x['baseline_share'], 'vanish': len(x['vanish']),
                    'appear': len(x['appear'])})
    assert len(out) == 14
    assert len(revisions) == 1
    return {'run': run, 'revision': revisions.pop(), 'cases': out}


def build(run, pv_run=None, joint_run=None, severity_run=None):
    data, N, risk, checks = block(run)
    layers = sorted(N["supply_ratio"], key=lambda p: -N["hhi"].get(p, 0))
    data.update({
        "layers": {"product": layers, "S": [N["supply_ratio"][p] for p in layers],
                   "hhi": [N["hhi"].get(p) for p in layers],
                   "top": [N["top_share"].get(p) for p in layers]},
        "tests": risk["tests"], "testRows": test_rows(risk["tests"]),
        "hard": {k: risk["hard"][k] for k in ("L", "U", "IS", "residual")},
        "hazards": risk["hazards"],
        "checks": {k: checks[k] for k in ("exports_vs_production", "reexport_flags",
                                          "site_coverage")}})
    for name, r in (("pv", pv_run), ("joint", joint_run)):
        if r:
            data[name] = block(r)[0]
    if severity_run:
        data["severity"] = severity(severity_run)
    data["choice"] = chemistry("chemistry-896581f", "chemistry-risk-d18c743", "liion", data, risk)
    data['supply'] = supply('supply-4ae36c1')
    if joint_run:
        data["joint_choice"] = chemistry("chemistry-896581f", "chemistry-risk-d18c743", "joint",
                                          data["joint"], load(joint_run)[2])
    ranges = {
        "Threshold α = 10–50%": [f"a{a}_h0_s0_L6_D12" for a in (0.1, 0.25, 0.5)],
        "Longest outage = 3–12 mo": [f"a0.25_h0_s0_L6_D{d}" for d in (3, 6, 12)],
        "Stock h = 0–3 mo": [f"a0.25_h{h}_s0_L6_D12" for h in (0, 1, 3)],
        "Spare σ = 0–0.5": [f"a0.25_h0_s{s}_L6_D12" for s in (0, 0.1, 0.5)],
        "Ramp = 6–24 mo (σ = 0.5)": [f"a0.25_h0_s0.5_L{t}_D12" for t in (6, 24)]}
    data["sensitivity"] = sorted(
        [{"label": label, "configs": keys, "values": [data["configs"][k]["L"] for k in keys]}
         for label, keys in ranges.items()], key=lambda r: max(r["values"]) - min(r["values"]),
        reverse=True)
    return data


def main():
    out = ROOT / "site" / "data.js"
    data = plain(build(*sys.argv[1:5]))
    out.write_text("window.DATA = " + json.dumps(data, separators=(",", ":"), ensure_ascii=False,
                                                 allow_nan=False) + ";\n", encoding="utf-8")
    print(f"{out}  {out.stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    main()
