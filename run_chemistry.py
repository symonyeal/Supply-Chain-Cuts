"""Certified chemistry-choice sweeps: python run_chemistry.py RUN WORKERS.

The physical network and capacities remain the 50% reference. Lattice enumeration and
direct primal/dual/predecessor certificates are retained separately from legacy results.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from chokepoint.brute import enumerate_lattice
from chokepoint.chemistry import model
from chokepoint.fetch import stamp
from chokepoint.net import build
from chokepoint.recourse import solve
from run_cuts import DURATIONS, EPS, K, certify, sparse, tasks

METALS = {'mine_co', 'refined_co', 'mine_ni', 'refined_ni', 'mine_mn', 'pcam'}


def job(sector, bounds, cfg, run):
    """One fixed-capacity recipe scenario, with complete duration-minimal cut witnesses."""
    tag = 'free' if bounds == (0, 1) else 'bounded'
    name = f"{sector}_{tag}_a{cfg['alpha']}_h{cfg['h']}_s{cfg['sigma']}_L{cfg['L']}"
    out = Path('results') / run / 'cuts' / f'{name}.json'
    if out.exists():
        return name, 'cached'
    run_stamp = stamp()
    N = build(sector=sector)
    M = model(N, bounds, h=cfg['h'], sigma=cfg['sigma'], L=cfg['L'])
    baseline = solve(M, [0]*len(M['V']))
    assert baseline['status'] == 'optimal' and baseline['phi'] <= EPS
    C = enumerate_lattice(M, DURATIONS, cfg['alpha'], K, EPS)
    cuts = sparse(C['cuts'])
    dense = [[dict(S).get(v, 0) for v in range(len(M['V']))] for S in cuts]
    cert = [certify(M, D, cfg['alpha']*M['total']) for D in dense]
    assert all(c['certified'] for c in cert)
    legacy_name = f"base_a{cfg['alpha']}_h{cfg['h']}_s{cfg['sigma']}_L{cfg['L']}"
    old = json.loads((Path('results') / f'{sector}-residual-2395a5c' / 'cuts' /
                      f'{legacy_name}.json').read_text())
    assert old['nodes'] == list(map(list, M['V']))
    key = lambda S: tuple(map(tuple, S))
    previous, current = set(map(key, old['cuts'])), set(map(key, cuts))
    comparison = {'vanish': sorted(previous-current), 'appear': sorted(current-previous)}
    if cfg == {'alpha': 0.25, 'h': 0, 'sigma': 0, 'L': 6}:
        restated = []
        for S in old['cuts']:
            if any(M['V'][v][1] in METALS for v, _ in S):
                D = [dict(S).get(v, 0) for v in range(len(M['V']))]
                R = solve(M, D)
                assert R['status'] == 'optimal' and R['gap'] <= 10*EPS
                restated.append({'losses': [[*M['V'][v], d] for v, d in S],
                                 'shortfall': R['phi']/M['total'],
                                 'still_minimal': key(S) in current,
                                 'fails': R['phi'] > cfg['alpha']*M['total'] + EPS})
        comparison['metals_restated'] = restated
    data = {'stamp': run_stamp, 'task': name, 'sector': sector, 'config': cfg,
            'chemistry': M['chemistry'], 'nodes': list(map(list, M['V'])),
            'total': M['total'], 'baseline': baseline, 'cuts': cuts, 'certificates': cert,
            'complete': True, 'method': 'lattice', 'lp_calls': C['lp_calls'],
            'legacy_comparison': comparison}
    out.write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8')
    return name, len(cuts), 'certified'


def main():
    run = sys.argv[1]
    d = Path('results') / run
    (d / 'cuts').mkdir(parents=True, exist_ok=True)
    T = [(sector, bounds, cfg, run) for sector in ('liion', 'joint')
         for bounds in ((0, 1), (0.25, 0.75)) for name, _, cfg, _ in tasks(sector)
         if name.startswith('base')]
    T.sort(key=lambda x: (x[2]['h'] != 0 or x[2]['sigma'] != 0, x[2]['alpha'] != 0.25))
    with ProcessPoolExecutor(int(sys.argv[2])) as pool:
        for f in as_completed([pool.submit(job, *t) for t in T]):
            print(*f.result(), flush=True)


if __name__ == '__main__':
    main()
