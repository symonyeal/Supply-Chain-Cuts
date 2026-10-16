"""Build site/data.js from a result bundle: python analysis/build_site.py RUN_ID [PV_RUN_ID].

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


def load(run):
    d = ROOT / "results" / run
    cuts = {x.stem: json.loads(x.read_text(encoding="utf-8")) for x in (d / "cuts").glob("*.json")}
    return (json.loads((d / "network.json").read_text(encoding="utf-8")),
            json.loads((d / "data_checks.json").read_text(encoding="utf-8")),
            json.loads((d / "risk.json").read_text(encoding="utf-8")), cuts)


def build(run, pv_run=None):
    net, checks, risk, cuts = load(run)
    N = net["liion"]
    V = risk["nodes"]
    assert V == [[x["country"], x["product"]] for x in N["nodes"]]
    for R in cuts.values():
        assert all(c["certified"] for c in R["certificates"]), R["task"]
    configs = {}
    for k, x in risk["configs"].items():
        assert 0 <= x["L"] <= x["U"] <= 1
        R = cuts["_".join(k.split("_")[:-1])]
        phi = {json.dumps(S): c["phi"]/R["total"] for S, c in zip(R["cuts"], R["certificates"],
                                                                  strict=True)}
        configs[k.replace("base_", "")] = {
            "L": x["L"], "U": x["U"], "cuts": x["cuts"], "attribution": x["attribution"],
            "phi": [phi[json.dumps(S)] for S in x["cuts"]]}
    est = {f"{float(a)}": {"IS": risk["IS"][a], "MC": risk["MC"][a]} for a in risk["IS"]}
    nodes = {"country": [v[0] for v in V], "product": [v[1] for v in V],
             "basis": [x["basis"] for x in N["nodes"]], "share": [x["share"] for x in N["nodes"]],
             "years": [12*x["capacity"] for x in N["nodes"]],
             "annual": [x["annual"] for x in N["nodes"]], "unit": [x["unit"] for x in N["nodes"]],
             "source": [x["source"] for x in N["nodes"]], "p": risk["rates"]["p"],
             "exposure": risk["rates"]["exposure"], "onsets": risk["rates"]["onsets"]}
    layers = sorted(N["supply_ratio"], key=lambda p: -N["hhi"].get(p, 0))
    data = {
        "meta": {"run": run, "revision": risk["stamp"]["revision"],
                 "lock": risk["stamp"]["lock_sha256"], "rho": risk["rates"]["rho"],
                 "durations": risk["durations"], "D1": risk["D1"]},
        "nodes": nodes,
        "layers": {"product": layers, "S": [N["supply_ratio"][p] for p in layers],
                   "hhi": [N["hhi"].get(p) for p in layers],
                   "top": [N["top_share"].get(p) for p in layers]},
        "configs": configs, "estimates": est, "tests": risk["tests"], "hard": {
            k: risk["hard"][k] for k in ("L", "U", "IS")},
        "hazards": risk["hazards"], "checks": {k: checks[k] for k in (
            "exports_vs_production", "reexport_flags", "site_coverage")},
        "attribution": risk["attribution"],
    }
    if pv_run:
        _, _, prisk, _ = load(pv_run)
        data["pv"] = {"risk": {k: prisk[k] for k in ("configs", "IS", "MC", "tests")
                               if k in prisk}, "nodes": prisk["nodes"]}
    return data


def main():
    out = ROOT / "site" / "data.js"
    data = plain(build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
    out.write_text("window.DATA = " + json.dumps(data, separators=(",", ":"), ensure_ascii=False,
                                                 allow_nan=False) + ";\n", encoding="utf-8")
    print(f"{out}  {out.stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    main()
