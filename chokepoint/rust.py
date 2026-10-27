"""Optional JSON-lines exact-union backend; recourse remains in SciPy."""
# V: country/product nodes; p: onset probabilities; rho: country-shock share.
# D: outage months; w: categorical weights; L: exact cut-union probability.
import json
import os
from pathlib import Path
import subprocess


def executable(binary=None):
    """Resolve an explicitly built executable, without compiling at import time."""
    path = binary or os.environ.get("CUT_RISK_BIN")
    if not path:
        raise RuntimeError("Set CUT_RISK_BIN to the built cut-risk executable")
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def batch(inputs, *, binary=None):
    """Evaluate a batch in one process and preserve input/output order."""
    rows = list(inputs)
    payload = "".join(json.dumps(row, allow_nan=False) + "\n" for row in rows)
    run = subprocess.run([str(executable(binary))], input=payload, text=True,
                         capture_output=True, check=True)
    out = [json.loads(line) for line in run.stdout.splitlines()]
    if len(out) != len(rows):
        raise RuntimeError("Rust response count differs from request count")
    for row in out:
        if "error" in row:
            raise ValueError(row["error"])
    return out


def exact_union(V, p, rho, durations, weights, cuts, *, binary=None):
    """P(any duration cut), using the optional Rust executable."""
    row = {"V": [list(v) for v in V], "p": [float(x) for x in p], "rho": float(rho),
           "durations": [int(d) for d in durations], "weights": [float(w) for w in weights],
           "cuts": [[int(d) for d in cut] for cut in cuts]}
    return float(batch([row], binary=binary)[0]["L"])
