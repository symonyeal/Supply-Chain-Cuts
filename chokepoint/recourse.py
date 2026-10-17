"""Time-expanded material-balance LP and its dual; docs/MODEL.md."""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import hstack, lil_matrix


def matrices(V, u, a, d, h=0.0, sigma=0.0, L=1.0, final="cell", aggregate=True, ends=None,
             recipes=None, stock=None, shares=None):
    """Build min c'x, Ax <= b(D), Ex = f, x >= 0 over blocks of months.

    INPUT V: (country, product); u: monthly capacity; a[p,q]: input/output units;
          d: monthly demand vector or {final: vector}; h: months of stock;
          sigma: spare fraction; L: ramp months; ends: block end months (default monthly);
          recipes[layer][name] = (output, {input: coefficient}); shares[final] = (lo, hi);
          stock[input, layer]: reference input per unit capacity for initial inventory.
    OUTPUT shared primal matrices and valid capacity-dual bounds.
    Block aggregation is exact when all data are constant on each block: averaging a
    feasible solution over a block keeps every linear row, and inventory moves linearly
    between nonnegative endpoints (docs/MODEL.md).
    """
    V, u = list(map(tuple, V)), np.asarray(u, float)
    d = {final: np.asarray(d, float)} if not isinstance(d, dict) else {
        p: np.asarray(x, float) for p, x in d.items()
    }
    if len(set(V)) != len(V) or u.shape != (len(V),):
        raise ValueError("Distinct nodes and one capacity per node required")
    if not np.isfinite(u).all() or (u < 0).any() or h < 0 or sigma < 0 or L <= 0:
        raise ValueError("Finite nonnegative capacities and recourse, L > 0 required")
    T = len(next(iter(d.values())))
    if T == 0 or any(x.shape != (T,) or not np.isfinite(x).all() or (x < 0).any()
                     for x in d.values()):
        raise ValueError("Demand vectors must have equal positive length and nonnegative values")
    if any(not np.isfinite(x) or x <= 0 for x in a.values()):
        raise ValueError("Input coefficients must be finite and positive")
    layers = {p for _, p in V}
    recipes = {p: {p: (p, {q: x for (q, r), x in a.items() if r == p})}
               for p in layers} | (recipes or {})
    shares = shares or {}
    if any(not 0 <= lo <= hi <= 1 for lo, hi in shares.values()):
        raise ValueError("Chemistry shares require 0 <= lo <= hi <= 1")
    recipes = {p: {r: (q, b) for r, (q, b) in rs.items()
                   if not (q in shares and ((shares[q][1] == 0 and r == 'ncm') or
                                            (shares[q][0] == 1 and r != 'ncm')))}
               for p, rs in recipes.items()}
    if h and stock is None and any(len(rs) > 1 for rs in recipes.values()):
        raise ValueError("Alternative recipes with stock need reference input coefficients")
    stock = stock if stock is not None else {
        (q, p): x for p, rs in recipes.items() for _, b in rs.values() for q, x in b.items()}
    arcs = [(q, p, x) for rs in recipes.values() for p, b in rs.values() for q, x in b.items()]
    if any(not np.isfinite(x) or x <= 0 for _, _, x in arcs):
        raise ValueError("Recipe coefficients must be finite and positive")
    ends = np.arange(1, T + 1) if ends is None else np.array(sorted(set(ends)), int)
    if ends[0] < 1 or ends[-1] != T:
        raise ValueError("Block ends must lie in 1..T and end at T")
    starts = np.r_[1, ends[:-1] + 1]
    ramp = 1 + sigma*np.minimum(1, np.arange(1, T + 1)/L)
    if any(np.ptp(x[s - 1:e]) > 0 for s, e in zip(starts, ends, strict=True)
           for x in [ramp, *d.values()]):
        raise ValueError("Demand and ramp must be constant on every block")
    products = {p for rs in recipes.values() for p, _ in rs.values()} | {
        q for q, _, _ in arcs} | set(d)
    order, remaining = [], set(products)
    while remaining:
        P = sorted(p for p in remaining if not any(q == p and r in remaining
                                                  for r, q, _ in arcs))
        if not P:
            raise ValueError("Product graph must be acyclic")
        order.extend(P)
        remaining.difference_update(P)
    M = {p: float(p in d) for p in products}
    for p in reversed(order):
        M[p] = max([M[p], *(M[q]/x for r, q, x in arcs if r == p)])
    gamma = max([1, *(1/lo for lo, hi in shares.values() if 0 < lo < 1),
                  *(1/(1-hi) for lo, hi in shares.values() if 0 < hi < 1)])
    original_V, original_u = V, u
    if h == 0 and aggregate:
        V = [("ALL", p) for p in sorted({p for _, p in V})]
        u = np.array([sum(x for (_, q), x in zip(original_V, original_u, strict=True) if q == p)
                      for _, p in V])
    n, F, K, ell = len(V), list(d), len(ends), ends - starts + 1
    p = [v[1] for v in V]
    R = [(v, r, q, b) for v in range(n) for r, (q, b) in recipes[p[v]].items()]
    edges = [(q, v) for v in range(n)
             for q in sorted({q for _, b in recipes[p[v]].values() for q in b})]
    products = sorted(products)                      # a supplier-less q keeps Σx ≤ 0
    stocks = [(v, q) for q, v in edges]
    nr, m, s, j = len(R), len(edges), len(stocks), len(F)
    N = nr + m + s + j
    A = lil_matrix((K*(n + len(products) + j + len(shares)) + 2*len(shares), K*N))
    E = lil_matrix((K*s, K*N))
    b, f, c = np.zeros(A.shape[0]), np.zeros(K*s), np.zeros(K*N)
    U = u[None, :] * ramp[ends - 1][:, None]
    cap = np.arange(K*n).reshape(K, n)
    for t in range(K):
        offset = t*N
        for v in range(n):
            b[cap[t, v]] = U[t, v]
        for i, (v, _, q, _) in enumerate(R):
            A[cap[t, v], offset + i] = 1
            r = K*n + t*len(products) + products.index(q)
            A[r, offset + i] = -1
        for e, (q, _) in enumerate(edges):
            r = K*n + t*len(products) + products.index(q)
            A[r, offset + nr + e] = 1
        for l, q in enumerate(F):
            r = K*(n + len(products)) + t*j + l
            for i, (_, _, output, _) in enumerate(R):
                if output == q:
                    A[r, offset + i] = -1
            A[r, offset + nr + m + s + l] = -1
            b[r] = -d[q][ends[t] - 1]
            c[offset + nr + m + s + l] = ell[t]                  # Σ_t ℓ_t g_t
        for i, (w, q) in enumerate(stocks):
            r = t*s + i                                         # I_t = I_{t-1} + ℓ_t(x − a y)
            E[r, offset + nr + m + i] = 1
            if t:
                E[r, offset - N + nr + m + i] = -1
            else:
                f[r] = h*stock.get((q, p[w]), 0)*u[w]
            for e, (q2, w2) in enumerate(edges):
                if w2 == w and q2 == q:
                    E[r, offset + nr + e] = -ell[t]
            for k, (v, _, _, inputs) in enumerate(R):
                if v == w:
                    E[r, offset + k] = ell[t]*inputs.get(q, 0)
        for l, (q, (lo, hi)) in enumerate(shares.items()):
            r = K*(n + len(products) + j) + t*len(shares) + l
            b[r] = d[q][ends[t] - 1]
            for i, (_, name, output, _) in enumerate(R):
                if output == q:
                    A[r, offset + i] = 1
                    r0 = K*(n + len(products) + j + len(shares)) + 2*l
                    A[r0, offset + i] = ell[t]*(lo - (name == 'ncm'))
                    A[r0+1, offset + i] = ell[t]*((name == 'ncm') - hi)
    original_cap = cap[:, [V.index(("ALL", q)) for _, q in original_V]] if (
        h == 0 and aggregate) else cap
    original_U = original_u[None, :] * ramp[ends - 1][:, None]
    Mv = np.array([gamma*max(M[q] for q, _ in recipes[p].values()) for _, p in original_V])
    return {"V": original_V, "u": original_u, "a": a, "d": d, "T": T, "N": N,
            "A": A.tocsr(), "b": b, "E": E.tocsr(), "f": f, "c": c,
            "cap": original_cap, "U": original_U, "ends": ends, "ell": ell,
            "M": Mv, "Mcap": ell[:, None]*Mv[None, :],       # one unit of rate lasts ℓ_t months
            "total": float(sum(x.sum() for x in d.values())),
            "recipes": recipes, "shares": shares, "stock": stock,
            "recourse": {"h": h, "sigma": sigma, "L": L}}


