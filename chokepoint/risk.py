"""Exact cut union, count tail, residual Monte Carlo and latent-state IS."""
from functools import cache
from collections import Counter

import numpy as np
from scipy.stats import beta

from chokepoint.recourse import solve


def _parameters(V, p, rho, durations, weights):
    p, w = np.asarray(p, float), np.asarray(weights, float)
    if (p.shape != (len(V),) or not np.isfinite(p).all() or (p < 0).any()
            or (p > 1).any() or not 0 <= rho <= 1 or (w < 0).any()
            or len(w) != len(durations) or not np.isclose(w.sum(), 1)):
        raise ValueError("Valid node probabilities, rho and categorical duration weights required")
    groups = [np.array([i for i, (c, _) in enumerate(V) if c == country])
              for country in sorted({c for c, _ in V})]
    s = np.array([rho*p[I].min() for I in groups])
    q = p.copy()
    for I, x in zip(groups, s, strict=True):
        q[I] = (p[I] - x)/(1 - x) if x < 1 else 0
    return p, w, groups, s, q


def _law(p, durations, weights):
    out = {0: 1 - p}
    for D, w in zip(durations, weights, strict=True):
        out[D] = out.get(D, 0) + p*w
    return sorted((int(D), float(x)) for D, x in out.items() if x)


def state_probability(V, p, rho, durations, weights, D):
    """Exact probability of one complete categorical node state D."""
    _, w, groups, s, q = _parameters(V, p, rho, durations, weights)
    prob = 1.0
    for I, x in zip(groups, s, strict=True):
        independent = np.prod([dict(_law(q[v], durations, w)).get(D[v], 0) for v in I])
        shock = np.prod([dict(_law(1, durations, w)).get(D[v], 0) for v in I])
        prob *= (1 - x)*independent + x*shock
    return float(prob)


def exact_union(V, p, rho, durations, weights, cuts):
    """P(any minimal duration cut is contained in Z), by a memoised decision recursion."""
    _, w, groups, s, q = _parameters(V, p, rho, durations, weights)
    C = tuple(sorted({tuple((v, int(D)) for v, D in enumerate(S) if D) for S in cuts}))
    relevant = {v for S in C for v, _ in S}
    variables = []
    for j, I in enumerate(groups):
        J = [v for v in I if v in relevant]
        if J:
            variables.append((j, -1))
            variables.extend((j, v) for v in J)

    @cache
    def visit(t, active, shock):
        if () in active:
            return 1.0
        if not active:
            return 0.0
        j, v = variables[t]
        if v < 0:
            return (1 - s[j])*visit(t + 1, active, 0) + s[j]*visit(t + 1, active, 1)
        prob = 0.0
        for D, z in _law(1 if shock else q[v], durations, w):
            remaining = tuple(sorted({tuple((u, a) for u, a in S if u != v)
                                      for S in active if all(u != v or D >= a for u, a in S)}))
            prob += z*visit(t + 1, remaining, shock)
        return prob

    return float(visit(0, C, 0))


def bracket(V, p, rho, durations, weights, cuts, k=3, complete=False):
    """Return exact L <= P(fail) <= U; requires complete enumeration through support k."""
    if not complete:
        raise ValueError("A complete cut enumeration through k is required for the upper bound")
    _, w, groups, s, q = _parameters(V, p, rho, durations, weights)
    positive = sum(x for D, x in zip(durations, w, strict=True) if D > 0)
    counts = np.array([1.0])
    for I, shock in zip(groups, s, strict=True):
        independent, common = np.array([1.0]), np.array([1.0])
        for v in I:
            independent = np.convolve(independent, [1 - q[v]*positive, q[v]*positive])
            common = np.convolve(common, [1 - positive, positive])
        counts = np.convolve(counts, (1 - shock)*independent + shock*common)
    L = exact_union(V, p, rho, durations, w, cuts)
    tail = float(counts[k + 1:].sum())
    return {"L": L, "U": min(1.0, L + tail), "tail": tail, "k": k,
            "attribution": [exact_union(V, p, rho, durations, w, [S])/L if L else 0
                            for S in cuts], "attribution_overlaps": True}


def binomial_interval(m, n):
    """Exact central 95% binomial confidence limits (Clopper and Pearson, 1934)."""
    lo = float(beta.ppf(0.025, m, n-m+1)) if m else 0.0
    hi = float(beta.ppf(0.975, m+1, n-m)) if m < n else 1.0
    return [lo, hi]


