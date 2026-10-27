"""Capture fresh SciPy recourse certificates, then compare a native implementation."""
# N: physical network; M: recourse matrices; D: outage months; S: sparse duration cut.
# phi: cumulative shortfall; f: partial node capacity loss; t: elapsed seconds.
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess
import time

import scipy
from scipy.optimize._highspy import _core

from chokepoint.bom import bill
from chokepoint import chemistry, net
from chokepoint.recourse import solve
from run_risk import dense


def cases():
    networks = {}
    for run in ('liion-60eb399', 'pv-ba89465', 'joint-ba89465'):
        networks.update(json.loads((Path('results') / run / 'network.json').read_text()))
    for network in networks.values():
        network['recipe_bom'] = [bill(0), bill(1)]
    paths = [path for run in ('liion-60eb399', 'pv-ba89465', 'joint-ba89465')
             for path in sorted((Path('results') / run / 'cuts').glob('base*.json'))]
    paths += sorted(Path('results/chemistry-896581f/cuts').glob('*.json'))
    out = []
    for path in paths:
        row = json.loads(path.read_text())
        sector = row.get('sector') or row['network']['sector']
        config = row['config'].copy()
        if '_free_' in path.stem or '_bounded_' in path.stem:
            config.update(choice=True, shares=[0, 1] if '_free_' in path.stem else [0.25, 0.75])
        states = {tuple([0] * len(row['nodes']))}
        selected = row['cuts'] if config.get('h', 0) == 0 else row['cuts'][:1]
        for S in selected:
            D = dense(S, len(row['nodes']))
            states.add(tuple(D))
            for v, d in S:
                previous = max([0, *(x for x in (3, 6, 12) if x < d)])
                short = D.copy()
                short[v] = previous
                states.add(tuple(short))
        out.append({'key': path.as_posix(), 'network': networks[sector], 'config': config,
                    'states': [list(D) for D in sorted(states)]})
    # Full-node probes exercise capacity indexing, partial losses and block/ramp boundaries.
    for sector, N in networks.items():
        n = len(N['nodes'])
        states = [[0] * n]
        for v in range(n):
            for d in (3, 6, 12):
                D = [0] * n
                D[v] = d
                states.append(D)
        out.append({'key': 'probes:' + sector, 'network': N,
                    'config': {'h': 0, 'sigma': 0, 'L': 6}, 'states': states})
        out.append({'key': 'partial:' + sector, 'network': N,
                    'config': {'h': 1, 'sigma': 0.1, 'L': 6, 'f': [0.4] * n},
                    'states': [[12] * n, [0] * n]})
    return out


def oracle(case):
    cfg = case['config'].copy()
    cfg.pop('alpha', None)
    choice = cfg.pop('choice', False)
    f = cfg.pop('f', None)
    build = chemistry.model if choice else net.model
    M = build(case['network'], **cfg)
    return {'key': case['key'], 'ends': M['ends'].tolist(), 'total': M['total'],
            'shape': [M['A'].shape[0], M['E'].shape[0], len(M['c'])],
            'states': [dict(D=D, **solve(M, D, f=f)) for D in case['states']]}


