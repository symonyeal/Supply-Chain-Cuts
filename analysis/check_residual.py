"""Check W1 bundles against their immutable predecessors; write residual_checks.json.

Usage: python analysis/check_residual.py BEFORE AFTER.
"""
import copy
import json
import sys
from pathlib import Path

import numpy as np

from chokepoint.fetch import sha256, stamp


def check(before, after):
    """Legacy probabilities and cut bytes unchanged; R3/R4 against crude MC."""
    a, b = (Path("results") / x for x in (before, after))
    A, B = (json.loads((x / "risk.json").read_text(encoding="utf-8")) for x in (a, b))
    old, new = copy.deepcopy(A), copy.deepcopy(B)
    old.pop("stamp")
    new.pop("stamp")
    new.pop("residual")
    if "tests" in new:
        new["tests"]["H3_annual_failure"].pop("residual")
        new["hard"].pop("residual")
    assert new == old, "Legacy risk results changed"
    assert not B["stamp"]["dirty"]
    assert A["stamp"]["lock_sha256"] == B["stamp"]["lock_sha256"]
    assert json.loads((a / "network.json").read_text()) == json.loads(
        (b / "network.json").read_text())
    assert {p.name: sha256(p) for p in (a / "cuts").glob("*.json")} == {
        p.name: sha256(p) for p in (b / "cuts").glob("*.json")}
    rows = {}
    for alpha, R in B["residual"].items():
        C, M = B["configs"][f"base_a{alpha}_h0_s0_L6_D12"], B["MC"][alpha]
        assert R["L"] == C["L"] and R["estimate"] >= C["L"]
        se = float(np.hypot(R["se"], M["se"]))
        delta = abs(R["estimate"]-M["estimate"])
        rows[alpha] = {"L": C["L"], "estimate": R["estimate"], "ci95": R["ci95"],
                       "se": R["se"], "MC": M["estimate"], "MC_se": M["se"],
                       "difference": delta, "combined_se": se,
                       "agrees_with_MC": delta <= 4*se,
                       "smaller_se": R["se"] <= M["se"]}
    out = {"stamp": stamp(), "original_bundle": before, "bundle": after,
           "legacy_risk_equal": True, "network_equal": True, "cut_bytes_equal": True,
           "estimates": rows, "R4": rows["0.25"]["smaller_se"]}
    if B["sector"] == "joint":
        out["R3"] = rows["0.1"]["agrees_with_MC"]
    (b / "residual_checks.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    check(*sys.argv[1:3])
