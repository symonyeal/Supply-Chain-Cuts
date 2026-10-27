"""Native LP certificates against hand-derived shortage and the SciPy oracle."""
# N: physical network; D: outage months; phi: cumulative shortfall.
import json
import struct
import subprocess

import pytest

from analysis.check_native_model import compare
from chokepoint.net import model
from chokepoint.recourse import solve


def test_native_comparator_rejects_wrong_values_and_missing_states():
    old = [{'key': 'toy', 'ends': [12, 24], 'shape': [1, 0, 1], 'total': 2,
            'states': [{'D': [12], 'status': 'optimal', 'phi': 1.0, 'dual': 1.0,
                        'gap': 0.0, 'residual': 0.0}]}]
    wrong = json.loads(json.dumps(old))
    wrong[0]['states'][0]['phi'] = 0.1
    assert not compare(old, wrong, 1e-7)['within_tolerance']
    wrong[0]['states'] = []
    assert not compare(old, wrong, 1e-7)['within_tolerance']


def test_native_stock_ramp_partial_loss_and_validation(native):
    E = native('sc-model-check')
    N = {'nodes': [{'country': 'A', 'product': p, 'capacity': 1 / 12}
                   for p in ('mine', 'cell')], 'finals': ['cell'],
         'a': [['mine', 'cell', 1]], 'requirement': {'mine': 1, 'cell': 1}, 'ncm': 0.5}
    cases = []
    for h, sigma, f in ((0, 0, None), (1, 0, None), (1, 0.1, [0.4, 1]),
                        (0, 0.5, [0, 1])):
        config = {'h': h, 'sigma': sigma, 'L': 6}
        if f is not None:
            config['f'] = f
        cases.append({'key': f'{h}:{sigma}:{f}', 'network': N, 'config': config,
                      'states': [[0, 0], [12, 0], [0, 12], [12, 12]]})
    payload = ''.join(json.dumps(case) + '\n' for case in cases)
    result = subprocess.run([E], input=payload,
                            capture_output=True, text=True, check=True)
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert rows[0]['highs'] == '1.12.0'
    assert rows[0]['states'][1]['phi'] == pytest.approx(1)
    assert struct.pack('>d', rows[0]['states'][1]['residual']) == bytes(8)
    assert rows[1]['states'][1]['phi'] == pytest.approx(11 / 12)
    for case, out in zip(cases, rows, strict=True):
        cfg = case['config'].copy()
        f = cfg.pop('f', None)
        M = model(N, **cfg)
        for state, row in zip(case['states'], out['states'], strict=True):
            expected = solve(M, state, f=f)
            assert row['status'] == expected['status']
            for name in ('phi', 'dual', 'gap', 'residual'):
                assert row[name] == pytest.approx(expected[name], abs=1e-7)
    bad = dict(cases[0], states=[[5, 0]])
    result = subprocess.run([E], input=json.dumps(bad) + '\n',
                            capture_output=True, text=True, check=True)
    assert 'block-end' in json.loads(result.stdout)['error']
