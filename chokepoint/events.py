"""Policy-onset node-years from the OECD Inventory and national acts (design §5).

Exposure. Node (c, p) is observed in year t iff the OECD survey covers a commodity of p in
country c in year t (OECD 2026 coverage table). Unsurveyed node-years are missing, never 0.
Onset. An OECD record with a restrictive onset (introduction or increase) effective in t,
or an in-window national act effective in t, for a product of the node. Acts count only in
surveyed node-years: a positive record without a survey establishes no exposure.
"""
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

ALIAS = {"mine_graphite": "graphite", "li_hydroxide": "li_carbonate"}
YEARS = np.arange(2012, 2025)
SUSPENDED = ("suspension", "partial_suspension", "licensing_announced_then_suspended")
HARD = ("M3", "M4")                     # OECD export quota, export prohibition


def _records(root):
    E = json.loads((root / "data/events/policy_events.json").read_text(encoding="utf-8"))
    A = json.loads((root / "data/events/acts.yaml").read_text(encoding="utf-8"))
    out = []
    for e in E["events"]:
        if e["restrictive_onset_in_window"]:
            out.append({"id": e["id"], "country": e["country"], "products": e["products"],
                        "year": int(e["effective_date"][:4]), "measure": e["measure_type"],
                        "days": e["duration_days_lower_bound"] if e["right_censored"]
                        else e["duration_days_observed"], "censored": e["right_censored"]})
    for x in A["acts"]:
        if x["in_estimation_window"] and x["products"] and x["measure_type"] not in SUSPENDED:
            start = date.fromisoformat(x["effective_date"])
            end = date.fromisoformat(x.get("end_date") or x.get("censor_date") or "2024-12-31")
            out.append({"id": x["id"], "country": x["country"], "products": x["products"],
                        "year": start.year, "measure": x["measure_type"],
                        "days": (end - start).days, "censored": bool(x.get("right_censored"))})
    return out


def node_years(V, root=Path("."), hard=False):
    """Return Y[v, t] ∈ {0, 1, nan} over YEARS, the onset ids behind each 1, and records.

    INPUT  V ..... (country, product) nodes
           hard .. count only quotas and prohibitions (OECD M3, M4; prohibiting acts)
    OUTPUT Y, onset ids by 'c:p:year', and the records that create an onset (for durations)
    """
    root = Path(root)
    pm = json.loads((root / "data/events/product_map.json").read_text(encoding="utf-8"))
    surveyed = set()
    for r in csv.DictReader((root / "data/events/oecd_coverage.csv").open(encoding="utf-8")):
        if r["surveyed"] == "1":
            for p in pm["coverage_commodity_to_products"].get(r["commodity"], []):
                surveyed.add((r["country"], ALIAS.get(p, p), int(r["year"])))
    onsets, used = defaultdict(list), []
    for x in _records(root):
        if hard and x["measure"] not in HARD and "prohibition" not in x["measure"]:
            continue
        keys = {(x["country"], ALIAS.get(p, p), x["year"]) for p in x["products"]}
        if keys & surveyed:
            used.append(x)
        for key in keys & surveyed:
            onsets[key].append(x["id"])
    Y = np.full((len(V), len(YEARS)), np.nan)
    for i, (c, p) in enumerate(V):
        for t, y in enumerate(YEARS):
            if (c, p, int(y)) in surveyed:
                Y[i, t] = float(bool(onsets.get((c, p, int(y)))))
    return Y, {f"{c}:{p}:{y}": ids for (c, p, y), ids in sorted(onsets.items())}, used
