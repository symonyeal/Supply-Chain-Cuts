"""Capacity accounting at fixed demand and the METI charge-to-energy conversion."""
import pytest

from chokepoint.net import build, model
from chokepoint.recourse import solve
from run_supply import reserve


def test_reservation_keeps_demand_and_exposes_baseline_failure():
    N = build()
    P = reserve(N, {'refined_cu': 0.001})
    assert P['requirement'] == N['requirement']
    M = model(P)
    a = solve(M, [0]*len(M['V']))
    assert a['status'] == 'optimal' and a['gap'] < 1e-7
    assert a['phi']/M['total'] > 0.5
    assert N['supply_ratio']['refined_cu'] > 1


def test_meti_units_and_basis():
    A, B = build(japan_voltage=3.2), build(japan_voltage=3.7)
    a = next(x for x in A['nodes'] if (x['country'], x['product']) == ('JPN', 'cell'))
    b = next(x for x in B['nodes'] if (x['country'], x['product']) == ('JPN', 'cell'))
    assert b['annual'] == pytest.approx(5136311*3.7/1e6)
    assert a['annual']/b['annual'] == pytest.approx(3.2/3.7)
    assert b['basis'] == 'imputed' and b['unit'] == 'GWh'
