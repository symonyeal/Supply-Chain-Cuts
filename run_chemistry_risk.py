"""Risk for certified W3 scenarios: python run_chemistry_risk.py CUT_RUN OUT_RUN.

The approved share intervals have the same failure event on this horizon (MODEL).
Compute free-choice risk once and label its reuse for the nonbinding bounded scenario.
"""
import json
import sys
from pathlib import Path

from chokepoint.chemistry import model
from chokepoint.fetch import stamp
from chokepoint.net import build
from chokepoint.recourse import solve
from chokepoint.risk import bracket, residual_sampling
from run_risk import dense, truncate


def job(sector, run, out):
    """Keep the frozen onset law; change only recourse and its certified cut union."""
    run_stamp = stamp()
    source = Path('results') / run / 'cuts'
    previous = Path('results') / f'{sector}-residual-2395a5c'
    old = json.loads((previous / 'risk.json').read_text())
    N = build(sector=sector)
    frozen = json.loads((previous / 'network.json').read_text())[sector]
    assert all(N[k] == x for k, x in frozen.items())
    M = model(N)
    assert list(map(list, M['V'])) == old['nodes']
    baseline = solve(model(N, shares=(0.5, 0.5), T=1, durations=(1,)), [0]*len(M['V']))
    assert baseline['status'] == 'optimal' and baseline['phi'] <= 1e-7
    assert baseline['gap'] <= 1e-6
    p, rho, w = old['rates']['p'], old['rates']['rho'], old['durations']['weights']
    configs = {}
    for path in sorted(source.glob(f'{sector}_free_*.json')):
        R = json.loads(path.read_text())
        B = json.loads(path.with_name(path.name.replace('_free_', '_bounded_')).read_text())
        assert R['complete'] and B['complete'] and R['cuts'] == B['cuts']
        assert all(c['certified'] for c in R['certificates'])
        for DJ in (3, 6, 12):
            D, q = truncate(w, DJ)
            S = [s for s in R['cuts'] if all(d <= DJ for _, d in s)]
            key = R['task'].split('_free_')[1] + f'_D{DJ}'
            configs[key] = bracket(M['V'], p, rho, D, q,
                                   [dense(s, len(M['V'])) for s in S], complete=True)
    estimates = {}
    for alpha in ((0.1, 0.25, 0.5) if sector == 'liion' else (0.1, 0.25)):
        R = json.loads((source / f'{sector}_free_a{alpha}_h0_s0_L6.json').read_text())
        S = [dense(s, len(M['V'])) for s in R['cuts']]
        estimates[str(alpha)] = residual_sampling(M, p, rho, (3, 6, 12), w, S,
                                                  alpha=alpha, n=20000, seed=8, complete=True)
        print(sector, alpha, estimates[str(alpha)]['estimate'], flush=True)
    data = {'stamp': run_stamp, 'sector': sector, 'cut_bundle': run,
            'reference_bundle': previous.name, 'network_unchanged': True,
            'rates_unchanged': True, 'reference_monthly_mix_certificate': baseline,
            'share_equivalence': 'MODEL: restored by half horizon; monthly reference mix feasible',
            'configs': configs, 'residual': estimates,
            'scenarios': {'free': [0, 1], 'bounded_same_failure_event': [0.25, 0.75]}}
    path = Path('results') / out
    path.mkdir(parents=True, exist_ok=True)
    (path / f'{sector}.json').write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    for sector in ('liion', 'joint'):
        job(sector, *sys.argv[1:])
