"""Shared cut-sweep configuration and certified lattice orchestration."""
from itertools import product
from copy import deepcopy
from time import perf_counter

from chokepoint.brute import enumerate_lattice
from chokepoint.net import build, reexport_flags
from chokepoint.recourse import solve

DURATIONS, K, EPS, PRUNE = (3, 6, 12), 3, 1e-7, 0.05
ALPHA, H, SIGMA, LEAD = (0.10, 0.25, 0.50), (0, 1, 3), (0, 0.1, 0.5), (6, 24)
BASE = {"sector": "liion", "ncm": 0.5, "basis": "production"}


def reserve(N, eta):
    """Scale selected product capacities while preserving the reference demand."""
    N = deepcopy(N)
    for x in N['nodes']:
        f = eta.get(x['product'], 1)
        x['annual'] *= f
        x['capacity'] *= f
    for p, f in eta.items():
        N['supply_ratio'][p] *= f
        N['annual_totals'][p] *= f
    N['availability'] = eta
    return N


def sparse(cuts):
    """Return each dense duration state as sorted node-duration pairs."""
    return sorted([[v, int(d)] for v, d in enumerate(D) if d] for D in cuts)


def dense(cut, n):
    """Expand sparse node-duration pairs to one duration per node."""
    D = [0]*n
    for v, d in cut:
        D[v] = d
    return D


def certify(M, D, theta, durations=DURATIONS, eps=EPS):
    """Check that a failing cut's immediate duration predecessors survive."""
    R = solve(M, D)
    pred = []
    for v, d in enumerate(D):
        if d:
            E = list(D)
            E[v] = max([0, *(x for x in durations if x < d)])
            pred.append({"v": v, "D": E[v], "phi": solve(M, E, dual=False)["phi"]})
    ok = (R["status"] == "optimal" and R["phi"] > theta + eps and R["gap"] <= 10*eps
          and all(x["phi"] <= theta + eps for x in pred))
    return {"phi": R["phi"], "dual": R["dual"], "gap": R["gap"], "predecessors": pred,
            "certified": ok}


def certified_lattice(M, alpha=0.25, *, durations=DURATIONS, k=K, eps=EPS):
    """Enumerate minimal cuts of support <= k and attach primal/dual certificates.

    The reported seconds cover lattice enumeration only, matching the original runner
    timing boundary. The exact lattice implementation remains in `chokepoint.brute`.
    """
    start = perf_counter()
    R = enumerate_lattice(M, durations, alpha=alpha, k=k, eps=eps)
    seconds = perf_counter() - start
    cuts = sparse(R["cuts"])
    certificates = [certify(M, dense(S, len(M["V"])), alpha*M["total"], durations, eps)
                    for S in cuts]
    return {"cuts": cuts, "certificates": certificates, "lp_calls": R["lp_calls"],
            "seconds": seconds}


def tasks(sector="liion"):
    """Yield the saved fixed-mix sweep and its registered sensitivity tasks."""
    kw = {**BASE, "sector": sector}
    for alpha, h, sigma in product(ALPHA, H, SIGMA):
        for L in (LEAD if sigma else (6,)):
            if sector == "joint" and (h or sigma or alpha == 0.5):
                continue
            cfg = {"alpha": alpha, "h": h, "sigma": sigma, "L": L}
            checks = ["brute_full"] if sector == "pv" else ["pruned"]
            if sector == "liion" and h == sigma == 0:
                checks.append("milp_full")
            yield f"base_a{alpha}_h{h}_s{sigma}_L{L}", kw, cfg, checks
    if sector != "liion":
        return
    flagged = [tuple(x[:2]) for x in reexport_flags(build(**BASE))]
    variants = {"B1": {**BASE, "exclude": flagged}, "B2": {**BASE, "basis": "trade"},
                **{f"C1_ncm{x}": {**BASE, "ncm": x} for x in (0.0, 0.25, 0.75, 1.0)}}
    for name, kw in variants.items():
        for alpha in (0.10, 0.25):
            yield f"{name}_a{alpha}", kw, {"alpha": alpha, "h": 0, "sigma": 0, "L": 6}, []


def truncate(weights, DJ):
    """Truncate the duration law at DJ, combining all longer-duration mass."""
    durations = [d for d in DURATIONS if d <= DJ]
    return durations, [sum(x for d, x in zip(DURATIONS, weights, strict=True)
                            if min(d, DJ) == e) for e in durations]
