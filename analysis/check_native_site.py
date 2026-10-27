"""Compare every delivered explorer payload leaf against the native Rust builder."""
# p: JSON pointer; a/b: original/native leaf maps; runs: immutable result bundle names.
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.build_site import ROOT, build, plain

RUNS = ['liion-residual-2395a5c', 'pv-residual-2395a5c',
        'joint-residual-2395a5c', 'severity-26ebd48']


def leaves(value, path=''):
    """Preserve array positions, empty containers, scalar types and float bits."""
    if isinstance(value, dict):
        result = {path: ('object',)}
        for key, item in value.items():
            token = str(key).replace('~', '~0').replace('/', '~1')
            result.update(leaves(item, path + '/' + token))
        return result
    if isinstance(value, list):
        result = {path: ('array',)}
        for index, item in enumerate(value):
            result.update(leaves(item, path + '/' + str(index)))
        return result
    if isinstance(value, bool):
        return {path: ('boolean', value)}
    if isinstance(value, (int, float)):
        # JSON numbers are semantically one type; compare their binary64 values exactly.
        if isinstance(value, int) and abs(value) > 2**53:
            return {path: ('integer', value)}
        return {path: ('number', struct.pack('>d', float(value)).hex())}
    return {path: (type(value).__name__, value)}


def differences(old, new):
    a, b = leaves(old), leaves(new)
    if not isinstance(old, dict) or not isinstance(new, dict) or not old or not new:
        raise ValueError('Expected nonempty payload objects')
    return {'only_python': sorted(a.keys() - b.keys()),
            'only_rust': sorted(b.keys() - a.keys()),
            'different': [{'path': key, 'python': a[key], 'rust': b[key]}
                          for key in sorted(a.keys() & b.keys()) if a[key] != b[key]]}


def controls():
    assert differences({'a': 0.5}, {'a': 0.6})['different']
    assert differences({'a': 1}, {'b': 1}) == {
        'only_python': ['/a'], 'only_rust': ['/b'], 'different': []}
    assert differences({'a': [1, 2]}, {'a': [2, 1]})['different']
    assert differences({'a': []}, {'a': {}})['different']
    assert differences({'a': [1]}, {'a': {'0': 1}})['different']
    assert differences({'a': False}, {'a': 0})['different']


def native(binary, root=ROOT, runs=RUNS, full=False):
    args = [str(binary), *(['--full'] if full else []), str(root), *runs]
    process = subprocess.run(args, check=True,
                             text=True, encoding='utf-8', capture_output=True)
    return json.loads(process.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--runs', nargs='+', default=RUNS)
    args = parser.parse_args()
    controls()
    args.out.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    old_full = build(*args.runs)
    old = plain(old_full)
    python_seconds = time.perf_counter() - start
    start = time.perf_counter()
    new_full = native(args.binary, runs=args.runs, full=True)
    rust_seconds = time.perf_counter() - start
    new = native(args.binary, runs=args.runs)
    committed = json.loads((ROOT / 'site/data.js').read_text(encoding='utf-8')
                           .removeprefix('window.DATA = ').strip().removesuffix(';'))
    diff = differences(old, new)
    full_diff = differences(old_full, new_full)
    saved = differences(committed, new) if args.runs == RUNS else None
    report = {'identical': not any(diff.values()) and not any(full_diff.values()),
              'runs': args.runs,
              'python_compared_nodes': len(leaves(old)),
              'rust_compared_nodes': len(leaves(new)),
              'known_bad_rejected': True, 'diff': diff, 'full_precision_diff': full_diff,
              'committed_diff': saved,
              'python_seconds': python_seconds, 'rust_seconds': rust_seconds,
              'timing_scope': 'complete full-precision payload; Rust includes process/JSON',
              'scope': 'all configurations, cut witnesses, country unions and study exhibits'}
    for name, value in [('python', old), ('rust', new), ('python-full', old_full),
                        ('rust-full', new_full), ('parity', report)]:
        (args.out / (name + '.json')).write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=1) + '\n',
            encoding='utf-8')
    print(json.dumps(report, indent=1))
    if any(diff.values()) or any(full_diff.values()) or (
            saved is not None and any(saved.values())):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
