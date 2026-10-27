"""Full explorer payload parity and malformed-certificate rejection at the native boundary."""
# root: repository path; p: JSON pointer; runs: immutable result bundle names.
import json
import subprocess

import pytest

from analysis.build_site import build, plain
from analysis.check_native_site import RUNS, controls, differences
from analysis.check_native_site import native as payload


def test_payload_comparator_rejects_changed_missing_and_reordered_leaves():
    controls()
    with pytest.raises(ValueError, match='nonempty'):
        differences({}, {})
    assert differences({'x': [{'v': 1}, {'v': 1}]}, {'x': [{'v': 1}]})['only_python']
    assert differences({'x': -0.0}, {'x': 0.0})['different']


def test_native_complete_payload_matches_python(native):
    old_full = build(*RUNS)
    old = plain(old_full)
    new = payload(native('sc-site'))
    assert len(new['configs']) > 100 and len(new['testRows']) == 9
    assert not any(differences(old, new).values())
    new_full = payload(native('sc-site'), full=True)
    assert not any(differences(old_full, new_full).values())


def test_native_rejects_network_roster_mismatch(native, tmp_path):
    target = tmp_path / 'results' / 'bad'
    target.mkdir(parents=True)
    fixtures = {'network.json': {'liion': {'nodes': [{'country': 'A', 'product': 'ore'}]}},
                'data_checks.json': {},
                'risk.json': {'sector': 'liion', 'nodes': [['B', 'ore']]}}
    for name, value in fixtures.items():
        (target / name).write_text(json.dumps(value), encoding='utf-8')
    process = subprocess.run([native('sc-site'), str(tmp_path), 'bad'],
                             text=True, encoding='utf-8', capture_output=True, check=False)
    assert process.returncode != 0 and 'Network roster differs' in process.stderr
