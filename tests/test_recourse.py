"""φ(z) on a toy network with shortfalls derived by hand (design §4).

Graphite from CN (8/month) and MZ (2/month) feeds cells in KR (10/month), one unit of
graphite per cell, demand 10/month, T = 2.
"""
import numpy as np
from chokepoint.recourse import phi

V = [("CN", "gr"), ("MZ", "gr"), ("KR", "cell")]
u = np.array([8.0, 2.0, 10.0])
a = {("gr", "cell"): 1.0}
d = np.array([10.0, 10.0])


def f(D, **r):
    v, status = phi(V, u, a, d, np.array(D, float), **r)
    assert status == "optimal"
    return v


def test_hand_derived():
    assert abs(f([0, 0, 0])) < 1e-9                       # current flows feasible
    assert abs(f([1, 0, 0]) - 8) < 1e-9                   # CN out one month: 10 − 2
    assert abs(f([2, 0, 0]) - 16) < 1e-9
    assert abs(f([0, 0, 2]) - 20) < 1e-9                  # cell node out
    assert abs(f([1, 0, 0], h=1) - 0) < 1e-9              # I_0 = 10 covers month 1
    assert abs(f([2, 0, 0], h=1) - 6) < 1e-9              # 20 needed, 10 + 2 + 2 available
    assert abs(f([2, 0, 0], sigma=0.5, L=1) - 14) < 1e-9  # MZ ramps to 3: 2·(10 − 3)


def test_monotone():
    """Prop. 1: D ≤ D′ componentwise ⇒ φ(D) ≤ φ(D′)."""
    rng = np.random.default_rng(0)
    for _ in range(50):
        D = rng.integers(0, 3, 3)
        Dp = np.maximum(D, rng.integers(0, 3, 3))
        assert f(D, h=0.5, sigma=0.2, L=2) <= f(Dp, h=0.5, sigma=0.2, L=2) + 1e-9
