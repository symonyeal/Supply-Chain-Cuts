"""Cut-set sweep (design §4, §6): python run_cuts.py RUN_ID [WORKERS] [SECTOR].

Every task writes results/RUN_ID/cuts/<task>.json and is skipped if present. A task
enumerates minimal cuts of support <= K on the full network by lattice search and
certifies each: primal phi with its dual and gap, and every immediate duration predecessor
below the threshold. Certificate tasks repeat the enumeration on the pruned network
(share >= 5%) by exhaustive search and by the interdiction MILP, or on the full network by
the MILP; agreement of the lists is the certificate. SECTOR liion (v0.1.0) runs the sweep and
the variants of tests B1, B2, C1; pv runs the sweep with exhaustive search on the whole
network; joint runs the shared Li-ion and PV network at h = sigma = 0 (v0.2.0).
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
from pathlib import Path

from chokepoint.brute import enumerate_brute, enumerate_lattice
from chokepoint.cuts import enumerate_cuts
from chokepoint.fetch import stamp
from chokepoint.net import build, model, reexport_flags
from chokepoint.recourse import solve

DURATIONS, K, EPS, PRUNE = (3, 6, 12), 3, 1e-7, 0.05
ALPHA, H, SIGMA, LEAD = (0.10, 0.25, 0.50), (0, 1, 3), (0, 0.1, 0.5), (6, 24)
BASE = {"sector": "liion", "ncm": 0.5, "basis": "production"}


def sparse(cuts):
    return sorted([[v, int(d)] for v, d in enumerate(D) if d] for D in cuts)


def certify(M, D, theta):
    """phi(S) > theta with zero gap; each immediate duration predecessor has phi <= theta."""
    R = solve(M, D)
    pred = []
    for v, d in enumerate(D):
        if d:
            E = list(D)
            E[v] = max([0, *(x for x in DURATIONS if x < d)])
            pred.append({"v": v, "D": E[v], "phi": solve(M, E, dual=False)["phi"]})
    ok = (R["status"] == "optimal" and R["phi"] > theta + EPS and R["gap"] <= 10*EPS
          and all(x["phi"] <= theta + EPS for x in pred))
    return {"phi": R["phi"], "dual": R["dual"], "gap": R["gap"], "predecessors": pred,
            "certified": ok}


def tasks(sector="liion"):
    if sector != "liion":
        kw = {**BASE, "sector": sector}
        for alpha, h, sigma in product(ALPHA, H, SIGMA):
            for L in (LEAD if sigma else (6,)):
                if sector == "joint" and (h or sigma or alpha == 0.5):
                    continue
                cfg = {"alpha": alpha, "h": h, "sigma": sigma, "L": L}
                yield (f"base_a{alpha}_h{h}_s{sigma}_L{L}", kw, cfg,
                       ["brute_full"] if sector == "pv" else ["pruned"])
        return
    for alpha, h, sigma in product(ALPHA, H, SIGMA):
        for L in (LEAD if sigma else (6,)):
            cfg = {"alpha": alpha, "h": h, "sigma": sigma, "L": L}
            checks = ["pruned"] + (["milp_full"] if h == sigma == 0 else [])
            yield f"base_a{alpha}_h{h}_s{sigma}_L{L}", BASE, cfg, checks
    flagged = [tuple(x[:2]) for x in reexport_flags(build(**BASE))]
    variants = {"B1": {**BASE, "exclude": flagged}, "B2": {**BASE, "basis": "trade"},
                **{f"C1_ncm{x}": {**BASE, "ncm": x} for x in (0.0, 0.25, 0.75, 1.0)}}
    for name, kw in variants.items():
        for alpha in (0.10, 0.25):
            yield f"{name}_a{alpha}", kw, {"alpha": alpha, "h": 0, "sigma": 0, "L": 6}, []


def job(task, out):
    name, kw, cfg, checks = task
    path = out / f"{name}.json"
    if path.exists():
        return name, "cached"
    N = build(**kw)
    M = model(N, h=cfg["h"], sigma=cfg["sigma"], L=cfg["L"], durations=DURATIONS)
    theta = cfg["alpha"]*M["total"]
    t = time.perf_counter()
    R = enumerate_lattice(M, DURATIONS, alpha=cfg["alpha"], k=K, eps=EPS)
    res = {"task": name, "config": cfg, "network": {k: (sorted(map(list, v)) if k == "exclude"
                                                         else v) for k, v in kw.items()},
           "nodes": [list(v) for v in M["V"]], "theta": theta, "total": M["total"],
           "cuts": sparse(R["cuts"]), "complete": True, "method": "lattice",
           "seconds": time.perf_counter() - t, "lp_calls": R["lp_calls"]}
    res["certificates"] = [certify(M, [dict(S).get(v, 0) for v in range(len(M["V"]))], theta)
                           for S in res["cuts"]]
    if "pruned" in checks:
        E = [i for i, x in enumerate(N["nodes"]) if x["share"] >= PRUNE]
        t = time.perf_counter()
        b = sparse(enumerate_brute(M, DURATIONS, cfg["alpha"], K, EPS, eligible=E))
        tb = time.perf_counter() - t
        lat = sparse(enumerate_lattice(M, DURATIONS, cfg["alpha"], K, EPS, eligible=E)["cuts"])
        C = enumerate_cuts(M, DURATIONS, cfg["alpha"], K, EPS, time_limit=900, eligible=E)
        milp = sparse(x["D"] for x in C["cuts"])
        res["pruned"] = {"eligible": E, "brute": b, "brute_seconds": tb, "lattice": lat,
                         "milp": milp, "milp_status": C["status"], "milp_complete": C["complete"],
                         "milp_seconds": C["seconds"], "brute_equals_lattice": b == lat,
                         "milp_equals_brute": C["complete"] and milp == b}
    if "brute_full" in checks:
        t = time.perf_counter()
        b = sparse(enumerate_brute(M, DURATIONS, cfg["alpha"], K, EPS))
        res["brute_full"] = {"cuts": b, "seconds": time.perf_counter() - t,
                             "equals_lattice": b == res["cuts"]}
    if "milp_full" in checks:
        C = enumerate_cuts(M, DURATIONS, cfg["alpha"], K, EPS, time_limit=5400)
        milp = sparse(x["D"] for x in C["cuts"])
        res["milp_full"] = {"cuts": milp, "status": C["status"], "complete": C["complete"],
                            "seconds": C["seconds"], "calls": C["calls"],
                            "equals_lattice": C["complete"] and milp == res["cuts"]}
    path.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    return name, "done"


def main():
    out = Path("results") / sys.argv[1] / "cuts"
    out.mkdir(parents=True, exist_ok=True)
    if not (out.parent / "cuts_stamp.json").exists():
        (out.parent / "cuts_stamp.json").write_text(json.dumps(stamp(), indent=1),
                                                    encoding="utf-8")
    T = list(tasks(sys.argv[3] if len(sys.argv) > 3 else "liion"))
    T.sort(key=lambda x: "milp_full" not in x[3])     # long tasks first
    with ProcessPoolExecutor(int(sys.argv[2]) if len(sys.argv) > 2 else 6) as pool:
        for f in as_completed([pool.submit(job, x, out) for x in T]):
            print(*f.result(), flush=True)


if __name__ == "__main__":
    main()
