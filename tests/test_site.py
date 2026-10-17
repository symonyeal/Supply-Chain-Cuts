"""A cut's predecessor coordinates identify its witness independently of list order."""
import json
from pathlib import Path

import pytest

from analysis.build_site import certificates
from chokepoint.net import build, model
from chokepoint.recourse import solve


def test_frozen_witness_association():
    path = Path('results/liion-residual-2395a5c/cuts/base_a0.25_h0_s0_L6.json')
    R = json.loads(path.read_text(encoding='utf-8'))
    C = certificates(R)
    M = model(build(), durations=(3, 6, 12))
    for S in R['cuts']:
        D = [dict(S).get(v, 0) for v in range(len(M['V']))]
        assert C[json.dumps(S)]['phi'] == pytest.approx(solve(M, D, dual=False)['phi'])
