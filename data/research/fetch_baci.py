"""Freeze exact BACI rows for the supply chain, with member digests."""

import hashlib
import io
import json
import struct
import urllib.request
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/raw/baci"
K = {"250410", "250490", "260200", "260300", "260400", "260500", "260600",
     "282010", "282090", "282200", "282520", "283691", "283324", "283329",
     "284190", "284290", "285390", "380110", "740311", "750210", "760110",
     "810520", "850760", "280461", "381800", "854142", "854143"}


def read(u, a, b):
    """Read inclusive byte range [a, b] from an HTTP resource."""
    q = urllib.request.Request(u, headers={"Range": f"bytes={a}-{b}"})
    return urllib.request.urlopen(q, timeout=180)


def freeze(u, x, offset, hs, retrieved="2026-10-15"):
    """Freeze one archive member, selecting original rows by HS6 only."""
    a = offset + x.header_offset
    with read(u, a, a + 29) as r:
        h = struct.unpack("<4s5H3I2H", r.read())
    a += 30 + h[-2] + h[-1]
    z = zlib.decompressobj(-15)
    digest = hashlib.sha256()
    subset = x.filename.startswith("BACI_")
    name = x.filename.removesuffix(".csv") + "_selected.csv" if subset else x.filename
    p = OUT / name
    pending = b""
    n, size, crc = 0, 0, 0
    with read(u, a, a + x.compress_size - 1) as r, p.open("wb") as f:
        while b := r.read(1024 * 1024):
            b = z.decompress(b) if x.compress_type == zipfile.ZIP_DEFLATED else b
            digest.update(b)
            size, crc = size + len(b), zlib.crc32(b, crc)
            if subset:
                rows = (pending + b).split(b"\n")
                pending = rows.pop()
                for line in rows:
                    if n == 0 or line.split(b",")[3].strip(b'"').decode() in K:
                        f.write(line + b"\n")
                    n += 1
            else:
                f.write(b)
        if pending and pending.split(b",")[3].strip(b'"').decode() in K:
            f.write(pending)
    if size != x.file_size or crc != x.CRC:
        raise ValueError(f"Archive member length/CRC mismatch: {x.filename}")
    return {"path": p.relative_to(ROOT).as_posix(), "url": u,
            "retrieved": retrieved, "license": "Etalab-2.0",
            "license_url": "https://www.cepii.fr/DATA_DOWNLOAD/baci/doc/baci_webpage.html",
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size,
            "archive_member": x.filename, "archive_member_sha256": digest.hexdigest(),
            "transform": {"selection": {"k": sorted(K)}} if subset else None}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    E = []
    for hs in ("12", "22"):
        u = f"https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_HS{hs}_V202601.zip"
        r = urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=30)
        m = int(r.headers["Content-Length"])
        with read(u, m - 65536, m - 1) as r:
            b = r.read()
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            X = z.infolist()
            offset = m - 65536
            for x in X:
                metadata = x.filename.endswith(".csv") and not x.filename.startswith("BACI_")
                if "Y2024" in x.filename or metadata:
                    e = freeze(u, x, offset, hs)
                    E.append(e)
                    print(e["path"], e["bytes"], flush=True)
    p = ROOT / "data/research/manifest.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["sources"] += E
    p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