def residual_sampling(M, p, rho, durations, weights, cuts, alpha=0.25, n=4000,
                      seed=0, complete=False, k=3):
    """P(fail) = L + P(fail without an enumerated cut), MODEL §Annual probability.

    INPUT   M, cuts ... recourse model and certified failing duration states
            complete .. enumeration complete through support k
    OUTPUT  exact L, unbiased estimate, sample SE, exact-binomial 95% MC interval
    """
    if n < 2:
        raise ValueError("At least two inference samples required")
    V = M["V"]
    _, w, groups, s, q = _parameters(V, p, rho, durations, weights)
    rng = np.random.default_rng(seed)
    cut = np.asarray(cuts, int).reshape((-1, len(V)))
    L = exact_union(V, p, rho, durations, w, cuts)
    H = rng.random((n, len(s))) < s
    onset = rng.random((n, len(q))) < q
    for j, I in enumerate(groups):
        onset[:, I] |= H[:, j, None]
    D = rng.choice(durations, size=onset.shape, p=w)*onset
    theta, cache, m = alpha*M["total"], {}, 0
    for x in D:
        if len(cut) and np.any(np.all(x >= cut, axis=1)):
            continue
        if complete and np.count_nonzero(x) <= k:
            continue
        key = tuple(x)
        if key not in cache:
            R = solve(M, x, dual=False)
            if R["status"] != "optimal":
                raise RuntimeError(R)
            cache[key] = R["phi"] > theta + 1e-7
        m += cache[key]
    r = m/n
    lo, hi = binomial_interval(m, n)
    return {"L": L, "estimate": L + r, "se": float(np.sqrt(r*(1-r)/(n-1))),
            "ci95": [L + lo, min(1.0, L + hi)], "residual_estimate": r,
            "residual_events": int(m), "zero_residuals": m == 0, "lp_states": len(cache),
            "n": n, "seed": seed, "complete": complete, "k": k,
            "method": "lower_bound_plus_residual", "interval_method": "clopper_pearson_binomial"}


def partial_sampling(M, p, rho, durations, weights, mixtures, losses, alpha=0.25,
                     n=20000, seed=7):
    """Paired full and marked partial losses; samplewise monotonicity certifies S3.

    INPUT   mixtures[v] .. conditional measure probabilities at node v
            losses ...... named scenarios, each mapping measure type to loss fraction
    OUTPUT  probabilities, binomial intervals, paired reductions and maximum phi violation
    """
    if n < 2 or len(mixtures) != len(M["V"]):
        raise ValueError("At least two samples and one measure mixture per node required")
    _, w, groups, s, q = _parameters(M["V"], p, rho, durations, weights)
    rng = np.random.default_rng(seed)
    H = rng.random((n, len(s))) < s
    onset = rng.random((n, len(q))) < q
    for j, I in enumerate(groups):
        onset[:, I] |= H[:, j, None]
    D = rng.choice(durations, size=onset.shape, p=w)*onset
    marks = [rng.choice(list(m), n, p=list(m.values())) for m in mixtures]
    values = {name: np.array([[f.get(m, 1.0) for m in column] for column in marks]).T
              for name, f in losses.items()}
    if any(not np.isfinite(f).all() or (f < 0).any() or (f > 1).any() for f in values.values()):
        raise ValueError("Loss fractions must lie in [0,1]")
    names = ["full", *losses]
    F = {name: np.zeros(n, bool) for name in names}
    cache, violation = {}, 0.0
    for i, d in enumerate(D):
        phi = {}
        for name in names:
            f = np.ones(len(d)) if name == "full" else values[name][i]
            key = tuple((v, int(d[v]), float(f[v])) for v in np.flatnonzero(d))
            if key not in cache:
                R = solve(M, d, dual=False, f=f)
                if R["status"] != "optimal":
                    return {"status": R["status"], "samples_completed": i}
                cache[key] = R["phi"]
            phi[name] = cache[key]
            F[name][i] = phi[name] > alpha*M["total"] + 1e-7
            violation = max(violation, phi[name] - phi["full"])
    counts = Counter()
    for v, column in enumerate(marks):
        counts.update(column[onset[:, v]].tolist())
    out = {"status": "optimal", "n": n, "seed": seed, "alpha": alpha,
           "method": "paired_partial_loss_mc", "max_monotonicity_violation": violation,
           "monotone": violation <= 1e-7 and all(np.all(z <= F["full"]) for z in F.values()),
           "lp_states": len(cache), "onsets_by_measure": dict(counts), "scenarios": {}}
    for name, z in F.items():
        m = int(z.sum())
        r = m/n
        row = {"estimate": r, "se": float(np.sqrt(r*(1-r)/(n-1))),
               "ci95": binomial_interval(m, n), "failures": m}
        if name != "full":
            delta = int(np.count_nonzero(F["full"] & ~z))
            row.update(reduction=delta/n, reduction_ci95=binomial_interval(delta, n))
        out["scenarios"][name] = row
    return out


