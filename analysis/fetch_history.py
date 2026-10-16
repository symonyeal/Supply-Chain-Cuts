"""Freeze BACI HS12 2012–2023 before W2 severity estimation (registered 2026-10-16)."""
import io
import json
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

from data.research.fetch_baci import ROOT, OUT, freeze, read


def main():
    u = "https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_HS12_V202601.zip"
    with urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=30) as r:
        m = int(r.headers["Content-Length"])
    with read(u, m-65536, m-1) as r:
        b = r.read()
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        X = [x for x in z.infolist() if any(f"Y{t}_" in x.filename for t in range(2012, 2024))]
    assert len(X) == 12
    p = ROOT / "data/research/manifest.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    known = {x["archive_member"] for x in d["sources"] if x.get("archive_member")}
    X = [x for x in X if x.filename not in known]
    OUT.mkdir(parents=True, exist_ok=True)

    def acquire(x):
        e = freeze(u, x, m-65536, "12", retrieved="2026-10-16")
        print(e["path"], e["bytes"], flush=True)
        return e

    with ThreadPoolExecutor(3) as pool:
        E = list(pool.map(acquire, X))
    d["sources"] += E
    p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