def solve(M, D, dual=True, f=None):
    """Solve phi(D); independently solve its bounded dual; return residual certificates.

    f: loss fraction per node (default 1); disrupted capacity is (1 - f) U for t <= D.
    """
    D = np.asarray(D, float)
    f_loss = np.ones(len(D)) if f is None else np.asarray(f, float)
    if D.shape != (len(M["V"]),) or (D < 0).any() or not np.isfinite(D).all():
        raise ValueError("One finite nonnegative duration per node required")
    if not np.isin(D[D > 0], M["ends"]).all():
        raise ValueError("Durations must be block ends")
    A, E, c, f = (M[x] for x in ("A", "E", "c", "f"))
    b = M["b"].copy()
    b[np.unique(M["cap"])] = 0
    np.add.at(b, M["cap"].ravel(),
              (M["U"] * (1 - f_loss*(M["ends"][:, None] <= D))).ravel())
    R = linprog(c, A_ub=A, b_ub=b, A_eq=E if E.shape[0] else None,
                b_eq=f if len(f) else None, bounds=(0, None), method="highs")
    status = {0: "optimal", 1: "limit", 2: "infeasible", 3: "unbounded", 4: "numerical"}
    out = {"status": status.get(R.status, "unknown"), "message": R.message}
    if R.status:
        return out
    out.update(phi=float(R.fun), dual=None, gap=None,
               residual=float(max(0, np.max(A @ R.x - b, initial=0),
                                  np.max(np.abs(E @ R.x - f), initial=0), -R.x.min())))
    if dual:
        B = [(0, None)]*A.shape[0] + [(None, None)]*E.shape[0]
        for t in range(len(M["ends"])):
            for v in range(len(D)):
                B[M["cap"][t, v]] = (0, M["Mcap"][t, v])
        Q = linprog(np.r_[b, -f], A_ub=hstack([-A.T, E.T]).tocsr(),
                    b_ub=c, bounds=B, method="highs")
        if Q.status:
            return {"status": "dual_" + status.get(Q.status, "unknown"), "message": Q.message}
        out.update(dual=float(-Q.fun), gap=float(abs(R.fun + Q.fun)))
    return out


def phi(V, u, a, d, D, h=0.0, sigma=0.0, L=1.0, final="cell"):
    """Return minimum cumulative shortfall and status; design §4."""
    R = solve(matrices(V, u, a, d, h, sigma, L, final), D, dual=False)
    return R.get("phi"), R["status"]
