"""W5 fixed-demand capacity sensitivities: python run_supply.py RUN.

Japan supplements change the measured output roster and its reference demand.
Competing-demand reservations instead keep the original demand exactly fixed.
No probabilities are computed; HYPOTHESES N1/N2 govern the reservation cases.
"""
import json
import sys
from copy import deepcopy
from pathlib import Path

from chokepoint.brute import enumerate_lattice
from chokepoint.chemistry import model as choice
from chokepoint.fetch import stamp
from chokepoint.net import build, model
from chokepoint.recourse import solve
from run_cuts import DURATIONS, EPS, K, certify, sparse


def reserve(N, eta):
    """u[v] <- eta[p(v)] u[v]; keep requirements and final demand fixed (MODEL, W5)."""
    N = deepcopy(N)
    for x in N['nodes']:
        f = eta.get(x['product'], 1)
        x['annual'] *= f
        x['capacity'] *= f
    for p, f in eta.items():
        N['supply_ratio'][p] *= f
        N['annual_totals'][p] *= f
    N['availability'] = eta
    return N


def job(name, N, flexible, run):
    """Complete support-three list, optimal shortfalls and immediate predecessors."""
    run_stamp = stamp()
    M = choice(N) if flexible else model(N)
    baseline = solve(M, [0]*len(M['V']))
    assert baseline['status'] == 'optimal' and baseline['gap'] <= 10*EPS
    C = enumerate_lattice(M, DURATIONS, 0.25, K, EPS)
    cuts = sparse(C['cuts'])
    cert = [certify(M, [dict(s).get(v, 0) for v in range(len(M['V']))],
                    0.25*M['total']) for s in cuts]
    assert all(c['certified'] for c in cert)
    named = lambda S, V: sorted(tuple((V[v][0], V[v][1], d) for v, d in s) for s in S)
    if flexible:
        old = json.loads(Path('results/chemistry-896581f/cuts/'
                             'liion_free_a0.25_h0_s0_L6.json').read_text())
    else:
        old = json.loads(Path('results/liion-residual-2395a5c/cuts/'
                             'base_a0.25_h0_s0_L6.json').read_text())
    A, B = set(named(old['cuts'], old['nodes'])), set(named(cuts, M['V']))
    out = {'stamp': run_stamp, 'case': name, 'flexible': flexible, 'network': N,
           'total': M['total'], 'baseline': baseline, 'baseline_share': baseline['phi']/M['total'],
           'cuts': cuts, 'certificates': cert, 'complete': True, 'lp_calls': C['lp_calls'],
           'vanish': sorted(A-B), 'appear': sorted(B-A)}
    path = Path('results') / run / f'{name}.json'
    path.write_text(json.dumps(out, indent=1)+'\n', encoding='utf-8')
    print(name, 'baseline', out['baseline_share'], 'cuts', len(cuts),
          'vanish', len(A-B), 'appear', len(B-A), flush=True)


def main():
    run = sys.argv[1]
    (Path('results') / run).mkdir(parents=True, exist_ok=True)
    shares = json.loads(Path('data/raw/enduse/battery_shares.json').read_text())
    co, ni = shares['cobalt']['fraction'], shares['nickel']['fraction']
    for flexible in (False, True):
        tag = 'choice' if flexible else 'fixed'
        for voltage in (3.2, 3.7):
            job(f'japan{voltage}_{tag}', build(japan_voltage=voltage), flexible, run)
        job(f'eu_sold_{tag}', build(eu_sold=True), flexible, run)
        job(f'supplement_{tag}', build(japan_voltage=3.7, eu_sold=True), flexible, run)
        for f in (1, 0.1, 0.01):
            eta = {'mine_co': co, 'refined_co': co, 'mine_ni': ni, 'refined_ni': ni,
                   'refined_cu': f, 'aluminium': f, 'mine_mn': f}
            job(f'reserve{f}_{tag}', reserve(build(), eta), flexible, run)


if __name__ == '__main__':
    main()
