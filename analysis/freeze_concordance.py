"""Freeze numerical HS2007–HS2012 concordance facts from the local UN workbook."""
import json
from collections import defaultdict
from pathlib import Path

import xlrd

from chokepoint.fetch import sha256


def main():
    root = Path(".")
    raw = root / "data/raw/hs/HS12_HS07.xls"
    s = xlrd.open_workbook(raw).sheet_by_index(0)
    forward, reverse = defaultdict(set), defaultdict(set)
    for i in range(2, s.nrows):
        h12, _, h07, _ = s.row_values(i)
        forward[str(h07)].add(str(h12))
        reverse[str(h12)].add(str(h07))
    pm = json.loads((root / "data/events/product_map.json").read_text(encoding="utf-8"))
    out = {"source": "UNSD Correlation HS2012-HS2007", "raw_sha256": sha256(raw),
           "hs07_to_hs12": {h: sorted(forward[h]) for h in pm["hs6_to_products"]},
           "one_to_one": {h: next(iter(forward[h])) for h in pm["hs6_to_products"]
                          if len(forward[h]) == 1 and len(reverse[next(iter(forward[h]))]) == 1}}
    p = root / "data/events/hs07_hs12.json"
    p.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    manifest = root / "data/research/manifest.json"
    d = json.loads(manifest.read_text(encoding="utf-8"))
    d["sources"] = [x for x in d["sources"] if x["path"] != p.as_posix()]
    d["sources"].append({"path": p.as_posix(), "url": next(
        x["url"] for x in d["sources"] if x["path"] == raw.as_posix()),
        "retrieved": "2026-10-16", "license": "Transcribed numerical concordance facts, UNSD",
        "sha256": sha256(p), "bytes": p.stat().st_size,
        "transform": "one-to-one facts from Correlation HS2012-HS2007; raw workbook local only"})
    manifest.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
