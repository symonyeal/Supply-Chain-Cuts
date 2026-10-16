"""Exposure-aware beta-binomial pooling and country-shock calibration."""
import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.special import betaln


def _eb(N, K):
    """Empirical Bayes: argmax_(a,b) Σ_i log B(K_i + a, N_i − K_i + b) − log B(a, b)."""
    def f(x):
        a, b = np.exp(x)
        return -np.sum(betaln(K + a, N - K + b) - betaln(a, b))
    mean = (K.sum() + 0.5)/(N.sum() + 1)
    R = minimize(f, np.log([mean*10, (1 - mean)*10]), method="L-BFGS-B",
                 bounds=[(-7, 14), (-7, 14)])
    a, b = np.exp(R.x)
    return float(a), float(b), "empirical_bayes" if R.success else "fit_limit"


def fit_rates(V, Y, fit_rho=True):
    """Estimate node annual onset rates from Y[node,year] in {0,1,nan}.

    p_v = (K_v + a_p)/(N_v + a_p + b_p), (a_p, b_p) by empirical Bayes over the nodes of
    product p. A product without exposure borrows the prior fitted over all products,
    labelled as such; missing exposure is never a zero count.
    """
    Y = np.asarray(Y, float)
    if Y.ndim != 2 or len(V) != Y.shape[0] or not np.isin(Y[np.isfinite(Y)], [0, 1]).all():
        raise ValueError("Y must contain observed binary node-years and nan for missing exposure")
    N, K = np.isfinite(Y).sum(axis=1), np.nansum(Y, axis=1)
    p, priors, basis = np.zeros(len(V)), {}, [""]*len(V)
    seen = N > 0
    pool = _eb(N[seen], K[seen]) if seen.any() else (0.5, 0.5, "unobserved_Jeffreys_scenario")
    for product in sorted({p for _, p in V}):
        I = [i for i, (_, q) in enumerate(V) if q == product]
        J = [i for i in I if N[i]]
        a, b, prior_basis = _eb(N[J], K[J]) if J else (*pool[:2], "all_product_pool")
        priors[product] = {"a": a, "b": b, "basis": prior_basis}
        for i in I:
            p[i] = (K[i] + a)/(N[i] + a + b)
            basis[i] = prior_basis if N[i] else "pooled_no_exposure"
    rho, pairs = 0.0, []
    for country in sorted({c for c, _ in V}):
        I = np.array([i for i, (c, _) in enumerate(V) if c == country])
        for t in range(Y.shape[1]):
            J = I[np.isfinite(Y[I, t])]
            if len(J) > 1:
                pairs.append((J, p[I].min(), float(Y[J, t].sum() >= 2)))
    if fit_rho and pairs:
        def loss(r):
            z = 0.0
            for I, pmin, y in pairs:
                s = r*pmin
                q = (p[I] - s)/(1 - s) if s < 1 else np.zeros(len(I))
                counts = np.array([1.0])
                for x in q:
                    counts = np.convolve(counts, [1 - x, x])
                prob = np.clip(s + (1 - s)*counts[2:].sum(), 1e-12, 1 - 1e-12)
                z -= y*np.log(prob) + (1 - y)*np.log1p(-prob)
            return z
        R = minimize_scalar(loss, bounds=(0, 1), method="bounded")
        rho = min([0.0, float(R.x), 1.0], key=loss)
    return {"p": p.tolist(), "rho": rho, "priors": priors,
            "exposure": N.tolist(), "onsets": K.astype(int).tolist(), "basis": basis,
            "rho_country_years": len(pairs)}


def prequential(V, Y, years, train_end=2019):
    """Score each held-out year before updating; compare a fixed pooled training constant."""
    Y, years = np.asarray(Y, float), np.asarray(years)
    train = Y[:, years <= train_end]
    count = np.isfinite(train).sum()
    baseline = (np.nansum(train) + 0.5)/(count + 1)
    scores, base, n = [], [], 0
    for t, year in enumerate(years):
        if year <= train_end:
            continue
        R = fit_rates(V, Y[:, :t], fit_rho=False)
        I = np.isfinite(Y[:, t])
        p, y = np.clip(np.array(R["p"])[I], 1e-12, 1 - 1e-12), Y[I, t]
        scores.extend((-y*np.log(p) - (1 - y)*np.log1p(-p)).tolist())
        base.extend((-y*np.log(baseline) - (1 - y)*np.log1p(-baseline)).tolist())
        n += int(I.sum())
    model, constant = (float(np.mean(x)) if x else None for x in (scores, base))
    return {"model_log_loss": model, "constant_log_loss": constant, "test_node_years": n,
            "improves": bool(n and model < constant), "baseline_p": float(baseline),
            "train_end": train_end}


def duration_weights(records, durations=(3, 6, 12)):
    """Bin realised spell lengths upward onto D_1 < ... < D_J (months = days/30.44).

    An uncensored spell goes to the least D_j ≥ its length (D_J if longer). A censored spell
    longer than D_(J-1) is known to bin to D_J; shorter censored spells are reported, unused.
    """
    counts, short, zero = np.zeros(len(durations)), 0, 0
    for x in records:
        months = (x["days"] or 0)/30.44
        if x["censored"] and months <= durations[-2]:
            short += 1
        elif months <= 0:
            zero += 1
        else:
            counts[min(np.searchsorted(durations, months), len(durations) - 1)] += 1
    basis = "empirical_binned" if counts.sum() else "uniform_duration_scenario"
    w = counts/counts.sum() if counts.sum() else np.full(len(durations), 1/len(durations))
    return {"durations": list(durations), "weights": w.tolist(), "basis": basis,
            "counts": counts.astype(int).tolist(), "censored_short": short, "zero": zero}
