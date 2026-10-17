"""Alternative recipes: hand solutions, exact blocks and independent cut enumeration."""
import numpy as np
import pytest

from chokepoint.brute import enumerate_brute, enumerate_lattice
from chokepoint.cuts import enumerate_cuts
from chokepoint.recourse import matrices, solve


R = {'cam': {'lfp': ('cam_lfp', {'li': 1}),
             'ncm': ('cam_ncm', {'li': 1, 'pcam': 1})},
     'cell': {'lfp': ('cell', {'cam_lfp': 1}), 'ncm': ('cell', {'cam_ncm': 1})}}
V = [('A', 'pcam'), ('A', 'li'), ('A', 'cam'), ('A', 'cell')]


def test_lfp_survives_precursor_loss():
    M = matrices(V, [10]*4, {}, [10, 10], recipes=R, shares={'cell': (0, 1)})
    z = solve(M, [2, 0, 0, 0])
    assert z['status'] == 'optimal' and z['phi'] == pytest.approx(0)
    assert z['gap'] < 1e-7
    M = matrices(V, [10]*4, {}, [10, 10], recipes=R, shares={'cell': (0.25, 0.75)})
    assert solve(M, [2, 0, 0, 0])['phi'] == pytest.approx(20)


def test_share_bounds_apply_over_the_horizon():
    M = matrices(V, [5, 10, 10, 10], {}, [10, 10], recipes=R,
                 shares={'cell': (0.25, 0.75)})
    # Month 1: 10 LFP; month 2: 5 LFP + 5 NCM. No surplus can satisfy the quota.
    z = solve(M, [1, 0, 0, 0])
    assert z['phi'] == pytest.approx(0) and z['gap'] < 1e-7


def test_recipe_blocks_and_dual_bounds():
    rng = np.random.default_rng(8)
    stock = {('li', 'cam'): 1, ('pcam', 'cam'): 0.5,
             ('cam_lfp', 'cell'): 0.5, ('cam_ncm', 'cell'): 0.5}
    for bounds in ((0, 1), (0.25, 0.75), (0, 0), (1, 1)):
        for _ in range(10):
            u = rng.uniform(0, 15, 4)
            D = rng.choice([0, 2, 4], 4)
            kw = {'recipes': R, 'shares': {'cell': bounds}, 'h': 0.2, 'stock': stock}
            A = solve(matrices(V, u, {}, [10]*4, **kw), D)
            B = solve(matrices(V, u, {}, [10]*4, ends=[2, 4], **kw), D)
            assert A['status'] == B['status'] == 'optimal'
            assert A['phi'] == pytest.approx(B['phi']) and B['gap'] < 1e-7


def test_recipe_lattice_brute_and_milp_agree():
    rng = np.random.default_rng(9)
    W = [*V, ('B', 'cam'), ('B', 'cell')]
    for bounds in ((0, 1), (0.25, 0.75)):
        u = np.full(6, 12.0)
        u[[2, 4]], u[[3, 5]] = rng.dirichlet([1, 1])*12, rng.dirichlet([1, 1])*12
        M = matrices(W, u, {}, [10]*4,
                     recipes=R, shares={'cell': bounds})
        assert solve(M, [0]*6)['phi'] == pytest.approx(0)
        brute = {tuple(D) for D in enumerate_brute(M, [2, 4], alpha=0.25, k=2)}
        lattice = {tuple(D) for D in enumerate_lattice(M, [2, 4], alpha=0.25, k=2)['cuts']}
        C = enumerate_cuts(M, [2, 4], alpha=0.25, k=2, time_limit=120)
        assert C['complete'] and {tuple(c['D']) for c in C['cuts']} == brute == lattice


def test_baseline_failure_is_the_empty_cut():
    M = matrices([('A', 'cell')], [0.1], {}, [1, 1])
    assert enumerate_brute(M, [1, 2], k=0) == [[0]]
    assert enumerate_lattice(M, [1, 2], k=0)['cuts'] == [[0]]


def test_restored_by_half_horizon_makes_quota_nonbinding():
    rng = np.random.default_rng(10)
    A = matrices(V, [5, 10, 10, 10], {}, [10]*4, recipes=R, shares={'cell': (0, 1)})
    B = matrices(V, [5, 10, 10, 10], {}, [10]*4, recipes=R,
                 shares={'cell': (0.25, 0.75)})
    for _ in range(40):
        D = rng.choice([0, 1, 2], 4)
        assert solve(A, D)['phi'] == pytest.approx(solve(B, D)['phi'])
