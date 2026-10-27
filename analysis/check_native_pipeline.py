"""Compare native sampling, brackets, interval inversion, cut lists and site rebuild."""
# R: repository root; W: persistent evidence; D: outage state; C: minimal cut list.
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R))
from analysis.check_rust import configurations, edges
from analysis.check_native_site import differences
from chokepoint.brute import enumerate_lattice
from chokepoint.bom import bill
from chokepoint.chemistry import model as choice_model
from chokepoint.net import build, model
from chokepoint.risk import _parameters, binomial_interval, bracket


def run(binary, args, *, text=None):
    result = subprocess.run([str(binary), *map(str, args)], input=text, text=True,
                            encoding='utf8', capture_output=True, check=True)
    return json.loads(result.stdout)


def check(binary, out, full_cuts, resume=False):
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    cases = configurations() + edges()
    old = [bracket(**case['input'], complete=True) for case in cases]
    (out / 'python-brackets.json').write_text(json.dumps(old), encoding='utf8')
    text = ''.join(json.dumps({**case['input'], 'operation': 'bracket'}) + '\n' for case in cases)
    process = subprocess.run([str(binary), 'probability'], input=text, text=True,
                             encoding='utf8', capture_output=True, check=True)
    new = [json.loads(line) for line in process.stdout.splitlines()]
    assert len(new) == len(old) == 432
    max_error = 0
    for a, b in zip(old, new, strict=True):
        assert a['L'] == b['L']
        assert a['attribution'] == b['attribution']
        for key in ('U', 'tail'):
            error = abs(a[key] - b[key])
            assert error <= 2e-14, (a, b)
            max_error = max(max_error, error)
    report['brackets'] = {'cases': len(old), 'L_and_attribution_exact': True,
                          'max_tail_or_U_error': max_error}
    (out / 'rust-brackets.json').write_text(json.dumps(new), encoding='utf8')
    pairs = [[m, n] for n in (2, 10, 100, 20000) for m in sorted({0, 1, n//2, n-1, n})]
    expected = [binomial_interval(m, n) for m, n in pairs]
    actual = run(binary, ['interval'], text=json.dumps(pairs))
    error = float(np.max(np.abs(np.array(expected)-actual)))
    assert error < 2e-11, (expected, actual, error)
    report['binomial_intervals'] = {'cases': len(pairs), 'max_absolute_error': error}
    draws = []
    for sector, bundle in (('liion', 'liion-residual-2395a5c'),
                           ('pv', 'pv-residual-2395a5c'), ('joint', 'joint-residual-2395a5c')):
        path = R / 'results' / bundle / 'risk.json'
        law = json.loads(path.read_text(encoding='utf8'))
        for seed in (0, 4, 8, 2**40+7):
            n = 64
            V, p, rho = law['nodes'], law['rates']['p'], law['rates']['rho']
            ds, weights = law['durations']['durations'], law['durations']['weights']
            _, w, groups, s, q = _parameters(V, p, rho, ds, weights)
            rng = np.random.default_rng(seed)
            H = rng.random((n, len(s))) < s
            onset = rng.random((n, len(q))) < q
            for j, I in enumerate(groups):
                onset[:, I] |= H[:, j, None]
            expected = rng.choice(ds, size=onset.shape, p=w)*onset
            config = out / 'sample-config.json'
            config.write_text(json.dumps({'sector': sector, 'n': n, 'seed': seed}), encoding='utf8')
            actual = run(binary, ['sample-law', '--law', path, '--config', config])
            assert np.array_equal(expected, actual)
            draws.append({'sector': sector, 'seed': seed, 'states': n,
                          'categorical_values': int(expected.size)})
    report['sample_streams'] = draws
    cut_cases = [
        ('pv', False, {}), ('liion', True, {}), ('liion', False, {}),
        ('joint', True, {}), ('pv', False, {'h': 1, 'sigma': .1, 'k': 2}),
    ] if full_cuts else [('pv', False, {})]
    cut_report = []
    for i, (sector, choice, recourse) in enumerate(cut_cases):
        N = build(sector=sector)
        cfg = {'sector': sector, 'choice': choice, 'alpha': .25, 'k': 3,
               'time_limit': 180, **recourse}
        options = {key: cfg[key] for key in ('h', 'sigma', 'L') if key in cfg}
        M = choice_model(N, **options) if choice else model(N, **options)
        net_path, cfg_path = out / f'network-{i}.json', out / f'config-{i}.json'
        if choice:
            N['recipe_bom'] = [bill(0), bill(1)]
        baseline = out / f'cuts-python-{i}.json'
        reuse = resume and baseline.exists() and net_path.exists() and cfg_path.exists()
        if reuse:
            previous = json.loads(cfg_path.read_text(encoding='utf8'))
            assert {k: v for k, v in previous.items() if k != 'time_limit'} == {
                k: v for k, v in cfg.items() if k != 'time_limit'}
            assert json.loads(net_path.read_text(encoding='utf8')) == N
            old = json.loads(baseline.read_text(encoding='utf8'))
            python_seconds = None
        else:
            start = time.perf_counter()
            old = enumerate_lattice(M, (3, 6, 12), alpha=cfg['alpha'], k=cfg['k'])
            python_seconds = time.perf_counter()-start
            baseline.write_text(json.dumps(old), encoding='utf8')
        net_path.write_text(json.dumps(N), encoding='utf8')
        cfg_path.write_text(json.dumps(cfg), encoding='utf8')
        start = time.perf_counter()
        new = run(binary, ['cuts', '--network', net_path, '--config', cfg_path])
        native_seconds = time.perf_counter()-start
        (out / f'cuts-native-{i}.json').write_text(json.dumps(new), encoding='utf8')
        assert new['complete'] and new['status'] == 'optimal', {
            k: new.get(k) for k in ('status', 'complete', 'seconds', 'lp_calls')}
        a, b = {tuple(d) for d in old['cuts']}, {tuple(d) for d in new['cuts']}
        assert a == b and len(a) == len(old['cuts']) == len(new['cuts'])
        assert all(c['gap'] <= 1e-6 for c in new['certificates'])
        cut_report.append({'sector': sector, 'choice': choice, 'config': cfg,
                           'cuts': len(a), 'two_way_difference': [],
                           'python_seconds': python_seconds, 'rust_seconds': native_seconds,
                           'reused_oracle_after_network_and_config_check': reuse})
    report['cuts'] = cut_report
    destination = out / 'built'
    report['build'] = run(binary, ['build', '--out', destination])
    for name, assignment in (('data.js', 'window.DATA = '), ('context.js', 'window.CONTEXT=')):
        expected = json.loads((R/'site'/name).read_text(encoding='utf8').removeprefix(
            assignment).strip().removesuffix(';'))
        actual = json.loads((destination/name).read_text(encoding='utf8').removeprefix(
            assignment).strip().removesuffix(';'))
        diff = differences(expected, actual)
        assert not any(diff.values()), diff
    assert (destination/'context.csv').read_bytes() == (R/'site/context.csv').read_bytes()
    report['passed'] = True
    (out/'pipeline.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--full-cuts', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    check(args.binary, args.out, args.full_cuts, args.resume)
