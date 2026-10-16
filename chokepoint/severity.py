"""Registered W2 export event study; first full calendar year is not production loss."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from chokepoint.events import node_years


def exports(root=Path(".")):
    """Complete exporter–HS6–year tonnes; an existing missing q makes the cell unknown."""
    root = Path(root)
    countries = {int(x["country_code"]): x["country_iso3"] for x in csv.DictReader(
        (root / "data/raw/baci/country_codes_V202601.csv").open(encoding="utf-8"))}
    Q, missing = defaultdict(float), set()
    for t in range(2012, 2024):
        p = root / f"data/raw/baci/BACI_HS12_Y{t}_V202601_selected.csv"
        for x in csv.DictReader(p.open(encoding="utf-8")):
            key = countries[int(x["i"])], x["k"], t
            if not x["q"].strip():
                missing.add(key)
            else:
                Q[key] += float(x["q"])
    return Q, missing


def cohorts(root=Path(".")):
    """Isolated surveyed onsets with complete normalized volume and untreated controls."""
    root = Path(root)
    pm = json.loads((root / "data/events/product_map.json").read_text(encoding="utf-8"))
    concordance = json.loads((root / "data/events/hs07_hs12.json").read_text(encoding="utf-8"))
    E = json.loads((root / "data/events/policy_events.json").read_text(encoding="utf-8"))["events"]
    _, _, used = node_years([], root)
    ids = {e["id"] for e in used}
    Q, missing = exports(root)
    available = {h for _, h, _ in Q}
    surveyed = set()
    for x in csv.DictReader((root / "data/events/oecd_coverage.csv").open(encoding="utf-8")):
        if x["surveyed"] == "1":
            for p in pm["coverage_commodity_to_products"].get(x["commodity"], []):
                surveyed.add((x["country"], p, int(x["year"])))
    active = defaultdict(list)
    for e in E:
        h = concordance["one_to_one"].get(e["hs6"])
        if h:
            start = int(e["effective_date"][:4]) if e.get("effective_date") else 0
            end = int(e["end_date"][:4]) if e.get("end_date") else 2024
            active[e["country"], h].append((start, end, e["measure_type"]))
    candidates = defaultdict(list)
    excluded = Counter()
    for e in E:
        if e["id"] not in ids:
            continue
        t = int(e["effective_date"][:4])
        if not 2014 <= t <= 2022:
            excluded["outside_onset_window"] += 1
            continue
        h = concordance["one_to_one"].get(e["hs6"])
        if not h:
            excluded["not_one_to_one_concordance"] += 1
        elif h not in available:
            excluded["HS12_not_in_frozen_selection"] += 1
        else:
            candidates[e["country"], e["hs6"], h, e["measure_type"], t].append(e["id"])
    excluded["national_act_without_verified_HS6"] = len(ids - {e["id"] for e in E})
    countries = sorted({c for c, _, _ in surveyed})
    events, overlapping = [], []
    for (c, h07, h, m, t), ids in sorted(candidates.items()):
        years = list(range(t-2, t+2))

        observed = {d for d in countries if all(any((d, p, y) in surveyed
                    for p in pm["hs6_to_products"][h07]) for y in years)
                    and not any((d, h, y) in missing for y in years) and Q[d, h, t-1] > 0}
        if c not in observed:
            excluded["treated_incomplete_or_zero_baseline"] += 1
            continue
        controls = [d for d in sorted(observed) if d != c and not any(
            a <= t+1 and b >= t-2 for a, b, _ in active[d, h])]
        if not controls:
            excluded["no_surveyed_untreated_controls"] += 1
            continue
        C = [c, *controls]
        row = {"country": c, "hs07": h07, "hs12": h, "measure": m, "onset_year": t,
               "ids": ids, "countries": C,
               "Y": [[Q[d, h, y]/Q[d, h, t-1] for y in years] for d in C]}
        if any(a <= t+1 and b >= t-2 and kind != m for a, b, kind in active[c, h]):
            overlapping.append(row)
            excluded["overlapping_measure_type"] += 1
        else:
            events.append(row)
    return events, overlapping, dict(excluded)


def effect(e, counts=None):
    """Within-event DiD at relative years (-2,0,+1), baseline -1, equal control weights."""
    Y = np.asarray(e["Y"])
    w = np.ones(len(Y)) if counts is None else np.array([counts[c] for c in e["countries"]])
    if not w[0] or not w[1:].sum():
        return None
    d = Y[:, [0, 2, 3]] - Y[:, [1]]
    return d[0] - np.average(d[1:], axis=0, weights=w[1:])


def estimate(events, B=2000, seed=6):
    """Stacked exporter/year FE DiD; country-cluster bootstrap, registered W2 design."""
    groups = {m: [e for e in events if e["measure"] == m] for m in sorted(
        {e["measure"] for e in events} | {"M1", "M3", "M4", "M6", "M14"})}
    groups["M3_M4"] = [e for e in events if e["measure"] in ("M3", "M4")]
    countries = sorted({c for e in events for c in e["countries"]})
    rng, samples = np.random.default_rng(seed), {m: [] for m in groups}
    for _ in range(B):
        counts = Counter(rng.choice(countries, len(countries))) if countries else Counter()
        for m, E in groups.items():
            values = [(effect(e, counts), counts[e["country"]]) for e in E]
            values = [(x, w) for x, w in values if x is not None]
            if values:
                samples[m].append(np.average([x for x, _ in values], axis=0,
                                             weights=[w for _, w in values]))
    out = {}
    for m, E in groups.items():
        n, C = len(E), len({e["country"] for e in E})
        b = np.mean([effect(e) for e in E], axis=0).tolist() if E else None
        ci = np.quantile(samples[m], [0.025, 0.975], axis=0).T.tolist() if samples[m] else None
        pretrend = bool(ci and not ci[0][0] <= 0 <= ci[0][1])
        identified = n >= 5 and not pretrend and ci is not None
        loss = -b[2] if b else None
        interval = [-ci[2][1], -ci[2][0]] if ci else None
        threshold = 0.2 if m == "M1" else 0.5
        verdict = "untestable"
        if identified and m in ("M1", "M3", "M4", "M3_M4"):
            lo, hi = interval
            verdict = ("supported" if hi < threshold else "killed" if lo >= threshold
                       else "inconclusive") if m == "M1" else (
                       "supported" if lo >= threshold else "killed" if hi < threshold
                       else "inconclusive")
        out[m] = {"events": n, "treated_countries": C, "HS6": len({e["hs12"] for e in E}),
                  "relative_years": [-2, 0, 1], "beta": b, "ci95": ci, "loss": loss,
                  "loss_ci95": interval, "pretrend": pretrend, "weak_inference": C < 10,
                  "identified": identified, "verdict": verdict,
                  "f": float(np.clip(loss, 0, 1)) if identified else 1.0,
                  "f_basis": "export_response_scenario" if identified else "full_loss_fallback",
                  "bootstrap_draws": len(samples[m])}
    return out
