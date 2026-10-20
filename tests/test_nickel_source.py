"""Production sensitivity retains the reference demand and other material capacities."""
import pytest

from run_nickel import read_metal, replace_metal


def network():
    return {'nodes': [{'country': 'NOR', 'product': 'refined_ni', 'annual': 100., 'capacity': 2.},
                      {'country': 'NOR', 'product': 'cell', 'annual': 20., 'capacity': 1.}],
            'requirement': {'refined_ni': 50., 'cell': 20.},
            'demand_scale': {'cell': .5}}


def test_production_replaces_only_matching_metal_at_fixed_reference_demand():
    n = network()
    v, used = replace_metal(n, [{'iso3': 'NOR', 'value': '95000', 'year': '2023',
                               'form': 'metal', 'qualifier': 'reported', 'cell': 'T12!K50'}])
    assert v['nodes'][0]['annual'] == 95.
    assert v['nodes'][0]['capacity'] == pytest.approx(1.9)
    assert v['nodes'][0]['basis'] == 'production'
    assert v['nodes'][1] == n['nodes'][1]
    assert v['requirement'] == n['requirement']
    assert v['demand_scale'] == n['demand_scale']
    assert n['nodes'][0]['annual'] == 100.
    assert used[0]['cell'] == 'T12!K50'


def test_a_nonmetal_observation_is_not_silently_adopted():
    with pytest.raises(ValueError, match='metal'):
        replace_metal(network(), [{'iso3': 'NOR', 'value': '95000', 'year': '2023',
                                   'form': 'ferronickel', 'qualifier': 'reported', 'cell': 'x'}])


def test_duplicate_country_observation_is_rejected():
    r = {'iso3': 'NOR', 'value': '95000', 'year': '2023', 'form': 'metal',
         'qualifier': 'reported', 'cell': 'x'}
    with pytest.raises(ValueError, match='duplicate'):
        replace_metal(network(), [r, r])


def test_frozen_observations_match_published_metal_rows():
    rows = read_metal()
    expected = {'AUS': (92300, 'reported'), 'CHN': (244800, 'reported'),
                'FIN': (43300, 'estimated'), 'FRA': (5714, 'reported'),
                'JPN': (52000, 'estimated'), 'MDG': (36000, 'estimated'),
                'NOR': (95000, 'reported'), 'RUS': (156000, 'reported'),
                'ZAF': (37390, 'reported'), 'GBR': (34000, 'estimated')}
    assert {r['iso3']: (int(r['value']), r['qualifier']) for r in rows} == expected
    assert len(rows) == 10


def test_unobserved_origins_and_unretained_observations_keep_the_reference_roster():
    n = network()
    n['nodes'].append({'country': 'DEU', 'product': 'refined_ni', 'annual': 10.,
                       'capacity': .2, 'basis': 'trade'})
    p, used = replace_metal(n, [{'iso3': 'MDG', 'value': '36000', 'year': '2023',
                                'form': 'metal', 'qualifier': 'estimated', 'cell': 'T12!K43'}])
    assert p == n and p is not n and used == []
