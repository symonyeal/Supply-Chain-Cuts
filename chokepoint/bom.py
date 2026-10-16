"""Xu et al. (2020), supplementary Tables 1, 4 and 23; physical conversions."""
import csv
from pathlib import Path


def bill(ncm=0.5, root=Path(".")):
    """Return kg/kWh for an explicit LFP/NCM622 mixture, with source rows."""
    if not 0 <= ncm <= 1:
        raise ValueError("NCM622 fraction must be in [0,1]")
    rows = list(csv.DictReader((root / "data/raw/xu2020/bom_mid_size_bev.csv").open()))
    b = {}
    for row in rows:
        if row["chemistry"] in ("LFP", "NCM622"):
            weight = ncm if row["chemistry"] == "NCM622" else 1 - ncm
            p = row["material"]
            b[p] = b.get(p, 0) + weight*float(row["kg_per_pack"])/float(row["pack_kwh"])
    energies = {x["chemistry"]: float(x["wh_per_kg"]) for x in csv.DictReader(
        (root / "data/raw/xu2020/specific_energy.csv").open())}
    # LiFePO4 and LiMO2 stoichiometry; atomic masses are stated conversion assumptions.
    lfp = {x["material"]: float(x["kg_per_pack"])/66 for x in rows
           if x["chemistry"] == "LFP"}
    ncm_b = {x["material"]: float(x["kg_per_pack"])/66 for x in rows
             if x["chemistry"] == "NCM622"}
    cam_lfp = lfp["Li"]*(6.94 + 55.845 + 30.974 + 4*15.999)/6.94
    cam_ncm = sum(ncm_b[x] for x in ("Li", "Ni", "Co", "Mn")) + ncm_b["Li"]*2*15.999/6.94
    pcam = sum(ncm_b[x]*(1 + 2*17.007/m) for x, m in
                (("Ni", 58.6934), ("Co", 58.9332), ("Mn", 54.938)))
    return {"kg_kwh": b, "ncm_fraction": ncm, "cam_kg_kwh": (1 - ncm)*cam_lfp + ncm*cam_ncm,
            "pcam_kg_kwh": ncm*pcam, "lce_kg_kwh": b["Li"]*5.323,
            "specific_energy_wh_kg": 1/((1 - ncm)/energies["LFP"] + ncm/energies["NCM622"]),
            "basis": "pack_BOM_and_pack_specific_energy_applied_to_cell_trade_scenario",
            "source": "Xu2020 SI Tables 1,4,23; stoichiometric conversion; unit yield assumption"}
