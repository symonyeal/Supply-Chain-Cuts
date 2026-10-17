"""Recompute recovered cut witnesses: python analysis/check_witnesses.py RUN OUT."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.build_site import certificates
from chokepoint.fetch import stamp
from chokepoint.net import build, model
from chokepoint.recourse import solve


def check(run, out):
    """Check every recovered cut shortfall and predecessor directly against recourse."""
    start_stamp = stamp()
    rows = []
    for path in sorted((Path('results') / run / 'cuts').glob('*.json')):
        R = json.loads(path.read_text(encoding='utf-8'))
        kw = R['network'].copy()
        if 'exclude' in kw:
            kw['exclude'] = list(map(tuple, kw['exclude']))
        N = build(**kw)
        cfg = R['config']
        M = model(N, h=cfg['h'], sigma=cfg['sigma'], L=cfg['L'], durations=(3, 6, 12))
        C = certificates(R)
        err = 0
        for S in R['cuts']:
            c = C[json.dumps(S)]
            D = [dict(S).get(v, 0) for v in range(len(M['V']))]
            phi = solve(M, D, dual=False)
            assert phi['status'] == 'optimal' and phi['phi'] > R['theta'] + 1e-7
            err = max(err, abs(phi['phi'] - c['phi']))
            for p in c['predecessors']:
                E = D.copy()
                E[p['v']] = p['D']
                z = solve(M, E, dual=False)
                assert z['status'] == 'optimal' and z['phi'] <= R['theta'] + 1e-7
                err = max(err, abs(z['phi'] - p['phi']))
        assert err <= 1e-7
        rows.append({'task': R['task'], 'cuts': len(R['cuts']), 'max_error': err})
    result = {'stamp': start_stamp, 'source': run, 'checks': rows,
              'all_recovered_witnesses_match_LP': True}
    d = Path('results') / out
    d.mkdir(parents=True, exist_ok=True)
    (d / f'{run}.json').write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8')
    print(run, sum(x['cuts'] for x in rows), 'cuts checked', flush=True)


if __name__ == '__main__':
    check(*sys.argv[1:])
