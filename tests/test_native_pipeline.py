"""Native command contracts checked against independent Python risk and HTTP clients."""
# N: physical network; D: outage months; L/U: lower/upper failure bounds.
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import time

import pytest

from chokepoint.net import model
from chokepoint.risk import bracket, residual_sampling


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def supply(native):
    return native('supply')


def invoke(supply, command, **paths):
    args = [str(supply), command]
    for key, path in paths.items():
        args.extend(['--' + key, str(path)])
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                          timeout=60, check=False)


def save(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


@pytest.fixture
def toy(supply, tmp_path):
    N = {'nodes': [{'country': country, 'product': product, 'capacity': 1 / 12}
                   for country, product in [('A', 'mine'), ('B', 'cell')]],
         'finals': ['cell'], 'a': [['mine', 'cell', 1]],
         'requirement': {'mine': 1, 'cell': 1}, 'ncm': 0.5}
    config = {'alpha': 0.25, 'k': 1, 'n': 512, 'seed': 7, 'time_limit': 15}
    law = {'nodes': [['A', 'mine'], ['B', 'cell']],
           'rates': {'p': [0.2, 0.3], 'rho': 0.6},
           'durations': {'durations': [3, 6, 12], 'weights': [0.25, 0.25, 0.5]}}
    paths = {key: save(tmp_path / f'{key}.json', value)
             for key, value in [('network', N), ('config', config), ('law', law)]}
    cuts = invoke(supply, 'cuts', network=paths['network'], config=paths['config'])
    assert cuts.returncode == 0, cuts.stderr
    certificate = json.loads(cuts.stdout)
    assert certificate['complete'] is True
    # A 6-month loss is exactly 25%; a 12-month loss crosses the strict threshold.
    assert certificate['cuts'] == [[0, 12], [12, 0]]
    assert len(certificate['certificates']) == 2
    paths['cuts'] = save(tmp_path / 'cuts.json', certificate)
    return N, config, law, certificate, paths


def test_native_risk_matches_python_and_hand_probability(supply, toy):
    N, config, law, certificate, paths = toy
    result = invoke(supply, 'risk', **paths)
    assert result.returncode == 0, result.stderr
    native = json.loads(result.stdout)
    assert native['status'] == 'optimal'
    assert certificate['network'] == N
    assert certificate['config'] == config
    assert certificate['nodes'] == law['nodes']
    M = model(N)
    args = (M['V'], law['rates']['p'], law['rates']['rho'],
            law['durations']['durations'], law['durations']['weights'], certificate['cuts'])
    bounds = bracket(*args, k=1, complete=True)
    oracle = residual_sampling(M, *args[1:], alpha=0.25, k=1, complete=True,
                               n=config['n'], seed=config['seed'])
    # Independent onset countries: failure is the union of their 12-month onsets.
    assert native['bounds']['L'] == pytest.approx(0.1 + 0.15 - 0.1 * 0.15)
    assert native['bounds']['U'] == pytest.approx(bounds['U'], abs=1e-14)
    for name in ('L', 'estimate', 'se', 'ci95', 'residual_estimate'):
        assert native['residual'][name] == pytest.approx(oracle[name], rel=1e-13, abs=1e-14)
    for name in ('residual_events', 'zero_residuals', 'lp_states', 'n', 'seed', 'complete', 'k'):
        assert native['residual'][name] == oracle[name]
    assert oracle['lp_states'] > 0  # Exercise residual recourse beyond the enumerated cuts.
    assert native['residual']['ci95'][1] > native['residual']['L']


@pytest.mark.parametrize('change,expected', [
    ('network', 'exact network'), ('config', 'configuration mismatch'),
    ('incomplete', 'complete'), ('roster', 'roster differs'),
    ('law_grid', 'duration grids must match'), ('missing_rate', 'no frozen onset rate'),
])
def test_native_risk_rejects_unmatched_certificates(supply, toy, change, expected):
    N, config, law, certificate, paths = toy
    if change == 'network':
        N['nodes'][0]['capacity'] *= 2
        save(paths['network'], N)
    elif change == 'config':
        config['h'] = 1
        save(paths['config'], config)
    elif change == 'incomplete':
        certificate['complete'] = False
        save(paths['cuts'], certificate)
    elif change == 'roster':
        certificate['nodes'].reverse()
        save(paths['cuts'], certificate)
    elif change == 'law_grid':
        law['durations'] = {'durations': [3, 12], 'weights': [0.25, 0.75]}
        save(paths['law'], law)
    else:
        law['nodes'][0][0] = 'missing'
        save(paths['law'], law)
    result = invoke(supply, 'risk', **paths)
    assert result.returncode != 0
    assert expected in result.stderr
    assert not result.stdout.strip()


def request(port, method, path):
    client = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
    try:
        client.request(method, path)
        response = client.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        client.close()


def test_native_server_get_head_missing_and_traversal(supply, tmp_path):
    site = tmp_path / 'site'
    site.mkdir()
    body = b'<!doctype html><title>owned server probe</title>'
    (site / 'index.html').write_bytes(body)
    sentinel = b'outside site root'
    (tmp_path / 'outside.txt').write_bytes(sentinel)
    with socket.socket() as lease:
        lease.bind(('127.0.0.1', 0))
        port = lease.getsockname()[1]
    with (tmp_path / 'server.log').open('w') as log:
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        process = subprocess.Popen([str(supply), 'serve', '--root', str(tmp_path),
                                    '--listen', f'127.0.0.1:{port}'], cwd=ROOT,
                                   stdout=log, stderr=log, creationflags=flags)
        try:
            deadline = time.monotonic() + 8
            while True:
                assert process.poll() is None, 'Owned native server exited during startup'
                try:
                    status, headers, received = request(port, 'GET', '/?probe=1')
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.05)
            assert status == 200 and received == body
            assert headers['Content-Type'] == 'text/html; charset=utf-8'
            status, headers, received = request(port, 'HEAD', '/')
            assert status == 200 and received == b''
            assert int(headers['Content-Length']) == len(body)
            # HTTPConnection discards a HEAD response body; inspect the wire as well.
            with socket.create_connection(('127.0.0.1', port), timeout=2) as stream:
                stream.sendall(b'HEAD / HTTP/1.1\r\nHost: localhost\r\n\r\n')
                chunks = []
                while chunk := stream.recv(4096):
                    chunks.append(chunk)
            raw_headers, raw_body = b''.join(chunks).split(b'\r\n\r\n', 1)
            assert b'200 OK' in raw_headers and raw_body == b''
            for path in ('/absent.css', '/../outside.txt', '/..\\outside.txt',
                         '/%2e%2e/outside.txt'):
                status, _, received = request(port, 'GET', path)
                assert status == 404 and sentinel not in received
            assert request(port, 'POST', '/')[0] == 405
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_native_real_pv_run_manifest_binds_inputs_and_executable(supply, tmp_path):
    config = {'sector': 'pv', 'k': 1, 'n': 64, 'seed': 7, 'time_limit': 30}
    config_path = save(tmp_path / 'config.json', config)
    law_path = ROOT / 'results/pv-residual-2395a5c/risk.json'
    output = tmp_path / 'run'
    result = invoke(supply, 'run', root=ROOT, config=config_path, law=law_path, out=output)
    assert result.returncode == 0, result.stderr
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest == json.loads(result.stdout)
    assert manifest['config'] == config
    assert manifest['status'] == 'optimal' and manifest['cuts_complete'] is True
    assert manifest['solver'] == '1.12.0' and manifest['committed_sources'] > 0
    for name, path in [('binary_sha256', supply),
                       ('source_lock_sha256', ROOT / 'SOURCES.lock'),
                       ('law_sha256', law_path)]:
        assert manifest[name] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert len(manifest['network_sha256']) == 64
    N = json.loads((output / 'network.json').read_text(encoding='utf-8'))
    bundle = ROOT / 'results/pv-ba89465/network.json'
    frozen = json.loads(bundle.read_text(encoding='utf-8'))['pv']
    # The bundle recorded the network without the builder's working trade and BOM tables.
    assert {key: N[key] for key in frozen} == frozen
    assert json.loads((output / 'cuts.json').read_text(encoding='utf-8'))['network'] == N
    risk = json.loads((output / 'risk.json').read_text(encoding='utf-8'))
    assert risk['status'] == manifest['status']
    assert risk['residual']['n'] == config['n']
