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
from pathlib import Path

from chokepoint.brute import enumerate_brute, enumerate_lattice
from chokepoint.cuts import enumerate_cuts
from chokepoint.fetch import stamp
from chokepoint.net import build, model
from chokepoint.sweep import (DURATIONS, EPS, K, PRUNE, certified_lattice, sparse,
                              tasks)

def job(task, out):
    name, kw, cfg, checks = task
    path = out / f"{name}.json"
    if path.exists():
        return name, "cached"
    N = build(**kw)
    M = model(N, h=cfg["h"], sigma=cfg["sigma"], L=cfg["L"], durations=DURATIONS)
    theta = cfg["alpha"]*M["total"]
    C = certified_lattice(M, cfg["alpha"])
    res = {"task": name, "config": cfg, "network": {k: (sorted(map(list, v)) if k == "exclude"
                                                         else v) for k, v in kw.items()},
           "nodes": [list(v) for v in M["V"]], "theta": theta, "total": M["total"],
           "cuts": C["cuts"], "complete": True, "method": "lattice",
           "seconds": C["seconds"], "lp_calls": C["lp_calls"],
           "certificates": C["certificates"]}
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