def importance_sampling(M, p, rho, durations, weights, cuts, alpha=0.25, n=4000,
                        pilot=400, seed=0, complete=False, k=3, crude=False):
    """Estimate failure with a separate cross-entropy pilot and exact latent likelihoods.

    OUTPUT estimate, standard error, normal 95% Monte Carlo interval, weight ESS.
    A zero observed failure gives no useful normal error estimate; zero_events flags it.
    """
    if n < 2 or pilot < 0:
        raise ValueError("At least two inference samples and a nonnegative pilot required")
    V = M["V"]
    _, w, groups, s, q = _parameters(V, p, rho, durations, weights)
    rng, cache = np.random.default_rng(seed), {}
    cut = np.asarray(cuts, int).reshape((-1, len(V)))
    theta = alpha*M["total"]

    def failure(D):
        if len(cut) and np.any(np.all(D >= cut, axis=1)):
            return True
        if complete and np.count_nonzero(D) <= k:
            return False
        key = tuple(D)
        if key not in cache:
            R = solve(M, D, dual=False)
            if R["status"] != "optimal":
                raise RuntimeError(R)
            cache[key] = R["phi"] > theta + 1e-7
        return cache[key]

    def sample(N, sh, qi):
        H = rng.random((N, len(s))) < sh
        B = rng.random((N, len(q))) < qi
        onset = B.copy()
        for j, I in enumerate(groups):
            onset[:, I] |= H[:, j, None]
        D = rng.choice(durations, size=onset.shape, p=w)*onset
        logw = np.zeros(N)
        for X, original, proposal in ((H, s, sh), (B, q, qi)):
            I = (original > 0) & (original < 1)
            logw += (X[:, I]*np.log(original[I]/proposal[I])
                     + (~X[:, I])*np.log((1 - original[I])/(1 - proposal[I]))).sum(axis=1)
        z = np.array([failure(x) for x in D], float)
        return H, B, z, np.exp(logw)

    sh, qi = s.copy(), q.copy()
    if not crude:
        relevant = np.any(cut > 0, axis=0) if len(cut) else np.ones(len(V), bool)
        qi[(q > 0) & (q < 1) & relevant] = np.clip(q[relevant & (q > 0) & (q < 1)], 0.15, 0.8)
        sh[(s > 0) & (s < 1)] = np.clip(s[(s > 0) & (s < 1)], 0.05, 0.8)
        if pilot:
            H, B, z, likelihood = sample(pilot, sh, qi)
            elite = z*likelihood
            if np.count_nonzero(elite) > 2:
                for X, original, proposal in ((H, s, sh), (B, q, qi)):
                    I = (original > 0) & (original < 1)
                    target = (elite[:, None]*X).sum(axis=0)/elite.sum()
                    proposal[I] = np.clip(0.5*proposal[I] + 0.5*target[I], 0.01, 0.95)
    _, _, z, likelihood = sample(n, sh, qi)
    values = z*likelihood
    estimate, se = float(values.mean()), float(values.std(ddof=1)/np.sqrt(n))
    return {"estimate": estimate, "se": se,
            "ci95": [max(0, estimate - 1.96*se), min(1, estimate + 1.96*se)],
            "effective_sample_size": float(likelihood.sum()**2/(likelihood @ likelihood)),
            "n": n, "pilot": 0 if crude else pilot, "seed": seed,
            "zero_events": bool(not z.any()), "lp_states": len(cache),
            "method": "crude_mc" if crude else "cross_entropy_importance_sampling"}
