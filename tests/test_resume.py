"""Resume requires exact task/input identity and an intact completed certificate."""

import json

import pytest

from analysis.build_site import clean
from chokepoint.resume import identity, lease, publish, reusable


def certified():
    return {
        "receipt": "task",
        "complete": True,
        "method": "lattice",
        "nodes": [["A", "ore"]],
        "theta": 1,
        "cuts": [[[0, 3]]],
        "certificates": [
            {
                "certified": True,
                "phi": 2,
                "dual": 2,
                "gap": 0,
                "predecessors": [{"v": 0, "D": 0, "phi": 0}],
            }
        ],
    }


def test_resume_rejects_truncated_legacy_changed_and_uncertified_results(tmp_path):
    path = tmp_path / "task.json"
    path.write_text("{")
    assert not reusable(path, "task")
    path.write_text(json.dumps(certified()))
    assert not reusable(path, "task")
    publish(path, certified())
    assert reusable(path, "task")
    assert not reusable(path, "other task")
    changed = json.loads(path.read_text())
    changed["cuts"] = []
    path.write_text(json.dumps(changed))
    assert not reusable(path, "task")
    changed = certified()
    changed["certificates"][0]["certified"] = False
    publish(path, changed)
    assert not reusable(path, "task")


def test_identity_tracks_dirty_source_bytes_not_only_git_revision(tmp_path):
    (tmp_path / "SOURCES.lock").write_text('{"sources":[]}')
    (tmp_path / "run_cuts.py").write_text("")
    code = tmp_path / "chokepoint"
    code.mkdir()
    source = code / "model.py"
    source.write_text("x=1")
    first = identity(("task", {}, {}, []), tmp_path, [3, 6], 3, 1e-7)
    source.write_text("x=2")
    assert identity(("task", {}, {}, []), tmp_path, [3, 6], 3, 1e-7) != first


def test_task_lease_has_one_writer_and_releases_on_exit(tmp_path):
    path = tmp_path / "task.json"
    with lease(path), pytest.raises(OSError), lease(path):
        pytest.fail("A second writer acquired the task")
    with lease(path):
        pass


def test_interrupted_candidate_preserves_previous_task(tmp_path, monkeypatch):
    path = tmp_path / "task.json"
    publish(path, certified())
    old = path.read_bytes()

    def fail(*args):
        raise OSError("injected interruption")

    monkeypatch.setattr("chokepoint.resume.os.replace", fail)
    with pytest.raises(OSError):
        publish(path, {**certified(), "receipt": "new"})
    assert path.read_bytes() == old


@pytest.mark.parametrize("dirty", [None, False, ["changed.py"], [0]])
def test_publication_requires_an_empty_provenance_path_list(dirty):
    assert not clean({"dirty": dirty})
    assert clean({"dirty": []})
