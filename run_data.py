"""Networks and data reconciliations (design §3): python run_data.py RUN_ID.

Writes results/RUN_ID/network.json (Li-ion, PV, joint) and results/RUN_ID/data_checks.json.
Nothing is rescaled to reconcile sources; differences are reported.
"""
import csv
import json
import sys
from pathlib import Path

from chokepoint.events import node_years
from chokepoint.fetch import stamp
from chokepoint.net import build, reexport_flags


def slim(N):
    keep = ("sector", "nodes", "a", "requirement", "supply_ratio", "finals", "demand_scale",
            "coverage", "cutoff", "ncm", "capacity_basis", "hhi", "top_share",
            "missing_baci_quantities", "unparsed_usgs", "annual_totals")
    return {k: N[k] for k in keep}


def main():
    root, run = Path("."), Path("results") / sys.argv[1]
    run.mkdir(parents=True, exist_ok=True)
    voltage = float(sys.argv[2]) if len(sys.argv) > 2 else None
    eu = len(sys.argv) > 3 and sys.argv[3] == 'eu-sold'
    nets = {s: build(sector=s, japan_voltage=voltage, eu_sold=eu)
            for s in ("liion", "pv", "joint")}
    L = nets["liion"]
    miit = {x["product"]: float(x["value"]) for x in csv.DictReader(
        (root / "data/raw/miit/production_2024.csv").open()) if x["statistic"] == "production"}
    trade = build(basis="trade", cutoff=0)
    prod = {(x["country"], x["product"]): x["annual"] for x in build(
        cutoff=0, japan_voltage=voltage, eu_sold=eu)["nodes"]}
    exports = {(x["country"], x["product"]): x["annual"] for x in trade["nodes"]
               if x["basis"] == "trade"}
    recon = [{"country": c, "product": p, "exports": e, "production": prod[c, p],
              "ratio": e/prod[c, p]} for (c, p), e in sorted(exports.items())
             if (c, p) in prod and p in ("cell", "li_carbonate", "refined_co")
             and abs(prod[c, p] - e) > 1e-9]
    research = {(r["country"], {"mine_graphite": "graphite", "li_hydroxide": "li_carbonate"}
                 .get(r["product"], r["product"]), int(r["year"]))
                for r in csv.DictReader((root / "data/events/observed_node_years.csv").open())
                if r["restrictive_onset"] == "1"}
    V = [(x["country"], x["product"]) for x in L["nodes"]]
    _, ids, _ = node_years(V, root)
    derived = {(c, p, int(y)) for c, p, y in (k.split(":") for k in ids)}
    sites = json.loads((root / "data/sites/coverage.json").read_text(encoding="utf-8"))
    checks = {
        "stamp": stamp(root),
        "miit_parts_vs_total": {"parts": miit["li_ion_consumer_cell"] + miit[
            "li_ion_storage_cell"] + miit["li_ion_traction_cell"], "total": miit["li_ion_cell"]},
        "exports_vs_production": recon,
        "comtrade_tariff_lines_vs_baci": json.loads(
            (root / "data/raw/supplement/reconciliation.json").read_text()),
        "japan_nominal_voltage": voltage,
        "german_sold_carbonate_proxy": eu,
        "bgs": "not used: licence unresolved",
        "reexport_flags": reexport_flags(L),
        "events_vs_research_csv": {
            "only_derived": sorted(map(list, (derived - research) & {k for k in derived})),
            "only_research_on_nodes": sorted(map(list, {x for x in research - derived
                                                        if x[:2] in set(V)}))},
        "site_coverage": {"threshold": sites["threshold"], "passed": sites["coverage_test_passed"],
                          "mode": sites["natural_hazard_mode"],
                          "layers": {x["product"]: x["verified_located_capacity_share"]
                                     for x in sites["layers"]}},
    }
    (run / "network.json").write_text(json.dumps({s: slim(N) for s, N in nets.items()},
                                                 indent=1) + "\n", encoding="utf-8")
    (run / "data_checks.json").write_text(json.dumps(checks, indent=1) + "\n", encoding="utf-8")
    print(len(L["nodes"]), "Li-ion nodes;", len(nets["pv"]["nodes"]), "PV;",
          len(nets["joint"]["nodes"]), "joint;", len(recon), "export/production pairs")


if __name__ == "__main__":
    main()
