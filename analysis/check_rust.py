"""Measure exact cut-union parity and batch time against the Python oracle."""
# V: nodes; p: onset probabilities; rho: country-shock share; D: outage months.
# w: conditional duration weights; L: cut-union probability; S: sparse cut.
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import time

from chokepoint.risk import exact_union
from chokepoint.rust import batch
from run_risk import dense, truncate


def bits(value):
    return struct.pack('>d', value).hex()


def differences(old, new):
    """Compare the complete keyed row sets, retaining the delivered float bits."""
    a = {row['key']: row for row in old}
    b = {row['key']: row for row in new}
    if len(a) != len(old) or len(b) != len(new):
        raise ValueError('Duplicate comparison keys')
    return {'only_python': sorted(a.keys() - b.keys()),
            'only_rust': sorted(b.keys() - a.keys()),
            'different': [{'key': key, 'python_bits': bits(a[key]['L']),
                           'rust_bits': bits(b[key]['L']),
                           'difference': b[key]['L'] - a[key]['L']}
                          for key in sorted(a.keys() & b.keys())
                          if bits(a[key]['L']) != bits(b[key]['L'])]}


def configurations():
    paths = [Path('results') / run / 'risk.json' for run in (
        'liion-60eb399', 'pv-ba89465', 'joint-ba89465')]
    paths.extend(sorted(Path('results/chemistry-risk-d18c743').glob('*.json')))
    out = []
    for path in paths:
        result = json.loads(path.read_text(encoding='utf-8'))
        law = result if 'rates' in result else json.loads((
            Path('results') / result['reference_bundle'] / 'risk.json').read_text())
        V = law['nodes']
        for key, cfg in result['configs'].items():
            DJ = int(key.rsplit('_D', 1)[1])
            D, w = truncate(law['durations']['weights'], DJ)
            if 'cuts' in cfg:
                cuts = cfg['cuts']
            else:
                source = Path('results') / result['cut_bundle'] / 'cuts' / (
                    result['sector'] + '_free_' + key.rsplit('_D', 1)[0] + '.json')
                cuts = [S for S in json.loads(source.read_text())['cuts']
                        if all(d <= DJ for _, d in S)]
            out.append({'key': path.as_posix() + ':' + key, 'saved': cfg['L'],
                        'input': {'V': V, 'p': law['rates']['p'], 'rho': law['rates']['rho'],
                                  'durations': D, 'weights': w,
                                  'cuts': [dense(S, len(V)) for S in cuts]}})
    return out


def edges():
    base = {'V': [['B', 'x'], ['A', 'x'], ['B', 'y']], 'p': [0.2, 0.4, 0.7],
            'rho': 0.5, 'durations': [3, 6, 12], 'weights': [0.2, 0.3, 0.5],
            'cuts': [[3, 0, 6], [0, 12, 0]]}
    variants = {'empty_cuts': {'cuts': []}, 'empty_cut': {'cuts': [[0, 0, 0]]},
                'zero_probabilities': {'p': [0, 0, 0]},
                'one_probabilities': {'p': [1, 1, 1]},
                'rho_zero': {'rho': 0}, 'rho_one': {'rho': 1},
                'one_probabilities_rho_one': {'p': [1, 1, 1], 'rho': 1},
                'mixed_probabilities_rho_one': {'p': [0, 1, 0.7], 'rho': 1},
                'duplicate_durations': {'durations': [3, 3, 12]},
                'zero_duration': {'durations': [0, 3, 12]},
                'zero_weights': {'weights': [0, 0, 1]},
                'duplicate_cuts': {'cuts': base['cuts'] * 2},
                'redundant_cuts': {'cuts': base['cuts'] + [[6, 0, 12]]},
                'no_nodes_no_cuts': {'V': [], 'p': [], 'cuts': []},
                'no_nodes_empty_cut': {'V': [], 'p': [], 'cuts': [[]]}}
    return [{'key': 'edge:' + name, 'input': base | changes}
            for name, changes in variants.items()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cases = configurations() + edges()
    # Validate the comparator before using it on the actual output.
    known_bad = differences([{'key': 'test', 'L': 0.5}], [{'key': 'test', 'L': 0.6}])
    assert len(known_bad['different']) == 1
    assert differences([{'key': 'a', 'L': 0.5}], [{'key': 'b', 'L': 0.5}]) == {
        'only_python': ['a'], 'only_rust': ['b'], 'different': []}
    old = []
    start = time.perf_counter()
    for case in cases:
        value = exact_union(**case['input'])
        old.append({'key': case['key'], 'L': value, 'bits': bits(value)})
    python_seconds = time.perf_counter() - start
    (args.out / 'rust-oracle.json').write_text(json.dumps(old, indent=1) + '\n')
    start = time.perf_counter()
    responses = batch([case['input'] for case in cases], binary=args.binary)
    rust_seconds = time.perf_counter() - start
    new = [{'key': case['key'], **response} for case, response in zip(cases, responses,
                                                                   strict=True)]
    diff = differences(old, new)
    saved_diff = [{'key': case['key'], 'saved': case['saved'], 'fresh': row['L']}
                  for case, row in zip(cases, old, strict=True)
                  if 'saved' in case and bits(case['saved']) != bits(row['L'])]
    report = {'identical': not any(diff.values()), 'python_rows': len(old),
              'rust_rows': len(new), 'range': dict(Counter(
                  case['key'].split(':')[0] for case in cases)),
              'known_bad_rejected': True, 'diff': diff, 'saved_diff': saved_diff,
              'python_seconds': python_seconds, 'rust_batch_seconds': rust_seconds,
              'batch_speedup': python_seconds / rust_seconds,
              'timing_scope': 'one complete batch; Rust includes process and JSON overhead',
              'not_tested': 'recourse LP, Monte Carlo and data fitting are not ported'}
    (args.out / 'rust-output.json').write_text(json.dumps(new, indent=1) + '\n')
    (args.out / 'rust-parity.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report, indent=1), flush=True)
    if not report['identical'] or saved_diff:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
