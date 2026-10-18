"""Append source-audit evidence without changing the computed headlines."""

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

R = Path(r"C:\Users\Yeal\Documents\My Projects\Chokepoint-Lab")
W = Path(__file__).resolve().parent


def rows(p, enc="utf-8-sig"):
    return list(csv.DictReader((R / p).open(encoding=enc, newline="")))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


r = json.loads((W / "results.json").read_text(encoding="utf-8"))
s = json.loads((W / "source_trace.json").read_text(encoding="utf-8"))
before = (W / "results-before-source-audit.json")
if not before.exists():
    before.write_bytes((W / "results.json").read_bytes())
checks = {}
myb = s["workbooks"]["data/raw/usgs/myb1-2023-cobalt.xlsx"]["T8"]
checks["MYB_positive_refinery_cells"] = [
    {"iso3": x["iso3"], "value": float(x["value"]),
     "workbook": myb[int(re.search(r"\d+$", x["sheet_cell"])[0])-1][3]}
    for x in rows("data/raw/usgs/myb2023_cobalt_refinery.csv") if x["value"]]
checks["MYB_all_positive_cells_match"] = all(x["value"] == x["workbook"] for x in checks["MYB_positive_refinery_cells"])
chile = s["workbooks"]["data/raw/cochilco/production_1996_2025.xlsx"]
checks["Cochilco_all_five_cells_match"] = all(float(x["value"]) == chile[x["cell"]] for x in rows("data/raw/cochilco/lithium_chemicals_2024.csv"))
txt = s["pdf"]["data/raw/xu2020/supplement.pdf"]
pack = txt["42"].split("Mid-size BEVs", 1)[1].split("Large BEVs", 1)[0]
bom = {m: [float(v) for v in z.split()] for m, z in re.findall(r"(?m)^(Li|Ni|Co|Mn|Al|Cu|Graphite|Si)\s+([\d. ]+)\s*$", pack)}
checks["Xu_material_cells"] = [
    {"chemistry": x["chemistry"], "material": x["material"], "value": float(x["kg_per_pack"]),
     "PDF": bom[x["material"]][0 if x["chemistry"] == "LFP" else 4]}
    for x in rows("data/raw/xu2020/bom_mid_size_bev.csv") if x["chemistry"] in {"LFP", "NCM622"}]
checks["Xu_all_16_material_cells_match"] = all(x["value"] == x["PDF"] for x in checks["Xu_material_cells"])
checks["Xu_66_kWh_pack_match"] = "Mid-size BEVs 194 291 169 66" in txt["30"]
checks["Xu_129_174_Wh_per_kg_match"] = "Mid-size BEVs 129 178 160 163 174" in txt["31"]
checks["coverage"] = {k: v for k, v in s["coverage"].items() if k != "country_labels"}
checks["coverage_all_1521_rows_exact"] = (s["coverage"]["PDF_rows"] == s["coverage"]["frozen_rows"] == 1521
    and not any(s["coverage"][k] for k in ("unresolved_country_labels", "PDF_only", "frozen_only", "cell_differences")))
checks["national_acts"] = {
    "CHN-MOFCOM-2023-39": {"effective_date": "2023-12-01", "raw_date_clause_found": True,
                            "scope_checked": "Licensing for specified natural flake and artificial graphite items; not a universal ban."},
    "CHN-MOFCOM-2024-46-GRAPHITE": {"effective_date": "2024-12-03", "raw_date_clause_found": True,
                                    "scope_checked": "Stricter final-user/final-use review for graphite dual-use exports to USA; effective on publication."},
    "IDN-ESDM-11-2019": {"effective_date": "2020-01-01", "raw_date_clause_found": True,
                         "scope_checked": "Nickel ore below 1.7 percent Ni; ministry release dated 2019-09-02."},
    "ZWE-SI213-2022": {"effective_date": "2022-12-16", "raw_date_clause_found": True,
                       "scope_checked": "Lithium-bearing ore/unbeneficiated lithium subject to written permit, with exceptions; Gazette date and immediate effect."},
}
checks["national_HTML_all_search_terms_found"] = all(v is not None for a in s["national_act_raw_excerpts"].values() for v in a.values())
zwe = s["pdf"]["data/events/raw/zimbabwe-si213-2022.pdf"]
checks["Zimbabwe_date_and_immediate_effect_found"] = "immediate effect" in zwe["1"] and "16th December, 2022" in zwe["2"]

X = rows("data/raw/usgs/MCS2026_Commodities_Data.csv", "cp1252")
x = [float(z["Value"].replace(",", "")) for z in X if z["Year"] == "2024" and z["Commodity"] == "Cobalt"
     and "World" in z["Section"] and z["Statistics_detail"] == "Mine production" and z["Country"] != "Other countries"]
