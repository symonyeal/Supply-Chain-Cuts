"""Fixed-demand USGS metal-output sensitivity; baseline and 12-month single outages.

N is the reference network; rows are 2023 nickel-content tonnes from USGS T12.
Only retained refined_ni nodes change. No complete cut list or probability is computed.
"""
import argparse
import csv
import json
import math
from copy import deepcopy
from pathlib import Path

from chokepoint.chemistry import model as choice
from chokepoint.fetch import sha256, stamp
from chokepoint.net import build, model
from chokepoint.recourse import solve

RAW = Path('data/raw/usgs')
BOOK = 'myb1-2023-nicke-ERT.xlsx'
ROWS = 'myb2023_nickel_metal.csv'
EPS = 1e-7


def replace_metal(N, rows):
    """Replace retained refined_ni output at the reference demand and normalisation."""
    observations = {}
    for r in rows:
        if r['form'] != 'metal':
            raise ValueError('Only metal observations may replace refined_ni')
        c = r['iso3']
        if c in observations:
            raise ValueError(f'duplicate country observation: {c}')
        q = float(r['value']) / 1000  # tonnes nickel content -> kt; net capacities use kt
        if not math.isfinite(q) or q <= 0:
            raise ValueError('Finite positive metal output required')
        observations[c] = r, q
    P, used = deepcopy(N), []
    for x in P['nodes']:
        if x['product'] != 'refined_ni' or x['country'] not in observations:
            continue
        r, q = observations[x['country']]
        old = x['annual']
        if not math.isfinite(old) or old <= 0:
            raise ValueError('Finite positive reference annual output required')
        used.append(dict(r) | {'old_annual_kt': old, 'new_annual_kt': q,
                               'old_basis': x.get('basis', 'unverified')})
        x.update(annual=q, capacity=x['capacity'] * q / old, basis='production',
                 source=f"USGS MYB {r['year']} {r['cell']}",
                 note=f"{r['year']} metal output, {r['qualifier']}; "
                      'not battery-grade or installed capacity')
    return P, used


def read_metal(root=Path('.')):
    """Read the frozen observations and check each against its workbook coordinate."""
    import openpyxl

    root = Path(root)
    sources = json.loads((root / 'SOURCES.lock').read_text(encoding='utf-8'))['sources']
    for f in (BOOK, ROWS):
        source = next(x for x in sources if x['path'] == (RAW / f).as_posix())
        if sha256(root / RAW / f) != source['sha256']:
            raise ValueError(f'Frozen nickel source hash mismatch: {f}')
    with (root / RAW / ROWS).open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    w = openpyxl.load_workbook(root / RAW / BOOK, data_only=True, read_only=True)
    try:
        s = w['T12']
        if s['A4'].value != '(Metric tons, nickel content)' or str(s['K6'].value) != '2023':
            raise ValueError('USGS nickel units or reference year changed')
        for r in rows:
            sheet, cell = r['cell'].split('!')
            if sheet != 'T12' or cell[0] != 'K' or r['year'] != '2023':
                raise ValueError('Expected a 2023 T12 column-K metal observation')
            i = int(cell[1:])
            flag = s[f'L{i}'].value
            qualifier = 'estimated' if flag == 'e' else 'reported' if flag is None else flag
            if (float(s[cell].value) != float(r['value'])
                    or qualifier != r['qualifier'] or s[f'A{i}'].value != r['source_label']):
                raise ValueError(f"Observation differs from workbook: {r['iso3']} {r['cell']}")
    finally:
        w.close()
    replace_metal({'nodes': []}, rows)  # validate forms, numeric values and unique countries
    return rows


def singletons(N, flexible, root=Path('.')):
    """Solve the baseline and every single-node 12-month outage with bounded-dual checks."""
    kw = {'T': 24, 'h': 0, 'sigma': 0, 'L': 6, 'durations': (12,)}
    M = choice(N, root=root, **kw) if flexible else model(N, **kw)

    def one(D):
        r = solve(M, D)
        if r['status'] != 'optimal':
            raise RuntimeError(f"Recourse status {r['status']}: {r['message']}")
        if r['gap'] > 10 * EPS or r['residual'] > 10 * EPS:
            raise RuntimeError('Recourse certificate exceeds tolerance')
        return r | {'share': r['phi'] / M['total'],
                    'fails': r['phi'] > .25 * M['total'] + EPS}

    baseline = one([0] * len(M['V']))
    outages = []
    for v, (country, product) in enumerate(M['V']):
        D = [0] * len(M['V'])
        D[v] = 12
        outages.append({'country': country, 'product': product, **one(D)})
    return {'total': M['total'], 'baseline': baseline, 'outages': outages}


def study(root=Path('.')):
    """Compare the two source bases at fixed demand under fixed and flexible chemistry."""
    root = Path(root)
    provenance = stamp(root)
    rows = read_metal(root)
    N = build(root=root)
    P, used = replace_metal(N, rows)
    assert N['requirement'] == P['requirement'] and N['demand_scale'] == P['demand_scale']
    assert [(x['country'], x['product']) for x in N['nodes']] == [
        (x['country'], x['product']) for x in P['nodes']]
    assert all(a == b for a, b in zip(N['nodes'], P['nodes'], strict=True)
               if a['product'] != 'refined_ni')
    cases = {}
    for flexible in (False, True):
        a, b = singletons(N, flexible, root), singletons(P, flexible, root)
        changed = [{'country': x['country'], 'product': x['product'],
                    'reference_share': x['share'], 'metal_share': y['share'],
                    'reference_fails': x['fails'], 'metal_fails': y['fails']}
                   for x, y in zip(a['outages'], b['outages'], strict=True)
                   if x['fails'] != y['fails']]
        cases['flexible' if flexible else 'fixed'] = {
            'reference': a, 'metal': b, 'changed_singletons': changed}
    return {'stamp': provenance, 'parameters': {'T': 24, 'h': 0, 'sigma': 0, 'L': 6,
                                               'duration': 12, 'alpha': .25, 'eps': EPS},
            'scope': 'baseline and individual outages only; not a complete cut list or probability',
            'source_year': 2023, 'reference_network_year': 2024,
            'source_hashes': {f: sha256(root / RAW / f) for f in (BOOK, ROWS)},
            'source_observations': rows, 'used': used,
            'unmatched': [r for r in rows if r['iso3'] not in {x['iso3'] for x in used}],
            'reference_demand': N['requirement'], 'reference_demand_scale': N['demand_scale'],
            'reference_nodes': N['nodes'], 'metal_nodes': P['nodes'],
            'share_scope': 'node.share remains the reference pre-screen share, not recomputed',
            'cases': cases}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True, help='JSON result path')
    a = p.parse_args(argv)
    r = study()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(r, indent=1) + '\n', encoding='utf-8')
    for name, c in r['cases'].items():
        print(name, 'baseline shares', c['reference']['baseline']['share'],
              c['metal']['baseline']['share'], 'changed singletons', len(c['changed_singletons']))


if __name__ == '__main__':
    main()
