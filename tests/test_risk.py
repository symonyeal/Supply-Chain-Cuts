"""Exact risk compared with a hand-enumerated categorical state space."""
from itertools import product

import numpy as np
import pytest

from chokepoint.risk import (bracket, exact_union, importance_sampling, residual_sampling,
                            state_probability)
from chokepoint.rates import fit_rates, prequential
from chokepoint.recourse import matrices


def test_correlated_duration_union_and_tail():
    V = [("A", "ore"), ("A", "metal"), ("B", "cell")]
    p = np.array([0.1, 0.2, 0.3])
    C = [[2, 0, 0], [1, 1, 0], [0, 0, 2]]
    durations, weights, rho = [1, 2], [0.25, 0.75], 0.6
    probabilities, fail, tail = [], 0, 0
    for D in product([0, 1, 2], repeat=3):
        q = state_probability(V, p, rho, durations, weights, D)
        probabilities.append(q)
        if any(all(x <= y for x, y in zip(S, D, strict=True)) for S in C):
            fail += q
        if sum(x > 0 for x in D) > 1:
            tail += q
    assert sum(probabilities) == pytest.approx(1)
    R = bracket(V, p, rho, durations, weights, C, k=1, complete=True)
    assert R["L"] == pytest.approx(fail)
    assert R["tail"] == pytest.approx(tail)
    assert R["U"] == pytest.approx(min(1, fail + tail))
    assert exact_union(V, p, 0, durations, weights, [[0, 0, 0]]) == 1
    with pytest.raises(ValueError, match="complete"):
        bracket(V, p, rho, durations, weights, C, k=1, complete=False)


def test_importance_sampling_known_probability():
    V = [("A", "cell")]
    M = matrices(V, [10], {}, [10, 10])
    R = importance_sampling(M, [0.08], 0, [1, 2], [0.5, 0.5],
                            [[2]], alpha=0.6, n=3000, pilot=300, seed=7)
    assert abs(R["estimate"] - 0.04) < 4*R["se"]
    assert R["effective_sample_size"] > 0


def test_rates_planted_marginal_and_no_missing_as_zero():
    rng = np.random.default_rng(5)
    V = [(str(i), "ore") for i in range(60)]
    Y = (rng.random((60, 300)) < 0.2).astype(float)
    Y[0, :] = np.nan
    R = fit_rates(V, Y)
    assert abs(np.mean(R["p"]) - 0.2) < 0.02
    assert R["exposure"][0] == 0
    assert R["basis"][0] == "pooled_no_exposure"
    P = prequential(V, Y, np.arange(1725, 2025), train_end=2019)
    assert np.isfinite(P["model_log_loss"])


def test_residual_hand_enumerated_probability():
    """Eight units of ore feed two 4-cell suppliers: their 1+1 pair is the residual cut."""
    V = [("A", "ore"), ("A", "cell"), ("B", "cell")]
    p, rho, durations, weights = [0.1, 0.2, 0.3], 0.6, [1, 2], [0.25, 0.75]
    M = matrices(V, [8, 4, 4], {("ore", "cell"): 1}, [8, 8])
    C = [[1, 0, 0], [0, 2, 0], [0, 0, 2]]
    F = [*C, [0, 1, 1]]
    P = sum(state_probability(V, p, rho, durations, weights, D)
            for D in product([0, 1, 2], repeat=3)
            if any(all(x <= y for x, y in zip(S, D, strict=True)) for S in F))
    L = exact_union(V, p, rho, durations, weights, C)
    s = rho*min(p[:2])
    r = (1-p[0])*(p[1]-s)/(1-s)*p[2]*weights[0]**2
    assert P == pytest.approx(L + r)
    R = residual_sampling(M, p, rho, durations, weights, C, alpha=0.3,
                          n=10000, seed=7, complete=True, k=1)
    assert R["L"] == pytest.approx(L)
    assert R["estimate"] >= L
    assert R["ci95"][0] <= P <= R["ci95"][1]
    assert R["residual_events"] > 0
    assert R["se"] == pytest.approx(np.sqrt(
        R["residual_estimate"]*(1-R["residual_estimate"])/(R["n"]-1)))
    B = residual_sampling(M, p, rho, durations, weights, C, alpha=0.3,
                          n=10000, seed=7, complete=False, k=1)
    assert B["estimate"] == R["estimate"]
    assert B["lp_states"] > R["lp_states"]


def test_residual_zero_events_have_an_interval():
    M = matrices([("A", "cell")], [10], {}, [10, 10])
    R = residual_sampling(M, [0.8], 0.6, [1, 2], [0.5, 0.5], [[2]],
                          alpha=0.6, n=1000, seed=7, complete=True, k=1)
    assert R["estimate"] == pytest.approx(0.4)
    assert R["zero_residuals"] and R["se"] == 0 and R["lp_states"] == 0
    assert R["ci95"] == pytest.approx([0.4, 0.4 + 1 - 0.025**(1/1000)])


def test_residual_matches_crude_on_random_network():
    from chokepoint.brute import enumerate_brute
    rng = np.random.default_rng(17)
    V = [("A", "ore"), ("B", "ore"), ("A", "cell"), ("C", "cell")]
    u = rng.uniform(0.6, 1.2, len(V))
    M = matrices(V, u, {("ore", "cell"): 1}, [min(u[:2].sum(), u[2:].sum())]*2)
    C = enumerate_brute(M, [1, 2], alpha=0.25, k=1)
    p, w = [0.13, 0.2, 0.18, 0.24], [0.4, 0.6]
    R = residual_sampling(M, p, 0.4, [1, 2], w, C, n=6000, seed=7,
                          complete=True, k=1)
    B = importance_sampling(M, p, 0.4, [1, 2], w, C, n=6000, seed=8,
                            complete=True, k=1, crude=True)
    assert abs(R["estimate"]-B["estimate"]) < 4*np.hypot(R["se"], B["se"])
    assert R["estimate"] >= R["L"]


def test_residual_all_events_and_invalid_sample_size():
    M = matrices([("A", "cell")], [10], {}, [10, 10])
    R = residual_sampling(M, [1], 1, [2], [1], [], alpha=0.6, n=20)
    assert R["estimate"] == 1 and R["residual_events"] == 20
    assert R["ci95"][0] == pytest.approx(0.025**(1/20))
    assert R["ci95"][1] == 1
    with pytest.raises(ValueError, match="two"):
        residual_sampling(M, [0.1], 0, [2], [1], [[2]], n=1)


def test_rates_planted_rho():
    """Country shocks at rho = 0.5 (s = rho min p) are recovered from multi-onset years."""
    rng = np.random.default_rng(8)
    C, P, T, p, rho = 40, 3, 150, 0.12, 0.5
    V = [(str(c), q) for c in range(C) for q in "abc"[:P]]
    s, q = rho*p, (p - rho*p)/(1 - rho*p)
    shock = rng.random((C, T)) < s
    Y = (rng.random((C*P, T)) < q) | np.repeat(shock, P, axis=0)
    R = fit_rates(V, Y.astype(float))
    assert abs(np.mean(R["p"]) - p) < 0.015
    assert abs(R["rho"] - rho) < 0.15
