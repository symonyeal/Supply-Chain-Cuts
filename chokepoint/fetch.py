"""Frozen-source verification. SOURCES.lock is the input contract."""
import hashlib
import json
import platform
import subprocess
import urllib.request
from pathlib import Path


def sha256(path):
    """Return the SHA-256 of exact file bytes."""
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify(root=Path(".")):
    """Verify every locked source; changed bytes are errors, never rebaselines.

    A committed source must be present. A local-only source (licence unverified) may be
    absent from a clone; if present, its hash must match.
    """
    sources = json.loads((root / "SOURCES.lock").read_text(encoding="utf-8"))["sources"]
    absent = []
    for x in sources:
        p = root / x["path"]
        if not p.is_file():
            if x["committed"]:
                raise ValueError(f"Committed frozen source missing: {p}")
            absent.append(x["path"])
        elif sha256(p) != x["sha256"]:
            raise ValueError(f"Hash mismatch: {p}")
    return {"sources": len(sources), "absent_local_only": absent,
            "lock_sha256": sha256(root / "SOURCES.lock")}


def fetch_source(source, root=Path(".")):
    """Fetch a direct frozen source only if absent; verify against the locked digest."""
    p = root / source["path"]
    if p.exists():
        if sha256(p) != source["sha256"]:
            raise ValueError(f"Hash mismatch: {p}")
        return p
    if source.get("transform") or source.get("archive_member"):
        raise ValueError("Derived snapshot: regenerate with the recorded acquisition script")
    request = urllib.request.Request(source["url"], headers={"User-Agent": "Chokepoint-Lab/0.2"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != source["sha256"]:
        raise ValueError(f"Remote bytes changed: {source['url']}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def stamp(root=Path(".")):
    """Provenance of a result bundle: code revision, tree state, lock digest, versions."""
    import numpy
    import scipy

    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                              text=True, check=True).stdout.rstrip()

    changed = [x[3:] for x in git("status", "--porcelain").splitlines()
               if not x[3:].startswith(("results/", "docs/", "site/"))]
    return {"revision": git("rev-parse", "HEAD"), "dirty": changed, **verify(root),
            "python": platform.python_version(), "numpy": numpy.__version__,
            "scipy": scipy.__version__}
