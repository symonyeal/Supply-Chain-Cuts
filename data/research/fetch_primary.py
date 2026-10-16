"""Freeze primary evidence for the 2024 capacity reconstruction."""

import hashlib
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "raw"


def fetch(x):
    """INPUT source entry. OUTPUT frozen file and SHA-256 sidecar entry."""
    p = OUT / x["path"]
    p.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(x["url"], timeout=90) as r:
        b = r.read()
    p.write_bytes(b)
    return {
        **x, "path": p.relative_to(ROOT).as_posix(), "retrieved": "2026-10-15",
        "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b),
    }


if __name__ == "__main__":
    U = [
        (
            "usgs/mcs2026_commodity_metadata.json",
            "https://www.sciencebase.gov/catalog/item/69837e43b66b01367d7ec7c7?format=json",
            "CC0-1.0",
        ),
        (
            "usgs/MCS2026_Commodities_Data.csv",
            ("https://www.sciencebase.gov/catalog/file/get/69837e43b66b01367d7ec7c7"
             "?f=__disk__d3%2Fac%2F84%2Fd3ac8466552946c5e8caa2c2c6338d9e1aff655d"),
            "CC0-1.0",
        ),
        (
            "usgs/MCS2026_Commodities_Data.xml",
            ("https://www.sciencebase.gov/catalog/file/get/69837e43b66b01367d7ec7c7"
             "?f=__disk__59%2F9f%2F78%2F599f78dcdae6cfc820ec8410e8a0e684c28be9d2"),
            "CC0-1.0",
        ),
        (
            "xu2020/supplement.pdf",
            ("https://media.springernature.com/original/springer-static/esm/"
             "art%3A10.1038%2Fs43246-020-00095-x/MediaObjects/43246_2020_95_MOESM1_ESM.pdf"),
            "CC-BY-4.0",
        ),
        (
            "usgs/myb1-2023-cobalt.xlsx",
            "https://pubs.usgs.gov/myb/vol1/2023/myb1-2023-cobalt.xlsx",
            "US-government-public-domain",
        ),
        (
            "cochilco/production_1996_2025.xlsx",
            ("https://www.cochilco.cl/web/download/140/"
             "estadisticas-estadisticas-de-la-mineria-no-metalica/16945/"
             "produccion-mineria-no-metalica-1996-2025.xlsx"),
            "No-explicit-open-license; factual-transcription-only",
        ),
    ]
    X = [{"path": p, "url": u, "license": l} for p, u, l in U]
    E = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        F = [(x, pool.submit(fetch, x)) for x in X]
        for x, f in F:
            try:
                y = f.result()
                E.append(y)
                print(y["path"], y["bytes"])
            except (OSError, URLError) as e:
                print(x["path"], type(e).__name__, str(e))
    p = ROOT / "data/research/manifest.json"
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"sources": []}
    old = {x["path"]: x for x in d["sources"]}
    old.update({x["path"]: x for x in E})
    p.write_text(json.dumps({"sources": list(old.values())}, indent=2) + "\n", encoding="utf-8")
