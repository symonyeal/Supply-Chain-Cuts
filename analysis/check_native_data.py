"""Freeze independent Python outputs and compare every native data value."""

import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys

# R: repository root; W: persistent evidence directory; x/y: compared values.
R = Path(__file__).resolve().parents[1]
W = R.parent.parent / "supply-chain-redesign-20261027/native-data"
sys.path.insert(0, str(R))


def cases():
    return [
        {"sector": sector, "ncm": ncm, "basis": basis, "cutoff": cutoff}
        for sector in ("liion", "pv", "joint")
        for ncm in (0.0, 0.5, 1.0)
        for basis in ("production", "trade")
        for cutoff in (0.0, 0.01, 0.05)
    ] + [
        {"sector": sector, **option}
        for sector in ("liion", "joint")
        for option in (
            {"japan_voltage": 3.7},
            {"eu_sold": True},
            {"japan_voltage": 3.6, "eu_sold": True},
            {"exclude": [["CHN", "cell"], ["IDN", "mine_ni"]]},
        )
    ]


def differences(x, y, path="$"):
    if isinstance(x, dict) and isinstance(y, dict):
        if x.keys() != y.keys():
            return [f"{path}: keys differ {x.keys() ^ y.keys()}"]
        return [d for key in x for d in differences(x[key], y[key], f"{path}.{key}")]
    if isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            return [f"{path}: lengths {len(x)} != {len(y)}"]
        return [d for i, (a, b) in enumerate(zip(x, y)) for d in differences(a, b, f"{path}[{i}]")]
    if x != y:
        return [f"{path}: {x!r} != {y!r}"]
    return []


def freeze():
    from analysis.build_context import build as context, outputs
    from chokepoint.net import build

    W.mkdir(parents=True, exist_ok=True)
    c = context(R)
    (W / "baseline-context.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf8")
    (W / "baseline-context.csv").write_bytes(outputs(c)[1].encode("utf8"))
    networks = []
    for opts in cases():
        kwargs = dict(opts)
        if "exclude" in kwargs:
            kwargs["exclude"] = [tuple(pair) for pair in kwargs["exclude"]]
        networks.append({"opts": opts, "network": build(root=R, **kwargs)})
    (W / "baseline-networks.json").write_text(
        json.dumps(networks, ensure_ascii=False), encoding="utf8"
    )
    (W / "README.md").write_text(
        "# Native data parity\n\nPython baselines frozen before Rust implementation. "
        "62 cases cover sectors, recipe endpoints, both source bases, cutoff endpoints, "
        "supplements and exclusions. Comparisons preserve all list ordering and full "
        "numeric precision; object key order is not semantic.\n",
        encoding="utf8",
    )
    print(f"Frozen {len(networks)} complete networks and context JSON/CSV")


def compare(exe):
    def native(op, opts=None):
        p = subprocess.run(
            [str(exe), op, str(R)],
            input=json.dumps(opts or {}),
            text=True,
            capture_output=True,
            check=True,
            encoding="utf8",
        )
        return p.stdout

    baseline = json.loads((W / "baseline-context.json").read_text(encoding="utf8"))
    bad = copy.deepcopy(baseline)
    bad["production"][0]["tonnes"] += 1
    assert differences(baseline, bad), "Comparator must reject a perturbed datum"
    checks = []
    got = json.loads(native("context"))
    checks.append({"check": "context", "differences": differences(baseline, got)})
    text = native("context-csv").encode("utf8")
    checks.append(
        {"check": "context_csv_bytes", "equal": text == (W / "baseline-context.csv").read_bytes()}
    )
    for i, case in enumerate(json.loads((W / "baseline-networks.json").read_text(encoding="utf8"))):
        got = json.loads(native("network", case["opts"]))
        checks.append(
            {
                "check": f"network_{i}",
                "opts": case["opts"],
                "differences": differences(case["network"], got),
            }
        )
    (W / "comparison.json").write_text(json.dumps(checks, indent=2), encoding="utf8")
    failures = [c for c in checks if c.get("differences") or c.get("equal") is False]
    print(
        json.dumps(
            {"checks": len(checks), "failures": len(failures), "first_failures": failures[:3]},
            indent=2,
        )
    )
    return int(bool(failures))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--out", type=Path, default=W)
    args = parser.parse_args()
    W = args.out
    if args.baseline:
        freeze()
    if args.exe:
        sys.exit(compare(args.exe))
