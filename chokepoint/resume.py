"""Task receipts and exclusive atomic publication for cut sweeps."""

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import uuid


def identity(task, root, durations, k, eps):
    """Bind actual code/input bytes and the full task, including dirty source edits."""
    root = Path(root)
    lock = json.loads((root / "SOURCES.lock").read_text(encoding="utf-8"))
    paths = [
        root / "SOURCES.lock",
        root / "run_cuts.py",
        *sorted((root / "chokepoint").glob("*.py")),
    ]
    paths += [root / s["path"] for s in lock["sources"] if (root / s["path"]).is_file()]
    hashes = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
    }
    task = json.loads(
        json.dumps(task, default=lambda x: sorted(map(list, x)) if isinstance(x, set) else list(x))
    )
    data = {"schema": 1, "task": task, "durations": durations, "k": k, "eps": eps, "sha256": hashes}
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def reusable(path, fingerprint):
    """A file's existence is not a completed, certified task."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        digest = value.pop("payload_sha256", None)
        if (
            digest
            != hashlib.sha256(
                json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            ).hexdigest()
        ):
            return False
        if (
            value.get("receipt") != fingerprint
            or value.get("complete") is not True
            or value.get("method") != "lattice"
        ):
            return False
        cuts, certs = value["cuts"], value["certificates"]
        if not isinstance(cuts, list) or not isinstance(certs, list) or len(cuts) != len(certs):
            return False
        nodes, theta = value["nodes"], value["theta"]
        if not isinstance(nodes, list) or not nodes or not isinstance(theta, (int, float)):
            return False
        keys = []
        for cut, cert in zip(cuts, certs, strict=True):
            if not isinstance(cut, list) or any(
                not isinstance(p, list)
                or len(p) != 2
                or type(p[0]) is not int
                or not 0 <= p[0] < len(nodes)
                or type(p[1]) is not int
                or p[1] <= 0
                for p in cut
            ):
                return False
            if len({p[0] for p in cut}) != len(cut) or cert.get("certified") is not True:
                return False
            if not all(
                type(cert.get(k)) in (int, float) and math.isfinite(cert[k])
                for k in ("phi", "dual", "gap")
            ):
                return False
            if (
                not cert["dual"] > theta + 1e-7
                or not 0 <= cert["gap"] <= 1e-6
                or abs(cert["phi"] - cert["dual"]) > 1e-6
            ):
                return False
            predecessors = cert.get("predecessors")
            if (
                not isinstance(predecessors, list)
                or len(predecessors) != len(cut)
                or any(p.get("phi", float("inf")) > theta + 1e-7 for p in predecessors)
            ):
                return False
            keys.append(json.dumps(cut))
        if len(set(keys)) != len(keys):
            return False
        for name in ("pruned", "milp_full", "brute_full"):
            if name in value:
                check = value[name]
                if name == "pruned" and not (
                    check.get("brute_equals_lattice") is True
                    and check.get("milp_equals_brute") is True
                    and check.get("milp_complete") is True
                ):
                    return False
                if name != "pruned" and check.get("equals_lattice") is not True:
                    return False
                if name == "milp_full" and check.get("complete") is not True:
                    return False
        return True
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


@contextmanager
def lease(path):
    """Hold an OS lease; process death releases it without a stale-lock convention."""
    lock = Path(str(path) + ".lock")
    with lock.open("a+b") as file:
        if os.name == "nt":
            import msvcrt

            file.seek(0)
            if not file.read(1):
                file.write(b"0")
                file.flush()
            file.seek(0)
            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == "nt":
                file.seek(0)
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(file, fcntl.LOCK_UN)


def publish(path, value):
    """Sync one unique candidate before replacing a single task result."""
    path = Path(path)
    value = {
        **value,
        "payload_sha256": hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest(),
    }
    candidate = path.with_name(path.name + "." + uuid.uuid4().hex + ".candidate")
    with candidate.open("x", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(value, indent=1, allow_nan=False) + "\n")
        file.flush()
        os.fsync(file.fileno())
    os.replace(candidate, path)
