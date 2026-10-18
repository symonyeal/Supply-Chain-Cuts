"""Compare the portable test outputs with the immutable accepted audit."""

import difflib
import hashlib
import json
import sys
from pathlib import Path

import numpy
import openpyxl
import pypdf
import scipy

W = Path(__file__).resolve().parent
P, T = W / "portable", W / "portable-test"


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


accepted = {
    "results.json": "a3f5efb32394aea9d2f6eac82aa551cb64cc12f135c22754153d274a78035970",
    "independent_check.md": "ef3eee0685a236700c801b2bbf3c955d6db62ddb8eab4b7e370002d7882334a2",
    "recompute.py": "29092b322abc6ed6a83f29791941c8affad0f1955821aa9fd82de6efe2998083",
    "trace_sources.py": "1c92ee50e897556a93b79114b7da48c3e7ea7ed7838af24e9a687d749fc9b456",
}
r, t = read(W / "results.json"), read(T / "results.json")
s, u = read(W / "source_trace.json"), read(T / "source_trace.json")
checks = {
    "accepted_files_immutable": all(sha(W / p) == h for p, h in accepted.items()),
    "sector_certificates_and_L_exactly_equal": r["sectors"] == t["sectors"],
    "rates_exactly_equal": r["rates"] == t["rates"],
    "events_exactly_equal": r["events"] == t["events"],
    "source_trace_exactly_equal": s == u,
    "enumerated_cut_lists_equal": all(t["enumeration"]["sectors"][x]["same_named_list"] for x in ("pv", "joint")),
    "frozen_input_hashes_match_lock": not t["locked_input_mismatches"],
    "cut_copies_byte_identical": all(sha(P / "inputs" / p) == sha(W.parent / "independent-inputs" / p) for p in ("pv-cuts.json", "joint-cuts.json")),
}
hhi = {p: {"accepted": r["network"]["layers"][p]["HHI"], "portable": t["network"]["layers"][p]["HHI"]}
       for p in r["network"]["layers"] if r["network"]["layers"][p]["HHI"] != t["network"]["layers"][p]["HHI"]}
for x in (r, t):
    for v in x["network"]["layers"].values():
        v.pop("HHI")
checks["network_equal_except_disclosed_HHI_correction"] = r["network"] == t["network"]
assert all(checks.values()), checks
out = {
    "original_code_sha256": {p: accepted[p] for p in ("recompute.py", "trace_sources.py")},
    "portable_code_sha256": {p: sha(P / p) for p in ("recompute.py", "trace_sources.py")},
    "cut_input_sha256": {p: sha(P / "inputs" / p) for p in ("pv-cuts.json", "joint-cuts.json")},
    "immutable_accepted_artifacts_sha256": {p: accepted[p] for p in ("results.json", "independent_check.md")},
    "test": {"output_directory": "../portable-test", "checks": checks,
             "L": {s: t["sectors"][s]["probability"]["L"] for s in ("pv", "joint")},
             "enumerated_cuts": {s: t["enumeration"]["sectors"][s]["found"] for s in ("pv", "joint")},
             "HHI_correction": hhi},
    "versions": {"python": sys.version, "numpy": numpy.__version__, "scipy": scipy.__version__,
                 "openpyxl": openpyxl.__version__, "pypdf": pypdf.__version__},
}
(P / "package-manifest.json").write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8")
patch = ""
for p in ("recompute.py", "trace_sources.py"):
    patch += "".join(difflib.unified_diff((W / p).read_text(encoding="utf-8").splitlines(keepends=True),
                                        (P / p).read_text(encoding="utf-8").splitlines(keepends=True),
                                        fromfile="original/"+p, tofile="portable/"+p))
(P / "portability.patch").write_text(patch, encoding="utf-8")
x = read(P / "package-manifest.json")
print(json.dumps({"checks": x["test"]["checks"], "L": x["test"]["L"], "versions": x["versions"]}, indent=2))