def compare(old, new, tolerance):
    a, b = ({row['key']: row for row in rows} for rows in (old, new))
    if len(a) != len(old) or len(b) != len(new):
        raise ValueError('Duplicate configuration keys')
    diff = {'only_python': sorted(a.keys() - b.keys()),
            'only_rust': sorted(b.keys() - a.keys()), 'structural': [], 'numeric': []}
    exact, numeric, maximum = 0, 0, 0.0
    for key in sorted(a.keys() & b.keys()):
        for name in ('ends', 'shape'):
            if a[key][name] != b[key][name]:
                diff['structural'].append({'key': key, 'column': name})
        ar = {tuple(row['D']): row for row in a[key]['states']}
        br = {tuple(row['D']): row for row in b[key]['states']}
        if len(ar) != len(a[key]['states']) or len(br) != len(b[key]['states']):
            raise ValueError('Duplicate state keys')
        for D in sorted(ar.keys() | br.keys()):
            if D not in ar or D not in br:
                diff['structural'].append({'key': key, 'D': D, 'column': 'missing state'})
                continue
            if ar[D]['status'] != br[D]['status']:
                diff['structural'].append({'key': key, 'D': D, 'column': 'status',
                                           'python': ar[D]['status'], 'rust': br[D]['status']})
            for name in ('phi', 'dual', 'gap', 'residual'):
                x, y = ar[D].get(name), br[D].get(name)
                if x is None or y is None:
                    if x != y:
                        diff['structural'].append({'key': key, 'D': D, 'column': name})
                    continue
                delta = abs(x - y)
                maximum = max(maximum, delta)
                if struct.pack('d', x) == struct.pack('d', y):
                    exact += 1
                else:
                    numeric += 1
                    diff['numeric'].append({'key': key, 'D': D, 'column': name,
                                            'python': x, 'rust': y, 'absolute_difference': delta,
                                            'exceeds_tolerance': delta > tolerance})
            match = re.search(r'_a([0-9.]+)_', key)
            alpha = float(match[1]) if match else 0.25
            if ((ar[D].get('phi', 0) > alpha * a[key]['total'] + 1e-7)
                    != (br[D].get('phi', 0) > alpha * b[key]['total'] + 1e-7)):
                diff['structural'].append({'key': key, 'D': D,
                                           'column': f'{alpha:g} classification'})
    return {'diff': diff, 'exact_numeric_fields': exact, 'different_numeric_fields': numeric,
            'max_absolute_difference': maximum, 'tolerance': tolerance,
            'within_tolerance': not any(diff[k] for k in ('only_python', 'only_rust', 'structural'))
            and not any(row['exceeds_tolerance'] for row in diff['numeric'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--binary')
    parser.add_argument('--seconds', type=float, default=600)
    parser.add_argument('--compare', action='store_true')
    parser.add_argument('--skip-python-timing', action='store_true')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if not args.compare:
        rows, inputs = [], []
        start = time.perf_counter()
        all_cases = cases()
        for case in all_cases:
            rows.append(oracle(case))
            inputs.append(case)
            elapsed = time.perf_counter() - start
            print(case['key'], len(case['states']), f'{elapsed:.3f}s', flush=True)
            (args.out / 'python.json').write_text(json.dumps(rows) + '\n')
            (args.out / 'inputs.json').write_text(json.dumps(inputs) + '\n')
            if elapsed > args.seconds:
                break
        metadata = {'scipy': scipy.__version__, 'highs': '.'.join(str(x) for x in (
            _core.HIGHS_VERSION_MAJOR, _core.HIGHS_VERSION_MINOR, _core.HIGHS_VERSION_PATCH)),
                    'seconds': time.perf_counter() - start, 'cases': len(rows),
                    'states': sum(len(x['states']) for x in rows),
                    'available_cases': len(all_cases)}
        (args.out / 'baseline.json').write_text(json.dumps(metadata, indent=1) + '\n')
        print(metadata, flush=True)
        return
    old = json.loads((args.out / 'python.json').read_text())
    inputs = json.loads((args.out / 'inputs.json').read_text())
    # A planted wrong numeric value and a missing state must both be detected.
    planted = [{'key': 'test', 'ends': [1], 'shape': [1, 0, 1], 'total': 1,
                'states': [{'D': [1], 'status': 'optimal', 'phi': 0.5}]}]
    bad = json.loads(json.dumps(planted))
    bad[0]['states'][0]['phi'] = 0.8
    assert not compare(planted, bad, 1e-7)['within_tolerance']
    bad[0]['states'] = []
    assert not compare(planted, bad, 1e-7)['within_tolerance']
    payload = ''.join(json.dumps(case) + '\n' for case in inputs)
    start = time.perf_counter()
    run = subprocess.run([args.binary], input=payload, text=True, capture_output=True, check=True)
    elapsed = time.perf_counter() - start
    new = [json.loads(line) for line in run.stdout.splitlines()]
    (args.out / 'rust.json').write_text(json.dumps(new) + '\n')
    report = compare(old, new, 1e-7)
    # Time exactly the same inputs without the baseline's repeated artifact checkpoints.
    python_seconds = None
    if not args.skip_python_timing:
        start = time.perf_counter()
        fresh_python = [oracle(case) for case in inputs]
        python_seconds = time.perf_counter() - start
        repeated = compare(old, fresh_python, 1e-7)
        if not repeated['within_tolerance']:
            raise RuntimeError('Python oracle changed between baseline and timed run')
    report.update(rust_seconds=elapsed, known_bad_rejected=True,
                  identical=report['within_tolerance'] and report['different_numeric_fields'] == 0,
                  python_seconds=python_seconds,
                  timing_scope='same input cases, build plus cold primal/dual solve per state; '
                               'Rust includes JSON process overhead; one pass each',
                  cases=len(new), states=sum(len(row['states']) for row in new))
    (args.out / 'parity.json').write_text(json.dumps(report, indent=1) + '\n')
    print({k: v for k, v in report.items() if k != 'diff'}, flush=True)
    if not report['within_tolerance']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