full_co = sum(t*t for t in x)/sum(x)**2
q = defaultdict(float)
for x in rows("data/raw/baci/BACI_HS12_Y2024_V202601_selected.csv"):
    if x["k"] == "850760" and re.fullmatch(r"\d+(?:\.\d+)?", x["q"]):
        q[x["i"]] += float(x["q"])
iso = {x["country_iso3"]: x["country_code"] for x in rows("data/raw/baci/country_codes_V202601.csv")}
cam = {i: v*r["network"]["pack_Wh_per_kg"]/1e6*r["network"]["CAM_kg_per_kWh"] for i, v in q.items()}
cam[iso["CHN"]] = 3100.
full_cam = sum(t*t for t in cam.values())/sum(cam.values())**2
checks["HHI_reporting_difference"] = {
    "cause": "Preserved result HHI sums retained squared shares; documented HHI sums all positive origins. Both use the pre-cutoff total. No capacity or headline is affected.",
    "mine_co_preserved": r["network"]["layers"]["mine_co"]["HHI"], "mine_co_all_origins": full_co,
    "cam_preserved": r["network"]["layers"]["cam"]["HHI"], "cam_all_origins": full_cam,
}
checks["duration_record_rule"] = {
    "counts_3_6_12": [4, 3, 169], "excluded_short_censored": len(r["events"]["short_censored_excluded"]),
    "note": "Each record is counted once if any mapped onset node-year is surveyed, including below-cutoff origins. The four OECD IDs linked in acts.yaml remain separate records in the duration sample; node-year onsets are deduplicated.",
    "initial_over_deduplicated_counts_3_6_12": [2, 3, 167],
}
rates = r["rates"]["node_rates"]
pv = {"polysilicon", "wafer", "pv_cell", "module"}
checks["node_year_totals"] = {s: {"N": sum(x["N"] for x in rates if (x["product"] in pv) == (s == "pv")),
                                  "K": sum(x["K"] for x in rates if (x["product"] in pv) == (s == "pv"))} for s in ("liion", "pv")}
checks["singleton_summary"] = {
    "PV_6_month_max_phi": max(x["phi"] for x in r["sectors"]["pv"]["singletons"] if x["duration"] == 6),
    "joint_max_phi": max(x["phi"] for x in r["sectors"]["joint"]["singletons"]),
    "PV_failing": [x for x in r["sectors"]["pv"]["singletons"] if x["fails"]],
    "joint_failing_count": sum(x["fails"] for x in r["sectors"]["joint"]["singletons"]),
}
for p, h in s["sha256"].items():
    r["input_sha256"][str(R / p)] = h
lock = {str(R / x["path"]): x["sha256"] for x in json.loads((R / "SOURCES.lock").read_text())["sources"]}
checks["source_trace_lock_mismatches"] = [p for p, h in s["sha256"].items() if str(R / p) in lock and h != lock[str(R / p)]]
checks["limits"] = [
    "No production implementation, pre-existing project Python, tests, analysis or results were read or imported. Named cut lists were permitted comparison inputs.",
    "Raw OECD event reconstruction and post-hoc raw-PDF coverage verification are independent. policy_events.json supplies comparison facts and labels, not numerical onsets or lengths.",
    "National-act dates and legal scope were inspected in frozen raw text. Product mapping, merge links and censoring at 2024-12-31 remain curated assumptions; no independent legal completeness audit was attempted.",
    "MIIT and Fraunhofer frozen numerical CSV transcriptions were used; they were not independently re-transcribed from their original publications. USGS MYB, Cochilco and Xu numbers were traced to frozen workbook/PDF originals.",
    "Complete enumeration is through support three for this fixed-mix h=sigma=0 instance only. No result for larger supports, other chemistries, inventories or expansion is certified.",
    "The exact cut-union probability is a conditional model lower bound, computed in floating-point arithmetic. Data uncertainty, predictive rate validity and the true total failure probability were not independently estimated.",
]
checks["original_results_sha256"] = sha(before)
checks["artifact_sha256"] = {p: sha(W / p) for p in ("recompute.py", "trace_sources.py", "finalize_audit.py", "source_trace.json", "coverage_from_pdf.csv", "enumeration.json")}
r["source_audit"] = checks
(W / "results.json").write_text(json.dumps(r, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
v = json.loads((W / "results.json").read_text(encoding="utf-8"))
assert v["sectors"] == json.loads(before.read_text(encoding="utf-8"))["sectors"]
print(json.dumps({"source_checks": {k: z for k, z in checks.items() if isinstance(z, bool)},
                  "HHI": checks["HHI_reporting_difference"], "source_hash_mismatches": checks["source_trace_lock_mismatches"],
                  "L_readback": {s: v["sectors"][s]["probability"]["L"] for s in ("pv", "joint")}}, indent=2))
