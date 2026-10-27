"""Optional executable protocol and boundary checks against the Python oracle."""
# L: exact cut union; V: country/product nodes; rho: common-shock share.
import os

import pytest

from analysis.check_rust import bits, differences, edges
from chokepoint.risk import exact_union
from chokepoint.rust import batch


def test_comparator_rejects_bad_values_and_missing_keys():
    a = [{'key': 'a', 'L': 0.5}]
    assert differences(a, [{'key': 'a', 'L': 0.6}])['different']
    diff = differences(a, [{'key': 'b', 'L': 0.5}])
    assert diff['only_python'] == ['a'] and diff['only_rust'] == ['b']
    with pytest.raises(ValueError, match='Duplicate'):
        differences(a * 2, a)


def test_backend_selection_is_explicit():
    row = edges()[0]['input']
    assert exact_union(**row) == exact_union(**row, backend='python')
    with pytest.raises(ValueError, match='backend'):
        exact_union(**row, backend='missing')


@pytest.mark.skipif(not os.environ.get('CUT_RISK_BIN'), reason='CUT_RISK_BIN not set')
def test_rust_boundary_parity_and_bad_request():
    cases = edges()
    out = batch([case['input'] for case in cases])
    assert [row['bits'] for row in out] == [bits(exact_union(**case['input']))
                                           for case in cases]
    assert bits(exact_union(**cases[0]['input'], backend='rust')) == out[0]['bits']
    bad = dict(cases[0]['input'], rho=1.5)
    with pytest.raises(ValueError, match='Valid node'):
        batch([bad])
