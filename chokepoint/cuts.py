"""Dual-based interdiction MILP with upper-orthant exclusions; docs/MODEL.md."""
from time import perf_counter

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix, hstack

from chokepoint.recourse import solve


def _worst(M, durations, eligible, alpha, eps):
    """Solve the state with every eligible node out for the longest duration.

    OUTPUT (worst, verdict): verdict is None when that state fails, so enumeration must run;
    otherwise "worst_state_safe" or "worst_state_<status>" for a state that blocks a decision.
    """
    worst = solve(M, [max(durations) if v in eligible else 0 for v in range(len(M["V"]))])
    held = worst["status"]
    if held == "optimal" and worst["residual"] > 10*eps:
        held = "residual"
    if held != "optimal" or worst["phi"] <= alpha*M["total"] + eps:
        return worst, "worst_state_safe" if held == "optimal" else "worst_state_" + held
    return worst, None


class _Program:
    """The interdiction MILP: columns [dual multipliers of A and E, z[v, j] = node v out for
    durations[j], w = capacity multiplier times z]; bounds lo <= x <= hi, integral z, objective
    Σz; rows lb <= Bx <= ub appended one at a time. Row `failure` asks q'x >= floor: the dual
    value exceeds theta by the strict margin."""

    def __init__(self, M, durations, eligible, k, floor):
        A, E, b, f, c = (M[x] for x in ("A", "E", "b", "f", "c"))
        n, J = len(M["V"]), len(durations)
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
        self.rows, self.cols, self.vals, self.lb, self.ub = [], [], [], [], []
        self.z0, self.J, self.N, self.lo, self.hi = z0, J, N, lo, hi
        self.integrality, self.objective = integrality, objective
        Q = hstack([-A.T, E.T]).tocoo()
        self.rows.extend(Q.row.tolist())
        self.cols.extend(Q.col.tolist())
        self.vals.extend(Q.data.tolist())
        self.lb.extend([-np.inf]*len(c))
        self.ub.extend(c.tolist())
        for v in range(n):
            self.add([(z0 + v*J + j, 1) for j in range(J)], upper=1)
        self.add([(j, 1) for j in range(z0, w0)], upper=k)
        q = [(i, -x) for i, x in enumerate(b) if x]
        q.extend((m + i, x) for i, x in enumerate(f) if x)
        for l, (t, v, j) in enumerate(triples):
            r, z, w, bound = M["cap"][t, v], z0 + v*J + j, w0 + l, M["Mcap"][t, v]
            hi[w] = bound
            self.add([(w, 1), (r, -1)], upper=0)
            self.add([(w, 1), (z, -bound)], upper=0)
            self.add([(w, 1), (r, -1), (z, -bound)], lower=-bound)
            q.append((w, M["U"][t, v]))
        self.q, self.floor, self.failure = q, floor, len(self.lb)
        self.add(q, lower=floor)

    def add(self, x, lower=-np.inf, upper=np.inf):
        """Append the row lower <= Σ a x_j <= upper for the pairs (j, a) in x."""
        r = len(self.lb)
        for j, a in x:
            if a:
                self.rows.append(r)
                self.cols.append(j)
                self.vals.append(a)
        self.lb.append(lower)
        self.ub.append(upper)

    def matrix(self):
        return coo_matrix((self.vals, (self.rows, self.cols)),
                          shape=(len(self.lb), self.N)).tocsc()

    def milp(self, objective, B, time_limit):
        return milp(objective, integrality=self.integrality, bounds=Bounds(self.lo, self.hi),
                    constraints=LinearConstraint(B, self.lb, self.ub),
                    options={"time_limit": time_limit, "mip_rel_gap": 0})

    def boundary(self, B, time_limit):
        """Maximise the residual shortfall q'x without the failure row, to rule out strict
        failures inside the margin."""
        self.lb[self.failure] = -np.inf
        objective = np.zeros(self.N)
        for i, x in self.q:
            objective[i] -= x
        R = self.milp(objective, B, time_limit)
        self.lb[self.failure] = self.floor
        return R

    def state(self, x, durations, n):
        """The duration state D of n nodes that the z columns of solution x select."""
        z0, J = self.z0, self.J
        D = [0]*n
        for v in range(n):
            for j in range(J):
                if x[z0 + v*J + j] > 0.5:
                    D[v] = durations[j]
        return D

    def exclude(self, D, durations):
        """Forbid the upper orthant of cut D: no later state may cover its whole support."""
        z0, J = self.z0, self.J
        I = [v for v in range(len(D)) if D[v]]
        self.add([(z0 + v*J + j, 1) for v in I for j in range(J) if durations[j] >= D[v]],
                 upper=len(I) - 1)


