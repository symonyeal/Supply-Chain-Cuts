"""Dual-based interdiction MILP with upper-orthant exclusions; docs/MODEL.md."""
from time import perf_counter

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix, hstack

from chokepoint.recourse import solve


def enumerate_cuts(M, durations, alpha=0.25, k=3, eps=1e-7, time_limit=120,
                   max_cuts=10000, eligible=None):
    """Return minimal duration cuts, primal/dual witnesses and proven completeness.

    INPUT M: recourse matrices; durations: increasing positive months; k: support limit.
    OUTPUT cuts, complete, solver status and runtime. A time limit is incomplete.
    """
    durations = sorted({int(x) for x in durations})
    if not durations or durations[0] <= 0 or not 0 <= alpha < 1 or k < 0 or eps <= 0:
        raise ValueError("Positive durations/epsilon, 0 <= alpha < 1 and k >= 0 required")
    start = perf_counter()
    n, J = len(M["V"]), len(durations)
    eligible = set(range(n) if eligible is None else eligible)
    worst = solve(M, [max(durations) if v in eligible else 0 for v in range(n)])
    if worst["status"] == "optimal" and worst["phi"] <= alpha*M["total"] + eps:
        return {"cuts": [], "complete": True, "status": "worst_state_safe", "calls": 0,
                "seconds": perf_counter() - start, "alpha": alpha, "durations": durations,
                "k": k, "eps": eps, "worst_state": worst}
    A, E, b, f, c = (M[x] for x in ("A", "E", "b", "f", "c"))
    m, e = A.shape[0], E.shape[0]
    z0, w0 = m + e, m + e + n*J
    if not np.isin(durations, M["ends"]).all():
        raise ValueError("Durations must be block ends of the recourse LP")
    K = len(M["ends"])
    triples = [(t, v, j) for t in range(K) for v in range(n)
               for j, D in enumerate(durations) if M["ends"][t] <= D and M["M"][v] > 0]
    N = w0 + len(triples)
    lo, hi = np.zeros(N), np.full(N, np.inf)
    lo[m:z0], hi[z0:w0] = -np.inf, 1
    for v in range(n):
        if v not in eligible:
            hi[z0 + v*J:z0 + (v + 1)*J] = 0
    for t in range(K):
        hi[M["cap"][t]] = M["Mcap"][t]
    integrality, objective = np.zeros(N), np.zeros(N)
    integrality[z0:w0], objective[z0:w0] = 1, 1
    rows, cols, vals, lb, ub = [], [], [], [], []

    def row(x, lower=-np.inf, upper=np.inf):
        r = len(lb)
        for j, a in x:
            if a:
                rows.append(r)
                cols.append(j)
                vals.append(a)
        lb.append(lower)
        ub.append(upper)

    Q = hstack([-A.T, E.T]).tocoo()
    rows.extend(Q.row.tolist())
    cols.extend(Q.col.tolist())
    vals.extend(Q.data.tolist())
    lb.extend([-np.inf]*len(c))
    ub.extend(c.tolist())
    for v in range(n):
        row([(z0 + v*J + j, 1) for j in range(J)], upper=1)
    row([(j, 1) for j in range(z0, w0)], upper=k)
    q = [(i, -x) for i, x in enumerate(b) if x]
    q.extend((m + i, x) for i, x in enumerate(f) if x)
    for l, (t, v, j) in enumerate(triples):
        r, z, w, bound = M["cap"][t, v], z0 + v*J + j, w0 + l, M["Mcap"][t, v]
        hi[w] = bound
        row([(w, 1), (r, -1)], upper=0)
        row([(w, 1), (z, -bound)], upper=0)
        row([(w, 1), (r, -1), (z, -bound)], lower=-bound)
        q.append((w, M["U"][t, v]))
    theta = alpha*M["total"]
    # HiGHS feasibility tolerance must not turn equality into strict failure.
    margin = max(eps*10, 1e-6*max(1, M["total"]))
    failure_row = len(lb)
    row(q, lower=theta + margin)
    cuts, status, complete, calls = [], "not_started", False, 0
    while len(cuts) < max_cuts:
        remaining = time_limit - (perf_counter() - start)
        if remaining <= 0:
            status = "time_limit"
            break
        B = coo_matrix((vals, (rows, cols)), shape=(len(lb), N)).tocsc()
        R = milp(objective, integrality=integrality, bounds=Bounds(lo, hi),
                 constraints=LinearConstraint(B, lb, ub),
                 options={"time_limit": remaining, "mip_rel_gap": 0})
        calls += 1
        if R.status == 2:
            # Maximise residual shortfall to rule out strict failures inside the margin.
            lb[failure_row] = -np.inf
            check_objective = np.zeros(N)
            for i, x in q:
                check_objective[i] -= x
            R = milp(check_objective, integrality=integrality, bounds=Bounds(lo, hi),
                     constraints=LinearConstraint(B, lb, ub),
                     options={"time_limit": max(0.01, time_limit - (perf_counter() - start)),
                              "mip_rel_gap": 0})
            calls += 1
            lb[failure_row] = theta + margin
            if R.status == 2 or (R.status == 0 and -R.fun <= theta + eps):
                complete, status = True, "exhausted"
                break
            if R.status != 0:
                status = "boundary_check_limit"
                break
        if R.status != 0:
            status = {1: "limit", 3: "unbounded", 4: "numerical"}.get(R.status, "unknown")
            break
        D = [0]*n
        for v in range(n):
            for j in range(J):
                if R.x[z0 + v*J + j] > 0.5:
                    D[v] = durations[j]
        R0 = solve(M, D)
        if R0["status"] != "optimal" or R0["phi"] <= theta + eps:
            status = "certificate_failure"
            break
        for v in range(n):
            while D[v]:
                prev = [0, *durations][durations.index(D[v])]
                Dp = D.copy()
                Dp[v] = prev
                P = solve(M, Dp, dual=False)
                if P["status"] != "optimal":
                    raise RuntimeError(P)
                if P["phi"] <= theta + eps:
                    break
                D = Dp
        R0 = solve(M, D)
        predecessors = []
        for v in range(n):
            if D[v]:
                Dp = D.copy()
                Dp[v] = [0, *durations][durations.index(D[v])]
                P = solve(M, Dp)
                predecessors.append({"v": v, "D": Dp, **P})
        if R0.get("gap", np.inf) > eps*10 or any(
            x.get("gap", np.inf) > eps*10 or x["phi"] > theta + eps for x in predecessors
        ):
            status = "certificate_failure"
            break
        cuts.append({"D": D, **R0, "predecessors": predecessors})
        I = [v for v in range(n) if D[v]]
        if not I:
            complete, status = True, "baseline_failure"
            break
        row([(z0 + v*J + j, 1) for v in I for j in range(J) if durations[j] >= D[v]],
            upper=len(I) - 1)
    else:
        status = "cut_limit"
    return {"cuts": cuts, "complete": complete, "status": status, "calls": calls,
            "seconds": perf_counter() - start, "alpha": alpha, "durations": durations,
            "k": k, "eps": eps, "strict_margin": margin}
