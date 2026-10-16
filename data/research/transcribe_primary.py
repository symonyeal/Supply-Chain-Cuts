"""Freeze primary numerical transcriptions and deterministic licensed extracts."""

import csv
import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw"
SI = ("https://media.springernature.com/original/springer-static/esm/"
      "art%3A10.1038%2Fs43246-020-00095-x/MediaObjects/43246_2020_95_MOESM1_ESM.pdf")
LI = ("https://www.miit.gov.cn/jgsj/dzs/gzdt/art/2025/"
      "art_dc20a4d4b3a74dcf91ac1b212f87bbfc.html")
PV = ("https://www.miit.gov.cn/gyhxxhb/jgsj/dzxxs/dzjc/art/2025/"
      "art_da51f7f47c75477ea1fa6732155536db.html")


def write(name, rows, url, license_name, note):
    """Freeze records, their source and the numerical transformation."""
    p = RAW / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return {"path": p.relative_to(ROOT).as_posix(), "url": url,
            "retrieved": "2026-10-15", "license": license_name,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size,
            "transform": note}


if __name__ == "__main__":
    E = []
    C = ["LFP", "NCA", "NCM111", "NCM523", "NCM622", "NCM622-Si", "NCM811-Si", "NCM955-Si"]
    M = {
        "Li": [6.62, 6.84, 9.43, 9.14, 7.94, 8.06, 7.49, 6.72],
        "Ni": [0, 44.26, 23.18, 33.71, 35, 35.73, 44.26, 44.51],
        "Co": [0, 8.33, 23.27, 13.54, 11.71, 11.96, 5.55, 2.61],
        "Mn": [0, 0, 21.70, 18.93, 10.92, 11.15, 5.18, 2.32],
        "Al": [106.87, 83.41, 87.69, 86.68, 84.12, 80.35, 78.98, 77.11],
        "Cu": [56.33, 49.16, 49.70, 49.17, 48.54, 49.08, 48.58, 48.03],
        "Graphite": [78.84, 70.93, 72.79, 71.87, 70.24, 47.39, 46.55, 45.55],
        "Si": [0, 0, 0, 0, 0, 4.69, 4.60, 4.51],
    }
    rows = [{"chemistry": c, "material": m, "kg_per_pack": a[i], "pack_kwh": 66,
             "source_table": 23, "pack_source_table": 1, "pdf_page": 42, "source_url": SI}
            for m, a in M.items() for i, c in enumerate(C)]
    E.append(write("xu2020/bom_mid_size_bev.csv", rows, SI, "CC-BY-4.0",
                   "Numerical transcription: SI Tables 1 and 23; mid-size BEV, pack level."))
    rows = [{"chemistry": c, "wh_per_kg": x, "source_table": 4, "pdf_page": 31,
             "basis": "mid-size BEV pack", "source_url": SI}
            for c, x in zip(C, [129, 178, 160, 163, 174, 186, 193, 202], strict=True)]
    E.append(write("xu2020/specific_energy.csv", rows, SI, "CC-BY-4.0",
                   "Numerical transcription: SI Table 4; pack-specific energy, not bare cell."))
    A = [
        ("li_ion_cell", "production", 1170, "GWh", "reported", LI),
        ("li_ion_consumer_cell", "production", 84, "GWh", "reported", LI),
        ("li_ion_storage_cell", "production", 260, "GWh", "reported", LI),
        ("li_ion_traction_cell", "production", 826, "GWh", "reported", LI),
        ("cathode_active_material", "production", 3100000, "tonnes", "approximate", LI),
        ("anode_active_material", "production", 2000000, "tonnes", "approximate", LI),
        ("separator", "production", 21000000000, "m2", "approximate", LI),
        ("electrolyte", "production", 1300000, "tonnes", "approximate", LI),
        ("battery_grade_lithium_carbonate", "production", 670000, "tonnes", "reported", LI),
        ("battery_grade_lithium_hydroxide", "production", 360000, "tonnes", "reported", LI),
        ("pv_polysilicon", "production", 1820000, "tonnes", "strict_lower_bound", PV),
        ("pv_wafer", "production", 753, "GW", "reported", PV),
        ("pv_cell", "production", 654, "GW", "reported", PV),
        ("pv_module", "production", 588, "GW", "reported", PV),
        ("pv_wafer", "export", 60.9, "GW", "approximate", PV),
        ("pv_cell", "export", 57.5, "GW", "approximate", PV),
        ("pv_module", "export", 238.8, "GW", "approximate", PV),
    ]
    rows = [{"country": "China", "iso3": "CHN", "year": 2024, "product": p,
             "statistic": s, "value": v, "unit": u, "qualifier": q, "source_url": url,
             "published": "2025-02-27",
             "basis": "production" if s == "production" else "trade"}
            for p, s, v, u, q, url in A]
    E.append(write("miit/production_2024.csv", rows, LI,
                   "Numerical-facts; no source open license stated",
                   "Factual numerical transcription from two MIIT releases; row-specific URLs. "
                   "Source basis: listed firms plus association estimates; not nameplate."))
    source = RAW / "cochilco/production_1996_2025.xlsx"
    s = load_workbook(source, data_only=True).active
    rows = []
    for r in s.iter_rows():
        if r[0].value and "LITIO" in str(r[0].value):
            rows.append({"country": "Chile", "iso3": "CHL", "year": 2024,
                         "product_source_label": r[0].value.strip(), "value": r[29].value,
                         "unit": "tonnes", "worksheet": s.title, "cell": r[29].coordinate,
                         "basis": "production"})
    url = ("https://www.cochilco.cl/web/download/140/"
           "estadisticas-estadisticas-de-la-mineria-no-metalica/16945/"
           "produccion-mineria-no-metalica-1996-2025.xlsx")
    E.append(write("cochilco/lithium_chemicals_2024.csv", rows, url,
                   "Numerical-facts; no source open license stated",
                   "Exact cell extraction; Hoja1 column AD, tonnes of chemical compound."))
    url = ("https://www.ise.fraunhofer.de/content/dam/ise/de/documents/"
           "publications/studies/Photovoltaics-Report.pdf")
    rows = [{"year": 2024, "product": "pv_polysilicon", "value": 2.0,
             "unit": "g/Wp", "qualifier": "approximate", "pdf_page": 8,
             "published": "2026-07-14", "source_url": url}]
    E.append(write("fraunhofer/silicon_usage_2024.csv", rows, url,
                   "Numerical-fact; citation required by source",
                   "Numerical transcription, p8: silicon usage; not complete module mass."))
    p = ROOT / "data/research/manifest.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    old = {x["path"]: x for x in d["sources"]}
    old.update({x["path"]: x for x in E})
    p.write_text(json.dumps({"sources": list(old.values())}, indent=2) + "\n", encoding="utf-8")
    for x in E:
        print(x["path"], x["bytes"])
