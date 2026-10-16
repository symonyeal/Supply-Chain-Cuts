"""Planted export changes and independent fixed-effects normal equations (W2)."""
import numpy as np
import pytest

from chokepoint.severity import effect, estimate
from chokepoint.recourse import matrices
from chokepoint.risk import partial_sampling


def test_export_response_equals_fixed_effects():
    E = [{"country": "A", "countries": ["A", "B"],
          "Y": [[0.9, 1, 0.75, 0.6], [0.9, 1, 1.05, 1.1]]},
         {"country": "C", "countries": ["C", "D", "E"],
          "Y": [[0.9, 1, 0.65, 0.4], [0.9, 1, 1.05, 1.1], [0.9, 1, 1.05, 1.1]]}]
    A, b, weights, offset = [], [], [], 0
    for k, e in enumerate(E):
        for i, y in enumerate(e["Y"]):
            for t, value in enumerate(y):
                row = np.zeros(5 + 6 + 3)
                row[offset+i] = 1
                if t != 1:
                    j = [0, 2, 3].index(t)
                    row[5+3*k+j] = 1
                    if i == 0:
                        row[11+j] = 1
                A.append(row)
                b.append(value)
                weights.append(0.5 if i == 0 else 0.5/(len(e["Y"])-1))
        offset += len(e["Y"])
    w = np.sqrt(weights)
    x = np.linalg.lstsq(np.array(A)*w[:, None], np.array(b)*w, rcond=None)[0]
    assert x[-3:] == pytest.approx(np.mean([effect(e) for e in E], axis=0))
    assert x[-3:] == pytest.approx([0, -0.35, -0.6])


def test_planted_severity_and_unidentified_fallback():
    E = [{"country": str(i), "countries": [str(i), "control"], "measure": "M1", "hs12": "1",
          "Y": [[1, 1, 0.9, 0.9], [1, 1, 1, 1]]} for i in range(12)]
    R = estimate(E, B=40, seed=6)
    assert R["M1"]["loss"] == pytest.approx(0.1)
    assert R["M1"]["identified"] and R["M1"]["verdict"] == "supported"
    assert R["M1"]["f"] == pytest.approx(0.1)
    assert R["M4"]["f"] == 1 and not R["M4"]["identified"]
    assert R["M4"]["verdict"] == "untestable"


def test_paired_partial_losses_and_endpoints():
    M = matrices([("A", "cell")], [10], {}, [10, 10])
    R = partial_sampling(M, [1], 1, [2], [1], [{"M1": 1}],
                         {"central": {"M1": 0.5}, "low": {"M1": 0}, "high": {"M1": 1}},
                         alpha=0.6, n=100, seed=7)
    assert R["monotone"] and R["max_monotonicity_violation"] == 0
    S = R["scenarios"]
    assert S["full"]["estimate"] == S["high"]["estimate"] == 1
    assert S["central"]["estimate"] == S["low"]["estimate"] == 0
    assert S["central"]["reduction"] == 1
    assert S["central"]["ci95"][1] > 0
    assert R["lp_states"] == 3
