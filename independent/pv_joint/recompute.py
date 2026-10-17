"""Recompute the fixed-mix PV/joint model from permitted frozen inputs.

INPUT   Frozen primary tables, DATA/MODEL, and named duration cut lists.
OUTPUT  results.json, network.json, raw_events.json, node_years.csv.
"""

import argparse
import csv
import hashlib
import itertools
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from functools import cache
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.optimize import linprog, minimize, minimize_scalar
from scipy.special import betaln

a = argparse.ArgumentParser(description=__doc__)
a.add_argument("--root", type=Path, required=True, help="Frozen project input root.")
a.add_argument(
    "--out", type=Path, required=True, help="Directory for independent result artifacts."
)
a.add_argument("--pv-cuts", type=Path, required=True, help="Named PV cut-list JSON.")
a.add_argument("--joint-cuts", type=Path, required=True, help="Named joint cut-list JSON.")
args = a.parse_args()
R, W = args.root.resolve(), args.out.resolve()
C = {"pv": args.pv_cuts.resolve(), "joint": args.joint_cuts.resolve()}
W.mkdir(parents=True, exist_ok=True)
H = {}


def read(p, enc="utf-8-sig"):
    """Read permitted input bytes and record SHA-256."""
    p = Path(p)
    if not p.is_absolute():
        p = R / p
    b = p.read_bytes()
    H[str(p)] = hashlib.sha256(b).hexdigest()
    return b.decode(enc)


def rows(p, enc="utf-8-sig"):
    return list(csv.DictReader(read(p, enc).splitlines()))


