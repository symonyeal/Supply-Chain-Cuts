"""Recourse LP φ(z) (design §4)."""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix


def phi(V, u, a, d, D, h=0.0, sigma=0.0, L=1.0, final="cell"):
    """
    φ(z) = min Σ_τ g_τ
      s.t. y_vτ ≤ ū_vτ = (1 − [τ ≤ D_v]) u_v (1 + σ min(1, τ/L))     (capacity)
           Σ_w x_vw,τ ≤ y_vτ                                          (shipments ≤ output)
           I_wp,τ = I_wp,τ−1 + Σ_{v: p(v)=p} x_vw,τ − a_p,q(w) y_wτ,  I_wp,0 = h a_p,q(w) u_w
           Σ_{q(w)=final} y_wτ + g_τ ≥ d_τ                            (demand)
           x, y, I, g ≥ 0,  τ = 1..T.

    INPUT  V ......... nodes (c, p), n of them
           u ......... monthly capacity u_v
           a ......... {(p, q): units of input p per unit of q}
           d ......... demand d_τ, length T
           D ......... disruption duration of each node, months (0: none)
           h, sigma, L recourse r: inventory cover (months), spare fraction, ramp-up (months)
    OUTPUT φ(z), status ("optimal" or the solver's status message)
    """
    n, T = len(V), len(d)
    p = [v[1] for v in V]
    E = [(v, w) for v in range(n) for w in range(n) if (p[v], p[w]) in a]  # edges v → w
    P = sorted({(w, p[v]) for v, w in E})                                   # inventories (w, p)
    m, k = len(E), len(P)
    N = n + m + k + 1                                  # per period: y, x, I, g
    y = lambda t, v: t*N + v
    x = lambda t, e: t*N + n + e
    I = lambda t, i: t*N + n + m + i
    g = lambda t: t*N + n + m + k

    c = np.zeros(T*N); c[[g(t) for t in range(T)]] = 1
    tau = np.arange(1, T + 1)
    ubar = (tau[None, :] > D[:, None]) * u[:, None] * (1 + sigma*np.minimum(1, tau/L))[None, :]
    bounds = [(0, None)]*(T*N)
    for t in range(T):
        for v in range(n): bounds[y(t, v)] = (0, ubar[v, t])

    A_ub, b_ub = lil_matrix((T*(n + 1), T*N)), np.zeros(T*(n + 1))
    A_eq, b_eq = lil_matrix((T*k, T*N)), np.zeros(T*k)
    for t in range(T):
        for e, (v, w) in enumerate(E): A_ub[t*(n + 1) + v, x(t, e)] = 1
        for v in range(n): A_ub[t*(n + 1) + v, y(t, v)] = -1
        r = t*(n + 1) + n                                       # −Σ y_final − g ≤ −d
        for v in range(n):
            if p[v] == final: A_ub[r, y(t, v)] = -1
        A_ub[r, g(t)], b_ub[r] = -1, -d[t]
        for i, (w, q) in enumerate(P):
            r = t*k + i
            A_eq[r, I(t, i)] = 1
            if t: A_eq[r, I(t - 1, i)] = -1
            else: b_eq[r] = h*a[q, p[w]]*u[w]                   # I_wp,0
            for e, (v, w2) in enumerate(E):
                if w2 == w and p[v] == q: A_eq[r, x(t, e)] = -1
            A_eq[r, y(t, w)] = a[q, p[w]]

    res = linprog(c, A_ub.tocsr(), b_ub, A_eq.tocsr() if k else None, b_eq if k else None,
                  bounds=bounds, method="highs")
    return (res.fun, "optimal") if res.status == 0 else (None, res.message)
