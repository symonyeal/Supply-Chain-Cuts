"""Recompute located throughput coverage: python -m analysis.check_sites RUN.

The frozen candidate tables have no coordinate/capacity matches. Administrative
division names are not plant coordinates. No centroid is treated as an observed site.
"""
import csv
import json
import sys
from pathlib import Path

from chokepoint.fetch import stamp
from chokepoint.net import build


def main():
    run_stamp = stamp()
    path = Path('data/sites/coverage.json')
    old = json.loads(path.read_text())
    with Path('data/sites/site_candidates.csv').open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    sites = json.loads(Path('data/sites/sites.json').read_text())['sites']
    assert not sites and not any(x['latitude'] or x['longitude'] for x in rows)
    N = build(sector='joint')
    layers = []
    for p in sorted(N['requirement']):
        V = [x for x in N['nodes'] if x['product'] == p]
        candidates = [x for x in rows if x['product'] == p
                      or p == 'graphite' and x['product'] == 'mine_graphite']
        q = sum(x['annual'] for x in V)
        assert q > 0 and len({x['unit'] for x in V}) == 1
        layers.append({'product': p, 'candidate_records': len(candidates),
                       'records_with_capacity': sum(bool(x['capacity']) for x in candidates),
                       'located_capacity_records': 0, 'verified_located_capacity': 0,
                       'total_layer_capacity': q, 'unit': V[0]['unit'],
                       'denominator_basis': 'retained model annual output, not plant nameplate',
                       'verified_located_capacity_share': 0.0,
                       'coverage_status': 'no_verified_geocoded_capacity'})
    out = {**old, 'stamp': run_stamp, 'layers': layers, 'network_sector': 'joint',
           'matching_performed': False, 'coverage_test_passed': False,
           'terminal_reason': 'No verified coordinate-capacity pairs in frozen candidates; '
                              'no midstream/cell site table. All model-layer numerators zero; '
                              '70% threshold fails. Admin-1 exposure matching not measured.'}
    d = Path('results') / sys.argv[1]
    d.mkdir(parents=True, exist_ok=True)
    (d / 'site_coverage.json').write_text(json.dumps(out, indent=1)+'\n', encoding='utf-8')
    path.write_text(json.dumps(out, indent=1)+'\n', encoding='utf-8')
    print(len(layers), 'model layers; located numerator 0 in each; threshold fails')


if __name__ == '__main__':
    main()
