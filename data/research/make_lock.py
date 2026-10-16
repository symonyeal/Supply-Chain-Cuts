"""Write SOURCES.lock: url, retrieval date, SHA-256, bytes, licence and whether committed.

Raw files are committed only under a verified open licence or as transcribed numerical
facts; the rest stay local (gitignored), locked by hash and re-fetchable by URL.
"""
import json
from pathlib import Path

from chokepoint.fetch import sha256

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ("data/raw/hs/", "data/raw/cochilco/production_1996_2025.xlsx", "data/events/raw/oecd-",
         "data/events/raw/gdacs-", "data/events/raw/mofcom-", "data/events/raw/indonesia-",
         "data/events/raw/zimbabwe-")
OPEN = ("data/events/raw/oecd-report-2026.pdf",)
LICENCE = {"data/events/raw/oecd-report-2026.pdf": "CC-BY-4.0 (report p. 2)",
           "data/events/raw/oecd-": "OECD open licence per 2024 policy; dataset terms page "
                                    "returned 403 (unverified)",
           "data/events/raw/gdacs-": "GDACS terms (March 2025): attribution, no reuse licence",
           "data/events/raw/mofcom-": "Official announcement; no licence statement",
           "data/events/raw/indonesia-": "Official regulation; no licence statement",
           "data/events/raw/zimbabwe-": "Statutory instrument; no licence statement",
           "data/sites/raw/": "USGS public domain",
           "data/raw/usgs/myb1-2023-cobalt.xlsx": "USGS public domain (Darton figures cited)",
           "data/raw/usgs/myb2023_cobalt_refinery.csv": "Transcribed numerical facts, USGS"}


def licence(path, given):
    return given or next((v for k, v in sorted(LICENCE.items(), key=lambda x: -len(x[0]))
                          if path.startswith(k)), "unverified")


def main():
    rows = []
    for x in json.loads((ROOT / "data/research/manifest.json").read_text())["sources"]:
        x = dict(x)
        x["licence"] = x.pop("license", None) or x.get("licence")
        if sha256(ROOT / x["path"]) != x.pop("sha256"):
            raise ValueError(f"Frozen bytes changed since research: {x['path']}")
        x.pop("bytes", None)
        rows.append(x)
    for f in ("data/events/raw/downloads.json", "data/sites/raw/downloads.json"):
        for x in json.loads((ROOT / f).read_text()):
            if x["status"] == "ok":
                rows.append({"path": x["path"].replace("\\", "/"), "url": x["url"],
                             "retrieved": "2026-10-15", "licence": None})
    rows.append({"path": "data/raw/usgs/myb1-2023-cobalt.xlsx",
                 "url": "https://pubs.usgs.gov/myb/vol1/2023/myb1-2023-cobalt.xlsx",
                 "retrieved": "2026-10-15", "licence": None})
    rows.append({"path": "data/raw/usgs/myb2023_cobalt_refinery.csv",
                 "url": "https://pubs.usgs.gov/myb/vol1/2023/myb1-2023-cobalt.xlsx",
                 "retrieved": "2026-10-15", "licence": None,
                 "transform": "Table 8, 2023 column, transcribed with sheet cells"})
    out = []
    for x in rows:
        p = ROOT / x["path"]
        if not p.is_file():
            continue
        x["licence"] = licence(x["path"], x["licence"])
        x["committed"] = x["path"] in OPEN or not x["path"].startswith(LOCAL)
        out.append({**x, "sha256": sha256(p), "bytes": p.stat().st_size})
    out.sort(key=lambda x: x["path"])
    (ROOT / "SOURCES.lock").write_text(json.dumps({"sources": out}, indent=1) + "\n",
                                       encoding="utf-8")
    print(len(out), "sources;", sum(x["committed"] for x in out), "committed")


if __name__ == "__main__":
    main()
