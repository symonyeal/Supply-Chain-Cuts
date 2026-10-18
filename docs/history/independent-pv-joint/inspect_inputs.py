"""Summarize permitted frozen inputs without importing the project."""

import csv
import json
from collections import Counter
from pathlib import Path

R = Path(r"C:\Users\Yeal\Documents\My Projects\Chokepoint-Lab")


def rows(p):
    enc = "cp1252" if "MCS2026_Commodities" in p else "utf-8-sig"
    return list(csv.DictReader((R / p).open(encoding=enc, newline="")))


E = json.loads((R / "data/events/policy_events.json").read_text())["events"]
print("policy", len(E), Counter(tuple(sorted(e)) for e in E).most_common(2))
print("directions", Counter(x for e in E for x in e["directions"]))
print("onset", Counter((e["restrictive_onset_in_window"], e["left_truncated"], e["right_censored"]) for e in E))
print("fields", {k: E[-1][k] for k in E[-1] if k != "source_fields"})
X = rows("data/events/raw/oecd-battery-pv-2012-2024.csv")
print("raw", len(X), Counter(r["POLICY_DESCRIPTION"] for r in X))
print("DATI bad", Counter(r["OBS_VALUE"] for r in X if r["POLICY_DESCRIPTION"] == "DATI" and len(r["OBS_VALUE"]) != 10).most_common(20))
print("raw directions", Counter(r["OBS_VALUE"] for r in X if r["POLICY_DESCRIPTION"] == "DIR"))
print("policy source", Counter(e["source_file"] for e in E))
print("policy nonempty", sum(bool(e["products"]) for e in E))
print("policy duplicates", sum(len(e["reported_end_dates"]) > 1 for e in E))
print("no effective", [{k: e[k] for k in ("country", "hs6", "measure_type", "policy_variation", "effective_date", "directions", "restrictive_onset_in_window")} for e in E if not e["effective_date"]][:20])
print("edge effective", [{k: e[k] for k in ("country", "hs6", "effective_date", "directions", "restrictive_onset_in_window")} for e in E if e["effective_date"] and (e["effective_date"].endswith("-01-01") or any(d in {"revision", "extension", "indeterminable"} for d in e["directions"]))][:30])
for e in E:
    if len(e["reported_end_dates"]) > 1:
        print("end dates", {k: e[k] for k in ("id", "effective_date", "reported_end_dates", "end_date", "right_censored")})
        break
X = rows("data/raw/usgs/MCS2026_Commodities_Data.csv")
print("MCS countries", sorted({r["Country"] for r in X if r["Year"] == "2024" and "World" in r["Section"] and r["Commodity"] in {"Aluminum", "Lithium", "Cobalt", "Nickel", "Manganese", "Copper", "Graphite (Natural)"}}))
for p in ("pv", "joint"):
    a = json.loads((R.parent / "Chokepoint-Lab-brief/independent-inputs" / f"{p}-cuts.json").read_text())
    print(p, len(a["cuts"]), Counter(len(c["losses"]) for c in a["cuts"]))
    print("cut nodes", sorted({(v["country"], v["product"]) for c in a["cuts"] for v in c["losses"]}))
