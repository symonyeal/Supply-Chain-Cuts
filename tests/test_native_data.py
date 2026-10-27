"""Native raw-data seam checks; full 62-case parity has a separate evidence runner."""

import hashlib
import json
import subprocess

import pytest

from analysis.check_native_data import R, cases, differences

# E: native data executable; c: context; r: production row.


@pytest.fixture
def run(native):
    E = native("sc-data")

    def call(op, opts=None, root=R, check=True):
        return subprocess.run(
            [str(E), op, str(root)],
            input=json.dumps(opts or {}),
            capture_output=True,
            text=True,
            encoding="utf8",
            check=check,
        )

    return call


def test_comparator_rejects_missing_extra_and_changed_values():
    assert differences({"a": 1.0}, {"a": 1.0000000000000002})
    assert differences({"a": 1}, {})
    assert differences({}, {"a": 1})
    assert differences([1, 2], [2, 1])
    assert not differences({"a": [1, None]}, {"a": [1, None]})
    assert len(cases()) == 62


def test_native_context_values(run):
    from analysis.build_context import build, outputs

    c = json.loads(run("context").stdout)
    assert len(c["production"]) == 240
    assert len(c["refining"]) == 16
    assert not differences(build(), c)
    assert run("context-csv").stdout.encode("utf8") == outputs(build())[1].encode("utf8")


def test_native_network_supplement_and_no_ncm(run):
    from chokepoint.net import build

    for opts in (
        {"sector": "joint", "ncm": 0.0},
        {"sector": "liion", "japan_voltage": 3.7, "eu_sold": True},
    ):
        assert not differences(build(**opts), json.loads(run("network", opts).stdout))


def test_source_verification_rejects_tampered_bytes(run, tmp_path):
    original = b"source bytes"
    (tmp_path / "raw.csv").write_bytes(original + b" altered")
    (tmp_path / "SOURCES.lock").write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "path": "raw.csv",
                        "committed": True,
                        "sha256": hashlib.sha256(original).hexdigest(),
                    }
                ]
            }
        ),
        encoding="utf8",
    )
    p = run("verify", root=tmp_path, check=False)
    assert p.returncode != 0
    assert "Source hash mismatch: raw.csv" in p.stderr


def test_invalid_network_options_rejected(run):
    for opts in ({"ncm": 1.01}, {"cutoff": 1.0}, {"basis": "unverified"}, {"sector": "other"}):
        assert run("network", opts, check=False).returncode != 0


def test_empty_retained_chain_reports_failure(run):
    p = run("network", {"sector": "liion", "cutoff": 0.99}, check=False)
    assert p.returncode != 0
    assert "Zero requirement" in p.stderr