def _certify(M, D, durations, theta, eps):
    """Shrink a failing state D to a minimal cut and certify it and its predecessors.

    OUTPUT (cut, None) or (None, status) when a certificate or predecessor solve fails.
    """
    R0 = solve(M, D)
    if (R0["status"] != "optimal" or R0["dual"] <= theta + eps
            or R0["residual"] > 10*eps):
        return None, "certificate_failure"
    shrunk = True
    for v in range(len(D)):
        while D[v] and shrunk:
            prev = [0, *durations][durations.index(D[v])]
            Dp = D.copy()
            Dp[v] = prev
            P = solve(M, Dp, dual=False)
            if P["status"] != "optimal":
                shrunk = False
                break
            if P["phi"] <= theta + eps:
                break
            D = Dp
    if not shrunk:
        return None, "predecessor_" + P["status"]
    R0 = solve(M, D)
    predecessors = []
    for v in range(len(D)):
        if D[v]:
            Dp = D.copy()
            Dp[v] = [0, *durations][durations.index(D[v])]
            P = solve(M, Dp)
            predecessors.append({"v": v, "D": Dp, **P})
    if (R0.get("gap", np.inf) > eps*10 or R0["residual"] > eps*10 or any(
            x.get("gap", np.inf) > eps*10 or x["residual"] > eps*10 or x["phi"] > theta + eps
            for x in predecessors)):
        return None, "certificate_failure"
    return {"D": D, **R0, "predecessors": predecessors}, None


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
    n = len(M["V"])
    eligible = set(range(n) if eligible is None else eligible)
    worst, verdict = _worst(M, durations, eligible, alpha, eps)
    if verdict:
        return {"cuts": [], "complete": verdict == "worst_state_safe", "status": verdict,
                "calls": 0,
                "seconds": perf_counter() - start, "alpha": alpha, "durations": durations,
                "k": k, "eps": eps, "worst_state": worst}
    theta = alpha*M["total"]
    # HiGHS feasibility tolerance must not turn equality into strict failure.
    margin = max(eps*10, 1e-6*max(1, M["total"]))
    F = _Program(M, durations, eligible, k, theta + margin)
    cuts, status, complete, calls = [], "not_started", False, 0
    while len(cuts) < max_cuts:
        remaining = time_limit - (perf_counter() - start)
        if remaining <= 0:
            status = "time_limit"
            break
        B = F.matrix()
        R = F.milp(F.objective, B, remaining)
        calls += 1
        if R.status == 2:
            R = F.boundary(B, max(0.01, time_limit - (perf_counter() - start)))
            calls += 1
            if R.status == 2 or (R.status == 0 and -R.fun <= theta + eps):
                complete, status = True, "exhausted"
                break
            if R.status != 0:
                status = "boundary_check_limit"
                break
        if R.status != 0:
            status = {1: "limit", 3: "unbounded", 4: "numerical"}.get(R.status, "unknown")
            break
        cut, failure = _certify(M, F.state(R.x, durations, n), durations, theta, eps)
        if cut is None:
            status = failure
            break
        cuts.append(cut)
        if not any(cut["D"]):
            complete, status = True, "baseline_failure"
            break
        F.exclude(cut["D"], durations)
    else:
        status = "cut_limit"
    return {"cuts": cuts, "complete": complete, "status": status, "calls": calls,
            "seconds": perf_counter() - start, "alpha": alpha, "durations": durations,
            "k": k, "eps": eps, "strict_margin": margin}