def dump(p, x):
    (W / p).write_text(json.dumps(x, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def number(x):
    x = x.replace(",", "").strip()
    return float(x) if re.fullmatch(r"\d+(?:\.\d+)?", x) else None


def network():
    """Construct annual country-product capacities and sector requirements."""
    Z = rows("data/raw/baci/country_codes_V202601.csv")
    iso = {int(r["country_code"]): r["country_iso3"] for r in Z}
    names = {r["country_name"].casefold(): r["country_iso3"] for r in Z}
    names.update(
        {
            "congo (kinshasa)": "COD",
            "russia": "RUS",
            "vietnam": "VNM",
            "korea, republic of": "KOR",
            "korea, north": "PRK",
            "turkey": "TUR",
            "united states": "USA",
            "côte d’ivoire": "CIV",
            "c�te d�ivoire": "CIV",
            "tanzania": "TZA",
        }
    )
    X = rows("data/raw/usgs/MCS2026_Commodities_Data.csv", "cp1252")
    A, basis = defaultdict(dict), {}
    specs = {
        "Lithium": ("mine_li", "Mine production"),
        "Cobalt": ("mine_co", "Mine production"),
        "Nickel": ("mine_ni", "Mine production"),
        "Manganese": ("mine_mn", "Mine production"),
        "Graphite (Natural)": ("graphite", "Mine production"),
        "Copper": ("refined_cu", "Refinery production"),
        "Aluminum": ("aluminium", "Smelter production"),
    }
    unparsed = []
    for r in X:
        if r["Year"] != "2024" or "World" not in r["Section"] or r["Commodity"] not in specs:
            continue
        p, stat = specs[r["Commodity"]]
        if r["Statistics_detail"] != stat:
            continue
        x, c = number(r["Value"]), names.get(r["Country"].casefold())
        if x is None or c is None:
            unparsed.append({"product": p, "country": r["Country"], "value": r["Value"]})
            continue
        A[p][c] = x * (1 if r["Unit"] == "thousand metric tons" else 0.001)
        basis[c, p] = "production"
    Q, missing = {}, {}
    for rev in (12, 22):
        Q[rev] = defaultdict(lambda: defaultdict(float))
        missing[rev] = 0
        for r in rows(f"data/raw/baci/BACI_HS{rev}_Y2024_V202601_selected.csv"):
            x = number(r["q"])
            if x is None:
                missing[rev] += 1
                continue
            Q[rev][r["k"]][iso[int(r["i"])]] += x
    Z = rows("data/raw/xu2020/bom_mid_size_bev.csv")
    b0 = {
        ch: {
            r["material"]: float(r["kg_per_pack"]) / float(r["pack_kwh"])
            for r in Z
            if r["chemistry"] == ch
        }
        for ch in ("LFP", "NCM622")
    }
    b = {m: (b0["LFP"][m] + b0["NCM622"][m]) / 2 for m in b0["LFP"]}
    C0 = b0["LFP"]["Li"] * (6.94 + 55.845 + 30.974 + 4 * 15.999) / 6.94
    C1 = (
        sum(b0["NCM622"][m] for m in ("Li", "Ni", "Co", "Mn"))
        + b0["NCM622"]["Li"] * 2 * 15.999 / 6.94
    )
    P = (
        sum(
            b0["NCM622"][m] * (1 + 2 * 17.007 / a)
            for m, a in (("Ni", 58.6934), ("Co", 58.9332), ("Mn", 54.938))
        )
        / 2
    )
    C = (C0 + C1) / 2
    Z = rows("data/raw/xu2020/specific_energy.csv")
    E0 = {r["chemistry"]: float(r["wh_per_kg"]) for r in Z}
    E = 1 / (0.5 / E0["LFP"] + 0.5 / E0["NCM622"])
    Z = rows("data/raw/miit/production_2024.csv")
    M = {(r["product"], r["statistic"]): float(r["value"]) for r in Z}
    A["cell"] = {c: q * E / 1e6 for c, q in Q[12]["850760"].items()}
    A["cell"]["CHN"] = M["li_ion_cell", "production"]
    for c in A["cell"]:
        basis[c, "cell"] = "production" if c == "CHN" else "trade"
    for p, a in (("cam", C), ("pcam", P), ("aam", b["Graphite"])):
        A[p] = {c: q * a for c, q in A["cell"].items()}
        for c in A[p]:
            basis[c, p] = "imputed"
    for p, key in (("cam", "cathode_active_material"), ("aam", "anode_active_material")):
        A[p]["CHN"] = M[key, "production"] / 1000
        basis["CHN", p] = "production"
    for p, k in (("li_carbonate", "283691"), ("refined_ni", "750210")):
        A[p] = {c: q / 1000 for c, q in Q[12][k].items()}
        for c in A[p]:
            basis[c, p] = "trade"
    A["li_carbonate"]["CHN"] = (
        M["battery_grade_lithium_carbonate", "production"]
        + M["battery_grade_lithium_hydroxide", "production"] * 73.891 / (2 * 41.964)
    ) / 1000
    Z = rows("data/raw/cochilco/lithium_chemicals_2024.csv")
    A["li_carbonate"]["CHL"] = next(float(r["value"]) / 1000 for r in Z if r["cell"] == "AD21")
    basis["CHN", "li_carbonate"] = basis["CHL", "li_carbonate"] = "production"
    for r in rows("data/raw/usgs/myb2023_cobalt_refinery.csv"):
        if r["value"] and float(r["value"]) > 0:
            A["refined_co"][r["iso3"]] = float(r["value"]) / 1000
            basis[r["iso3"], "refined_co"] = "production"
    for c, q in Q[12]["380110"].items():
        A["graphite"][c] = A["graphite"].get(c, 0) + q / 1000
        basis[c, "graphite"] = "imputed"
    si = float(rows("data/raw/fraunhofer/silicon_usage_2024.csv")[0]["value"])
    edges = [
        ("mine_li", "li_carbonate", 1 / 5.323),
        ("li_carbonate", "cam", 5.323 * b["Li"] / C),
        ("pcam", "cam", P / C),
        ("mine_co", "refined_co", 1),
        ("mine_ni", "refined_ni", 1),
        ("refined_co", "pcam", b["Co"] / P),
        ("refined_ni", "pcam", b["Ni"] / P),
        ("mine_mn", "pcam", b["Mn"] / P),
        ("graphite", "aam", 1),
        ("cam", "cell", C),
        ("aam", "cell", b["Graphite"]),
        ("refined_cu", "cell", b["Cu"]),
        ("aluminium", "cell", b["Al"]),
        ("polysilicon", "wafer", si),
        ("wafer", "pv_cell", 1),
        ("pv_cell", "module", 1),
    ]
    for p, k, key in (
        ("polysilicon", "280461", "pv_polysilicon"),
        ("wafer", "381800", "pv_wafer"),
        ("pv_cell", "854142", "pv_cell"),
        ("module", "854143", "pv_module"),
    ):
        a = 1 / 1000 if p == "polysilicon" else M[key, "export"] / Q[22][k]["CHN"]
        A[p] = {c: q * a for c, q in Q[22][k].items()}
        A[p]["CHN"] = M[key, "production"] * (0.001 if p == "polysilicon" else 1)
        for c in A[p]:
            basis[c, p] = "production" if c == "CHN" else "trade"
    totals = {p: sum(q for q in x.values() if q > 0) for p, x in A.items()}
    hhi = {p: sum((q / totals[p]) ** 2 for q in x.values() if q > 0) for p, x in A.items()}
    A = {p: {c: q for c, q in x.items() if q > 0 and q / totals[p] >= 0.01} for p, x in A.items()}
    req, scales = {}, {}
    for f in ("cell", "module"):
        r = {f: sum(A[f].values())}
        while any(q in r and p not in r for p, q, a in edges):
            for p, q, a in edges:
                if q in r:
                    r[p] = a * r[q]
        s = min(1, *(sum(A[p].values()) / r[p] for p in r))
        req.update({p: a * s for p, a in r.items()})
        scales[f] = s
    nodes = [
        {"country": c, "product": p, "annual": q, "basis": basis[c, p], "S": q / req[p]}
        for p in sorted(A)
        for c, q in sorted(A[p].items())
    ]
    layers = {
        p: {
            "nodes": len(x),
            "annual": sum(x.values()),
            "coverage": sum(x.values()) / totals[p],
            "S": sum(x.values()) / req[p],
            "top_origin": max(x, key=x.get),
            "top_share": max(x.values()) / totals[p],
            "HHI": hhi[p],
            "bases": dict(Counter(basis[c, p] for c in x)),
        }
        for p, x in A.items()
    }
    meta = {
        "BOM_kg_per_kWh": b,
        "CAM_kg_per_kWh": C,
        "pCAM_kg_per_kWh": P,
        "pack_Wh_per_kg": E,
        "physical_edges": edges,
        "requirements": req,
        "demand_scale": scales,
        "layers": layers,
        "missing_BACI_mass": missing,
        "unparsed_MCS": unparsed,
    }
    dump("network.json", {"nodes": nodes, **meta})
    return nodes, edges, meta


def day(x):
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", x):
        d, m, y = map(int, x.split("/"))
        return date(y, m, d)
    return None


def events(nodes):
    """Derive OECD spells from raw SDMX and onsets on surveyed node-years."""
    pm = json.loads(read("data/events/product_map.json"))
    ps = pm["hs6_to_products"]

    def product(p):
        return "graphite" if p == "mine_graphite" else p

    O = defaultdict(dict)
    for r in rows("data/events/raw/oecd-battery-pv-2012-2024.csv"):
        k = (
            r["REF_AREA"],
            r["COMMODITY"].split("_")[-1],
            r["POLICY_TYPE"],
            r["POLICY_VARIATION"],
            int(r["TIME_PERIOD"]),
        )
        O[k][r["POLICY_DESCRIPTION"]] = r["OBS_VALUE"]
    G = defaultdict(list)
    for k, x in O.items():
        G[(*k[:4], day(x.get("DATI", "")))].append((k[-1], x))
    E = []
    for (c, hs, m, var, t), x in sorted(G.items(), key=lambda z: str(z[0])):
        directions = sorted({v.get("DIR", "") for y, v in x})
        ends = sorted({d for y, v in x if (d := day(v.get("END", ""))) is not None})
        end = max(ends) if ends else None
        censored = end is None or end >= date(2024, 12, 31)
        onset = (
            t is not None
            and 2012 <= t.year <= 2024
            and any(d in {"introduction", "increase", "reintroduction"} for d in directions)
        )
        e = {
            "country": c,
            "hs6": hs,
            "measure_type": m,
            "policy_variation": var,
            "effective_date": t.isoformat() if t else None,
            "end_date": end.isoformat() if end else None,
            "right_censored": censored,
            "restrictive_onset_in_window": onset,
            "products": [product(p) for p in ps.get(hs, [])],
            "directions": directions,
            "days": (date(2024, 12, 31) - t).days + 1
            if censored and t
            else ((end - t).days + 1 if end and t else None),
            "years": sorted(y for y, v in x),
            "source": "raw_OECD",
        }
        E.append(e)
    F = json.loads(read("data/events/policy_events.json"))["events"]

    def key(e):
        return tuple(
            e[k] for k in ("country", "hs6", "measure_type", "policy_variation", "effective_date")
        )

    F = {key(e): e for e in F}
    diffs = []
    for e in E:
        f = F.get(key(e))
        if f is None:
            diffs.append({"key": key(e), "field": "missing_derived_fact"})
            continue
        e["fact_id"] = f["id"]
        for k in ("end_date", "right_censored", "restrictive_onset_in_window", "directions"):
            if e[k] != f[k]:
                diffs.append({"key": key(e), "field": k, "raw": e[k], "derived": f[k]})
        ndays = (
            f["duration_days_lower_bound"] if f["right_censored"] else f["duration_days_observed"]
        )
        if e["days"] != ndays:
            diffs.append({"key": key(e), "field": "days", "raw": e["days"], "derived": ndays})
    acts = json.loads(read("data/events/acts.yaml"))["acts"]
    dedup = {
        v for e in acts if e.get("in_estimation_window") for v in e.get("deduplicate_oecd_ids", [])
    }
    for e in acts:
        if not e.get("in_estimation_window") or not e.get("is_restrictive_onset", True):
            continue
        t = date.fromisoformat(e["effective_date"])
        end = date.fromisoformat(e.get("censor_date", "2024-12-31"))
        E.append(
            {
                "country": e["country"],
                "products": [product(p) for p in e["products"]],
                "effective_date": t.isoformat(),
                "restrictive_onset_in_window": True,
                "right_censored": e.get("right_censored", True),
                "days": (end - t).days + 1,
                "source": "curated_national_act",
                "fact_id": e["id"],
            }
        )
    obs = set()
    for r in rows("data/events/oecd_coverage.csv"):
        if r["surveyed"] == "1":
            obs.update(
                (r["country"], product(p), int(r["year"]))
                for p in pm["coverage_commodity_to_products"][r["commodity"]]
            )
    onset = set()
    bins, excluded = Counter(), []
    for e in E:
        if not e["restrictive_onset_in_window"]:
            continue
        y = date.fromisoformat(e["effective_date"]).year
        I = {(e["country"], p, y) for p in e["products"]} & obs
        onset.update(I)
        if not I:
            continue
        d = e["days"] / 30.44
        if e["right_censored"] and d <= 6:
            excluded.append(e)
            continue
        bins[next((t for t in (3, 6, 12) if d <= t), 12)] += 1
    years = {
        (v["country"], v["product"]): {
            y: int((v["country"], v["product"], y) in onset)
            for y in range(2012, 2025)
            if (v["country"], v["product"], y) in obs
        }
        for v in nodes
    }
    with (W / "node_years.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["country", "product", "year", "onset"])
        w.writerows(
            (c, p, y, k) for (c, p), z in sorted(years.items()) for y, k in sorted(z.items())
        )
    dump("raw_events.json", E)
    return (
        years,
        np.array([bins[d] for d in (3, 6, 12)], dtype=float),
        {
            "raw_OECD_rows": sum(len(x) for x in O.values()),
            "raw_country_HS_measure_variation_years": len(O),
            "raw_OECD_spells": len(G),
            "derived_fact_spells": len(F),
            "raw_derived_discrepancies": diffs,
            "OECD_ids_linked_to_national_acts": sorted(dedup),
            "duration_counts": dict(bins),
            "short_censored_excluded": [
                {"id": e.get("fact_id"), "days": e["days"]} for e in excluded
            ],
            "mapped_surveyed_node_years_all_origins": len(obs),
            "mapped_onset_node_years_all_origins": len(onset),
        },
    )


def fit(nodes, years):
    """Fit the stated beta-binomial priors and country-year shock parameter."""
    K = {i: sum(y.values()) for i, y in years.items()}
    N = {i: len(y) for i, y in years.items()}

    def prior(I):
        k, n = np.array([K[i] for i in I]), np.array([N[i] for i in I])
        m = (sum(k) + 0.5) / (sum(n) + 1)

        def f(x):
            a, b = np.exp(x)
            return -np.sum(betaln(k + a, n - k + b) - betaln(a, b))

        r = minimize(f, np.log([10 * m, 10 * (1 - m)]), method="L-BFGS-B", bounds=[(-7, 14)] * 2)
        a, b = np.exp(r.x)
        return {
            "a": float(a),
            "b": float(b),
            "objective": float(r.fun),
            "success": bool(r.success),
            "message": str(r.message),
            "exposed_nodes": len(I),
            "N": int(sum(n)),
            "K": int(sum(k)),
        }

    pooled = prior([i for i in years if N[i]])
    products = sorted({p for c, p in years})
    priors, p = {}, {}
    for t in products:
        I = [i for i in years if i[1] == t and N[i]]
        priors[t] = prior(I) if I else {**pooled, "fallback": "all_exposed_joint_nodes"}
        a, b = priors[t]["a"], priors[t]["b"]
        p.update({i: (K[i] + a) / (N[i] + a + b) for i in years if i[1] == t})
    cmin = {c: min(v for i, v in p.items() if i[0] == c) for c, t in p}
    cy = []
    for c in cmin:
        for y in range(2012, 2025):
            I = [i for i in years if i[0] == c and y in years[i]]
            if len(I) >= 2:
                cy.append((c, y, I, int(sum(years[i][y] for i in I) >= 2)))

    def loss(rho):
        value = 0.0
        for c, y, I, k in cy:
            s = rho * cmin[c]
            q = np.array([(p[i] - s) / (1 - s) for i in I])
            zero = np.prod(1 - q)
            one = zero * np.sum(q / (1 - q))
            z = np.clip(s + (1 - s) * (1 - zero - one), 1e-12, 1 - 1e-12)
            value -= k * np.log(z) + (1 - k) * np.log1p(-z)
        return value

    opt = minimize_scalar(loss, bounds=(0, 1), method="bounded")
    rho = min((0.0, float(opt.x), 1.0), key=loss)
    return (
        p,
        rho,
        {
            "pooled_prior": pooled,
            "product_priors": priors,
            "rho": rho,
            "rho_log_loss": loss(rho),
            "rho_country_years": len(cy),
            "rho_multi_onset_years": sum(k for c, y, I, k in cy),
            "rho_objective_at_0": loss(0),
            "rho_objective_at_1": loss(1),
            "node_rates": [
                {"country": c, "product": t, "N": N[c, t], "K": K[c, t], "p": v}
                for (c, t), v in sorted(p.items())
            ],
        },
    )


def evaluate(nodes, edges, states, final):
    """Maximal cumulative production on a merging tree; 12 affected months.

    C[p,t] = min(C[p,t-1]+U[p,t], min_(q->p) C[q,t]).
    Induction in product order proves simultaneous cumulative maximality.
    Cost: O(|states|*12*(|products|+|edges|)); O(|states|*12*|products|).
    """
    products = sorted({v["product"] for v in nodes})
    inp = {p: [q for q, r, a in edges if r == p] for p in products}
    order = []
    while len(order) < len(products):
        order.extend(p for p in products if p not in order and all(q in order for q in inp[p]))
    n = len(states)
    U = {p: np.full((n, 12), sum(v["S"] for v in nodes if v["product"] == p)) for p in products}
    for i, z in enumerate(states):
        for j, d in z:
            v = nodes[j]
            U[v["product"]][i, :d] -= v["S"]
    C = {}
    for p in order:
        u = U[p]
        if p in final:
            u = np.minimum(u, 1.0)
        if not inp[p]:
            C[p] = u.cumsum(axis=1)
            continue
        a = np.minimum.reduce([C[q] for q in inp[p]])
        c = np.zeros_like(u)
        c[:, 0] = np.minimum(u[:, 0], a[:, 0])
        for t in range(1, 12):
            c[:, t] = np.minimum(c[:, t - 1] + u[:, t], a[:, t])
        C[p] = c
    return sum((12 - C[p][:, -1]) / 12 for p in final)


def lp_value(nodes, edges, z, final):
    """Independent time-expanded aggregate LP certificate, months 1,...,24."""
    products = sorted({v["product"] for v in nodes})
    j = {p: i for i, p in enumerate(products)}
    m, T = len(products), 24
    u = np.array([[sum(v["S"] for v in nodes if v["product"] == p)] * T for p in products]) / 12
    for i, d in z:
        u[j[nodes[i]["product"]], :d] -= nodes[i]["S"] / 12
    c = np.zeros((m, T))
    for p in final:
        u[j[p]] = np.minimum(u[j[p]], 1 / 12)
        c[j[p]] = -1
    A = []
    for p, q, a in edges:
        for t in range(T):
            r = np.zeros((m, T))
            r[j[q], : t + 1], r[j[p], : t + 1] = 1, -1
            A.append(r.ravel())
    r = linprog(
        c.ravel(),
        A_ub=np.array(A),
        b_ub=np.zeros(len(A)),
        bounds=list(zip(np.zeros(m * T), np.maximum(u.ravel(), 0))),
        method="highs",
    )
    return {"status": int(r.status), "phi": float(2 * len(final) + r.fun) if r.success else None}


def cuts(nodes, edges, sector):
    """Check every named cut, every duration predecessor, and all singletons."""
    data = json.loads(read(C[sector]))
    idx = {(v["country"], v["product"]): i for i, v in enumerate(nodes)}
    Z = [
        tuple(sorted((idx[v["country"], v["product"]], v["duration"]) for v in c["losses"]))
        for c in data["cuts"]
    ]
    finals = ["module"] if sector == "pv" else ["cell", "module"]
    theta = 0.5 * len(finals)
    V = evaluate(nodes, edges, Z, finals)
    cert, maxgap, lpcount = [], 0.0, 0
    for z, phi in zip(Z, V):
        pred = []
        lp = lp_value(nodes, edges, z, finals)
        lpcount += 1
        maxgap = max(maxgap, abs(phi - lp["phi"]))
        for i, d in z:
            d0 = {3: 0, 6: 3, 12: 6}[d]
            z0 = tuple((j, d0 if i == j else e) for j, e in z if i != j or d0 > 0)
            phi0 = float(evaluate(nodes, edges, [z0], finals)[0])
            lp0 = lp_value(nodes, edges, z0, finals)
            lpcount += 1
            maxgap = max(maxgap, abs(phi0 - lp0["phi"]))
            pred.append(
                {
                    "node": list(idx)[i],
                    "duration_from": d,
                    "duration_to": d0,
                    "phi": phi0,
                    "lp": lp0,
                    "survives": bool(phi0 <= theta + 1e-9),
                }
            )
        cert.append(
            {
                "losses": [
                    {"country": nodes[i]["country"], "product": nodes[i]["product"], "duration": d}
                    for i, d in z
                ],
                "phi": float(phi),
                "lp": lp,
                "fails": bool(phi > theta + 1e-9),
                "predecessors": pred,
            }
        )
    I = (
        list(range(len(nodes)))
        if sector == "joint"
        else [
            i
            for i, v in enumerate(nodes)
            if v["product"] in {"polysilicon", "wafer", "pv_cell", "module"}
        ]
    )
    singles = [(i, d) for i in I for d in (3, 6, 12)]
    vals = evaluate(nodes, edges, [[z] for z in singles], finals)
    single = [
        {
            "country": nodes[i]["country"],
            "product": nodes[i]["product"],
            "duration": d,
            "phi": float(v),
            "fails": bool(v > theta + 1e-9),
        }
        for (i, d), v in zip(singles, vals)
    ]
    out = {
        "sector": sector,
        "alpha": 0.25,
        "total_demand": 2 * len(finals),
        "failure_threshold": theta,
        "named_cut_count": len(Z),
        "support_counts": dict(Counter(map(len, Z))),
        "all_named_cuts_fail": all(c["fails"] for c in cert),
        "all_immediate_predecessors_survive": all(
            p["survives"] for c in cert for p in c["predecessors"]
        ),
        "lp_calls": lpcount,
        "max_LP_recurrence_difference": maxgap,
        "minimum_cut_margin": float(min(V) - theta),
        "minimum_predecessor_margin": min(
            theta - p["phi"] for c in cert for p in c["predecessors"]
        ),
        "singletons": single,
        "certificates": cert,
    }
    return Z, out


def union_probability(nodes, Z, p, rho, durations):
    """Exact DNF probability by country-conditioned node-state recursion.

    A residual clause is an intersection of node duration thresholds. Country
    shocks are integrated before leaving that country's node variables.
    """
    I = sorted({i for z in Z for i, d in z})
    countries = sorted({nodes[i]["country"] for i in I})
    order = [i for c in countries for i in I if nodes[i]["country"] == c]
    rank = {i: k for k, i in enumerate(order)}
    clauses = tuple(
        sorted(tuple(sorted((rank[i], (3, 6, 12).index(d) + 1) for i, d in z)) for z in Z)
    )
    groups = []
    offset = 0
    for c in countries:
        J = [i for i in order if nodes[i]["country"] == c]
        s = rho * min(p[v["country"], v["product"]] for v in nodes if v["country"] == c)
        q = [(p[nodes[i]["country"], nodes[i]["product"]] - s) / (1 - s) for i in J]
        groups.append((offset, len(J), s, tuple(q)))
        offset += len(J)
    gmap = {a: (n, s, q) for a, n, s, q in groups}

    @cache
    def reduce_clauses(C):
        C = sorted(set(C), key=lambda z: (len(z), z))
        out = []
        for c in C:
            z = dict(c)
            if not any(all(i in z and z[i] >= d for i, d in a) for a in out):
                out.append(c)
        return tuple(sorted(out))

    @cache
    def step(k, C, level):
        return reduce_clauses(
            tuple(
                tuple((i, d) for i, d in z if i != k)
                for z in C
                if not any(i == k and level < d for i, d in z)
            )
        )

    @cache
    def f(k, C, mode):
        if not C:
            return 0.0
        if () in C:
            return 1.0
        if k in gmap and mode == -1:
            n, s, q = gmap[k]
            return (1 - s) * f(k, C, 0) + s * f(k, C, 1)
        start, n, s, q = next(g for g in groups if g[0] <= k < g[0] + g[1])
        onset = 1.0 if mode == 1 else q[k - start]
        prob = np.r_[1 - onset, onset * durations]
        m = -1 if k + 1 == start + n else mode
        return sum(prob[l] * f(k + 1, step(k, C, l), m) for l in range(4) if prob[l] > 0)

    value = f(0, reduce_clauses(clauses), -1)
    return {
        "L": float(value),
        "recursion_cache": f.cache_info()._asdict(),
        "active_nodes": len(I),
        "active_countries": len(countries),
    }


def enumerate_cuts(nodes, edges, named):
    """Exhaust all duration states of support <=3 by sector decomposition.

    A sector's 12-month loss is <=1, so a joint cut at theta=1 must
    contain both sectors. Enumerate sector singles/pairs, then add losses.
    """
    t = perf_counter()
    pv = {"polysilicon", "wafer", "pv_cell", "module"}
    I = {
        "pv": [i for i, v in enumerate(nodes) if v["product"] in pv],
        "liion": [i for i, v in enumerate(nodes) if v["product"] not in pv],
    }
    Z, V, pred, lookup = {}, {}, {}, {}
    for sector in ("pv", "liion"):
        finals = ["module"] if sector == "pv" else ["cell"]
        lookup[sector] = {(): 0.0}
        for k in (1, 2, 3) if sector == "pv" else (1, 2):
            z = [
                tuple(zip(i, d))
                for i in itertools.combinations(I[sector], k)
                for d in itertools.product((3, 6, 12), repeat=k)
            ]
            value = evaluate(nodes, edges, z, finals)
            lookup[sector].update(zip(z, value))
            predecessor = []
            for a in z:
                v = []
                for i, d in a:
                    d0 = {3: 0, 6: 3, 12: 6}[d]
                    a0 = tuple((j, d0 if j == i else e) for j, e in a if j != i or d0)
                    v.append(lookup[sector][a0])
                predecessor.append(max(v))
            Z[sector, k], V[sector, k], pred[sector, k] = z, value, np.array(predecessor)
    found_pv = {
        z
        for k in (1, 2, 3)
        for z, v, v0 in zip(Z["pv", k], V["pv", k], pred["pv", k])
        if v > 0.5 + 1e-9 and v0 <= 0.5 + 1e-9
    }
    found_joint, counts = set(), {}
    for a, b in ((1, 1), (1, 2), (2, 1)):
        x, y = V["liion", a], V["pv", b]
        x0, y0 = pred["liion", a], pred["pv", b]
        minimal = (
            (x[:, None] + y[None, :] > 1 + 1e-9)
            & (x0[:, None] + y[None, :] <= 1 + 1e-9)
            & (x[:, None] + y0[None, :] <= 1 + 1e-9)
        )
        ix, iy = np.nonzero(minimal)
        found_joint.update(tuple(sorted(Z["liion", a][i] + Z["pv", b][j])) for i, j in zip(ix, iy))
        counts[f"{a}_Liion_{b}_PV"] = {"states": len(x) * len(y), "minimal": len(ix)}
    out = {
        "elapsed_seconds": perf_counter() - t,
        "epsilon": 1e-9,
        "sector_shortfall_evaluations": {
            s: sum(len(Z[s, k]) for k in (1, 2, 3) if (s, k) in Z) for s in I
        },
        "joint_mixed_states": counts,
        "sectors": {},
    }
    for sector, found in (("pv", found_pv), ("joint", found_joint)):
        expected = set(named[sector])

        def labels(z):
            return [
                {"country": nodes[i]["country"], "product": nodes[i]["product"], "duration": d}
                for i, d in z
            ]

        out["sectors"][sector] = {
            "found": len(found),
            "support_counts": dict(Counter(map(len, found))),
            "same_named_list": found == expected,
            "new_cuts": [labels(z) for z in sorted(found - expected)],
            "named_cuts_not_found": [labels(z) for z in sorted(expected - found)],
            "complete_through_support": 3,
        }
    dump("enumeration.json", out)
    return out


def main():
    t = perf_counter()
    for p in (
        "CLAUDE.md",
        "docs/DATA.md",
        "docs/MODEL.md",
        "docs/SOURCES.md",
        "docs/RESEARCH.md",
        "SOURCES.lock",
    ):
        x = read(p)
        if p in {"docs/DATA.md", "docs/MODEL.md"}:
            (W / (Path(p).stem + "-reference.md")).write_text(x, encoding="utf-8")
    nodes, edges, meta = network()
    print("network", len(nodes), {p: x["nodes"] for p, x in meta["layers"].items()}, flush=True)
    years, counts, event = events(nodes)
    p, rho, rate = fit(nodes, years)
    print(
        "events", event["duration_counts"], "rho", rho, "pooled", rate["pooled_prior"], flush=True
    )
    dump("fit.json", {"events": event, "rates": rate})
    output = {
        "python": sys.version,
        "network": meta,
        "node_count": len(nodes),
        "events": event,
        "rates": rate,
        "parameters": {
            "NCM622_share": 0.5,
            "cutoff": 0.01,
            "T": 24,
            "alpha": 0.25,
            "h": 0,
            "sigma": 0,
            "durations": [3, 6, 12],
        },
        "sectors": {},
    }
    named = {}
    for sector in ("pv", "joint"):
        Z, certificate = cuts(nodes, edges, sector)
        named[sector] = Z
        selected = [
            v
            for v in nodes
            if sector == "joint" or v["product"] in {"polysilicon", "wafer", "pv_cell", "module"}
        ]
        certificate["probability"] = union_probability(
            selected if sector == "pv" else nodes,
            [tuple((selected.index(nodes[i]), d) for i, d in z) for z in Z]
            if sector == "pv"
            else Z,
            p,
            rho,
            counts / counts.sum(),
        )
        output["sectors"][sector] = certificate
        print(
            sector,
            certificate["all_named_cuts_fail"],
            certificate["all_immediate_predecessors_survive"],
            certificate["probability"],
            flush=True,
        )
    output["enumeration"] = enumerate_cuts(nodes, edges, named)
    print("enumeration", output["enumeration"], flush=True)
    lock = json.loads(read("SOURCES.lock"))["sources"]
    lockhash = {str(R / r["path"]): r["sha256"] for r in lock}
    output["input_sha256"] = H
    output["locked_input_mismatches"] = [
        {"path": p, "actual": h, "lock": lockhash[p]}
        for p, h in H.items()
        if p in lockhash and h != lockhash[p]
    ]
    output["elapsed_seconds"] = perf_counter() - t
    dump("results.json", output)
    x = json.loads((W / "results.json").read_text(encoding="utf-8"))
    print(
        "readback",
        {s: x["sectors"][s]["probability"]["L"] for s in x["sectors"]},
        "seconds",
        x["elapsed_seconds"],
        flush=True,
    )


if __name__ == "__main__":
    main()
