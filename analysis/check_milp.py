"""Repeat the seven unfinished MILP certificates: python analysis/check_milp.py RUN WORKERS."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chokepoint.cuts import enumerate_cuts
from chokepoint.fetch import stamp
from chokepoint.net import build, model


def job(sector, name, leg, run):
    """Compare a longer, unseeded MILP run with its immutable lattice reference."""
    out = Path('results') / run / f'{sector}_{name}_{leg}.json'
    if out.exists():
        return out.name, 'cached'
    run_stamp = stamp()
    source = f'{sector}-residual-2395a5c'
    R = json.loads((Path('results') / source / 'cuts' / f'{name}.json').read_text())
    cfg = R['config']
    N = build(**R['network'])
    M = model(N, h=cfg['h'], sigma=cfg['sigma'], L=cfg['L'], durations=(3, 6, 12))
    eligible = R['pruned']['eligible'] if leg == 'pruned' else None
    expected = R['pruned']['lattice'] if leg == 'pruned' else R['cuts']
    if leg == 'pruned':
        assert R['pruned']['brute_equals_lattice']
    limit = 2700 if leg == 'pruned' else 10800
    C = enumerate_cuts(M, (3, 6, 12), cfg['alpha'], time_limit=limit, eligible=eligible)
    actual = sorted([[v, d] for v, d in enumerate(c['D']) if d] for c in C['cuts'])
    data = {'stamp': run_stamp, 'source': source, 'task': name, 'leg': leg,
            'time_limit': limit, 'method': 'unseeded_MILP', 'result': C,
            'equals_lattice': actual == expected, 'expected_cuts': len(expected)}
    assert not C['complete'] or actual == expected
    out.write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8')
    return out.name, C['status'], C['seconds']


def main():
    run = sys.argv[1]
    (Path('results') / run).mkdir(parents=True, exist_ok=True)
    T = [('liion', 'base_a0.1_h0_s0_L6', 'milp_full'),
         ('joint', 'base_a0.25_h0_s0_L6', 'pruned'),
         *[('liion', f'base_a0.1_h{h}_s{s}_L24', 'pruned')
           for h in (1, 3) for s in (0.1, 0.5)],
         ('liion', 'base_a0.25_h1_s0.5_L24', 'pruned')]
    with ProcessPoolExecutor(int(sys.argv[2])) as pool:
        for f in as_completed([pool.submit(job, *t, run) for t in T]):
            print(*f.result(), flush=True)


if __name__ == '__main__':
    main()
