"""A labelled 2024 country–product network from frozen production and trade rows.

Units. Node output is physical (kt, GWh, GW) in `annual`. Let R_f be the demand target of
final f and R_p = Σ_q a[p,q] R_q the annual requirement of p. The LP measures p in units
of R_p: capacity u_v = annual_v/(12 R_p), coefficient a'[p,q] = a[p,q] R_q/R_p, demand 1/12
per month. The rescaling is diagonal, hence exact; S_p = Σ_v annual_v / R_p is the supply
ratio of layer p in years of requirement per year.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from chokepoint.bom import bill
from chokepoint.recourse import matrices

HS = {"li_carbonate": ["283691"], "refined_ni": ["750210"], "refined_co": ["810520"],
      "synthetic_graphite": ["380110"], "cell": ["850760"], "polysilicon": ["280461"],
      "wafer": ["381800"], "pv_cell": ["854142"], "module": ["854143"]}
PV = ("polysilicon", "wafer", "pv_cell", "module")     # HS22 only (design §7)
LCE_LIOH = 73.891/(2*41.964)    # t Li2CO3 per t LiOH·H2O (GB/T 26008-2020 battery grade)
LCE_LI = 5.323                  # t Li2CO3 per t Li


def _baci(root):
    country_rows = list(csv.DictReader((root / "data/raw/baci/country_codes_V202601.csv").open()))
    countries = {int(x["country_code"]): x["country_iso3"] for x in country_rows}
    exports, imports, missing = {}, {}, {}
    for hs in ("12", "22"):
        E, I, gaps = defaultdict(float), defaultdict(float), 0
        for x in csv.DictReader((root / f"data/raw/baci/BACI_HS{hs}_Y2024_V202601_selected.csv")
                                .open()):
            if not x["q"]:
                gaps += 1
                continue
            E[countries[int(x["i"])], x["k"]] += float(x["q"])
            I[countries[int(x["j"])], x["k"]] += float(x["q"])
        exports[hs], imports[hs], missing[hs] = E, I, gaps
    return country_rows, countries, exports, imports, missing


def _usgs(root, names):
    chapters = {"LITHIUM": "mine_li", "COBALT": "mine_co", "NICKEL": "mine_ni",
                "GRAPHITE (NATURAL)": "graphite", "MANGANESE": "mine_mn",
                "COPPER": "refined_cu", "ALUMINUM": "aluminium"}
    prod, unparsed = {}, []
    for x in csv.DictReader((root / "data/raw/usgs/MCS2026_Commodities_Data.csv")
                            .open(encoding="cp1252")):
        if (x["Year"] != "2024" or not x["Section"].startswith("World")
                or x["Statistics"] != "Production" or x["MCS chapter"] not in chapters):
            continue
        if x["MCS chapter"] == "COPPER" and not x["Statistics_detail"].startswith("Refinery"):
            continue
        country = names.get(x["Country"].casefold())
        v = x["Value"].replace(",", "").strip()
        if not country:
            unparsed.append({"country": x["Country"], "chapter": x["MCS chapter"],
                             "value": v, "reason": "aggregate_or_unmapped"})
            continue
        try:
            value = float(v)
        except ValueError:
            unparsed.append({"country": country, "chapter": x["MCS chapter"],
                             "value": v, "reason": "withheld_or_non_numeric"})
            continue
        prod[country, chapters[x["MCS chapter"]]] = value*(
            1000 if x["Unit"] == "thousand metric tons" else 1)
    return prod, unparsed


class _Nodes:
    """The country-product nodes of one network, filled from the frozen source tables.

    INPUT  root: input tree; B: bill of materials; exports[HS rev][country, HS6]: BACI tonnes;
           iso3: origins; observed: production basis (statistics override the export proxies);
           exclude: (country, product) pairs never admitted.
    nodes[c, p] holds annual output with its basis, unit, source and note; trade(c, p) is the
    BACI export proxy in kt.
    """

    def __init__(self, root, B, exports, iso3, observed, exclude):
        self.root, self.B, self.exports, self.iso3 = root, B, exports, iso3
        self.observed, self.exclude, self.nodes = observed, exclude, {}
        self.miit = {x["product"]: float(x["value"]) for x in csv.DictReader(
            (root / "data/raw/miit/production_2024.csv").open()) if x["statistic"] == "production"}

    def put(self, c, p, annual, label, unit, source, note=""):
        """Set node (c, p) unless it has no output or is excluded."""
        if annual > 0 and (c, p) not in self.exclude:
            self.nodes[c, p] = {"country": c, "product": p, "annual": annual, "basis": label,
                                "unit": unit, "source": source, "note": note}

    def trade(self, c, p, scale=1e-3):
        return scale*sum(self.exports["22" if p in PV else "12"].get((c, hs), 0) for hs in HS[p])

    def fill(self, sector, ncm, prod, japan_voltage, eu_sold):
        """Put the origins of `sector`: Li-ion (USGS output, BACI proxies, production overrides,
        BOM-imputed midstream) and PV; prod[c, p] is USGS output in t."""
        if sector in ("liion", "joint"):
            self._origins(prod)
            if self.observed:
                self._observed(japan_voltage, eu_sold)
            else:
                for c in self.iso3:
                    self.put(c, "refined_co", self.trade(c, "refined_co"), "trade", "kt",
                             "BACI HS12 2024 810520", "Export proxy; HS810520 mixes intermediates")
            self._midstream(ncm)
        if sector in ("pv", "joint"):
            self._pv()

    def _origins(self, prod):
        """Li-ion origins: USGS 2024 output and BACI export proxies, with synthetic graphite
        exports added to natural graphite."""
        put, trade = self.put, self.trade
        for (c, p), value in prod.items():
            put(c, p, value/1000, "production", "kt", "USGS MCS2026, 2024 production")
        for c in self.iso3:
            put(c, "li_carbonate", trade(c, "li_carbonate"), "trade", "kt",
                "BACI HS12 2024 283691", "Export proxy, kt Li2CO3")
            put(c, "refined_ni", trade(c, "refined_ni"), "trade", "kt",
                "BACI HS12 2024 750210", "Export proxy; omits domestically absorbed metal")
            put(c, "cell", trade(c, "cell", self.B["specific_energy_wh_kg"]/1e6), "trade", "GWh",
                "BACI HS12 2024 850760", "Pack Wh/kg applied to mixed cell/pack exports")
            synthetic = trade(c, "synthetic_graphite")
            if synthetic:
                put(c, "graphite",
                    self.nodes.get((c, "graphite"), {}).get("annual", 0) + synthetic,
                    "imputed", "kt", "USGS natural + BACI 380110 synthetic exports",
                    "Substitution assumed; synthetic exports include non-anode use")

    def _observed(self, japan_voltage, eu_sold):
        """Production statistics that override the export proxies on the production basis: USGS
        MYB cobalt, MIIT China, Cochilco Chile and the optional METI and Eurostat variants."""
        root, put, miit = self.root, self.put, self.miit
        for x in csv.DictReader((root / "data/raw/usgs/myb2023_cobalt_refinery.csv").open()):
            if x["value"]:
                put(x["iso3"], "refined_co", float(x["value"])/1000, "production", "kt",
                    "USGS MYB 2023 Table 8", f"2023 refinery output, {x['qualifier']}")
        put("CHN", "cell", miit["li_ion_cell"], "production", "GWh", "MIIT 2024")
        put("CHN", "li_carbonate", (miit["battery_grade_lithium_carbonate"]
            + miit["battery_grade_lithium_hydroxide"]*LCE_LIOH)/1000, "production", "kt",
            "MIIT 2024", "Battery-grade carbonate + LiOH·H2O as LCE")
        for x in csv.DictReader((root / "data/raw/cochilco/lithium_chemicals_2024.csv")
                                .open()):
            if x["product_source_label"] == "CARBONATO DE LITIO":
                put("CHL", "li_carbonate", float(x["value"])/1000, "production", "kt",
                    "Cochilco Hoja1 AD21", "Carbonate only; sulfate excluded")
        if japan_voltage is not None:
            J = list(csv.DictReader((root / "data/raw/meti/liion_2024.csv").open()))
            q = sum(float(x["production_kAh"]) for x in J)
            put("JPN", "cell", q*japan_voltage/1e6, "imputed", "GWh",
                "METI 2024 h2daa2024k, items 0108/0109",
                f"Sealed Li-ion production kAh times assumed {japan_voltage} V; "
                "not installed capacity; scope excludes unreported battery categories")
        if eu_sold:
            E = json.loads((root / "data/raw/supplement/reconciliation.json").read_text())
            q = E['eurostat']['201343Z1']['DE']['PRODQNT']
            put("DEU", "li_carbonate", float(q)/1e6, "imputed", "kt",
                "Eurostat Prodcom 2024 201343Z1 sold quantity",
                "Sold-output proxy, both purity grades; not actual production or battery grade")

    def _midstream(self, ncm):
        """Cathode, anode and precursor nodes imputed from each cell origin's output by the BOM;
        China's cathode and anode come from MIIT on the production basis."""
        put, miit, B = self.put, self.miit, self.B
        for c, output in [(c, x["annual"]) for (c, p), x in list(self.nodes.items())
                          if p == "cell"]:
            china = c == "CHN" and self.observed
            put(c, "cam",
                miit["cathode_active_material"]/1000 if china else output*B["cam_kg_kwh"],
                "production" if china else "imputed", "kt", "MIIT 2024" if china else "BOM x cell")
            put(c, "aam", miit["anode_active_material"]/1000 if china else output*B["kg_kwh"][
                "Graphite"], "production" if china else "imputed", "kt",
                "MIIT 2024" if china else "BOM x cell")
            if ncm:
                put(c, "pcam", output*B["pcam_kg_kwh"], "imputed", "kt", "BOM x cell",
                    "No pCAM production statistic; tariff-line coverage incomplete")

    def _pv(self):
        """PV origins: BACI HS22 exports scaled to MIIT China GW, with MIIT China production on
        the production basis."""
        put, miit, exports = self.put, self.miit, self.exports
        gw = {"wafer": 60.9, "pv_cell": 57.5, "module": 238.8}     # MIIT China exports, GW
        for p in PV:
            hs = HS[p][0]
            factor = 1e-3 if p == "polysilicon" else gw[p]/exports["22"]["CHN", hs]
            for c in self.iso3:
                put(c, p, exports["22"].get((c, hs), 0)*factor, "trade",
                    "kt" if p == "polysilicon" else "GW", "BACI HS22 2024 / MIIT China exports",
                    "HS22 only; silicon and wafer codes include semiconductor products")
            if self.observed:
                key = "pv_cell" if p == "pv_cell" else "pv_" + p
                put("CHN", p, miit[key]/1000 if p == "polysilicon" else miit[key], "production",
                    "kt" if p == "polysilicon" else "GW", "MIIT 2024",
                    "Strict lower bound" if p == "polysilicon" else "")


def _arcs(sector, ncm, B):
    """Physical coefficients a[p, q]: units of p per unit of q."""
    a = {}
    if sector in ("liion", "joint"):
        a.update({("mine_li", "li_carbonate"): 1/LCE_LI,
                  ("li_carbonate", "cam"): B["lce_kg_kwh"]/B["cam_kg_kwh"],
                  ("graphite", "aam"): 1.0, ("cam", "cell"): B["cam_kg_kwh"],
                  ("aam", "cell"): B["kg_kwh"]["Graphite"],
                  ("refined_cu", "cell"): B["kg_kwh"]["Cu"],
                  ("aluminium", "cell"): B["kg_kwh"]["Al"]})
        if ncm:
            a.update({("pcam", "cam"): B["pcam_kg_kwh"]/B["cam_kg_kwh"],
                      ("mine_co", "refined_co"): 1.0, ("mine_ni", "refined_ni"): 1.0})
            for p, metal in (("refined_co", "Co"), ("refined_ni", "Ni"), ("mine_mn", "Mn")):
                a[p, "pcam"] = B["kg_kwh"][metal]/B["pcam_kg_kwh"]
    if sector in ("pv", "joint"):
        a.update({("polysilicon", "wafer"): 2.0, ("wafer", "pv_cell"): 1.0,
                  ("pv_cell", "module"): 1.0})    # Fraunhofer ISE 2026 p. 8: 2.0 g Si/Wp
    return a


def _shares(nodes, used, cutoff):
    """Layer totals; the origins at or above the cutoff share of a used layer, sorted by
    (product, country), with the coverage they retain; HHI and top share over all origins."""
    totals = defaultdict(float)
    for (_, p), x in nodes.items():
        totals[p] += x["annual"]
    hhi, top = defaultdict(float), defaultdict(float)       # over all origins, before cutoff
    for (_, p), x in nodes.items():
        hhi[p] += (x["annual"]/totals[p])**2
        top[p] = max(top[p], x["annual"]/totals[p])
    selected, coverage = [], defaultdict(float)
    for x in sorted(nodes.values(), key=lambda x: (x["product"], x["country"])):
        x["share"] = x["annual"]/totals[x["product"]]
        if x["share"] >= cutoff and x["product"] in used:
            selected.append(x)
            coverage[x["product"]] += x["share"]
    return (totals, selected, coverage, {p: hhi[p] for p in used if p in hhi},
            {p: top[p] for p in used if p in top})


def _requirement(selected, finals, order, a):
    """Requirements R, supply ratios S and demand scales; the second pass sets demand to the
    undisrupted achievable output."""
    scale = {f: 1.0 for f in finals}
    for _ in range(2):
        R = {f: scale[f]*sum(x["annual"] for x in selected if x["product"] == f) for f in finals}
        for p in order:                               # R_p = Σ_q a[p,q] R_q, top-down
            R[p] = sum(x*R[q] for (r, q), x in a.items() if r == p)
        S = {p: sum(x["annual"] for x in selected if x["product"] == p)/R[p] for p in R}
        scale = {f: scale[f]*min(1.0, *(S[p] for p in _closure(f, a))) for f in finals}
    return R, S, scale


def _flows(iso3, trade, imports):
    """Nonzero exports and all imports in kt, keyed "country:product"."""
    return ({f"{c}:{p}": trade(c, p) for c in iso3 for p in HS if trade(c, p)},
            {f"{c}:{p}": 1e-3*sum(imports["22" if p in PV else "12"].get((c, hs), 0)
                                  for hs in HS[p]) for c in iso3 for p in HS})


def build(root=Path("."), sector="liion", ncm=0.5, cutoff=0.01, basis="production",
          exclude=(), japan_voltage=None, eu_sold=False):
    """Build the physical network and its requirement-unit capacities.

    INPUT  sector ... liion | pv | joint;  ncm ... NCM622 fraction of the cathode mix
           cutoff ... origins below this share of their layer are excluded and reported
           basis .... production (MIIT, Cochilco, MYB override export proxies) | trade
           exclude .. (country, product) pairs removed before demand is set (test B1)
           japan_voltage .. optional METI supplement, assumed nominal V (not observed)
           eu_sold .. optional German Prodcom sold-carbonate proxy (imputed)
    OUTPUT nodes with annual, basis, share and capacity; physical a; requirements R;
           supply ratios S; coverage of each layer by the retained nodes.
    Demand is retained final output scaled to what the undisrupted chain delivers
    (demand_scale = min(1, min S_p over the chain), recorded), so phi(0) = 0.
    """
    if sector not in ("liion", "pv", "joint") or not 0 <= cutoff < 1:
        raise ValueError("sector in liion,pv,joint and 0 <= cutoff < 1 required")
    if basis not in ("production", "trade"):
        raise ValueError("basis in production,trade required")
    B = bill(ncm, root)
    country_rows, countries, exports, imports, missing = _baci(root)
    names = {x["country_name"].casefold(): x["country_iso3"] for x in country_rows}
    names.update({"congo (kinshasa)": "COD", "korea, republic of": "KOR",
                  "korea, north": "PRK", "russia": "RUS", "turkey": "TUR",
                  "vietnam": "VNM", "côte d’ivoire": "CIV", "côte d'ivoire": "CIV",
                  "united states": "USA", "tanzania": "TZA", "bolivia": "BOL",
                  "burma": "MMR", "laos": "LAO"})
    prod, unparsed = _usgs(root, names)
    iso3 = sorted(set(countries.values()))
    origins = _Nodes(root, B, exports, iso3, basis == "production", exclude)
    origins.fill(sector, ncm, prod, japan_voltage, eu_sold)
    a = _arcs(sector, ncm, B)
    used = {p for edge in a for p in edge}
    totals, selected, coverage, hhi, top = _shares(origins.nodes, used, cutoff)
    finals = [p for p in ("cell", "module") if p in totals]
    order = sorted(used - set(finals), key=lambda p: _depth(p, a))
    R, S, scale = _requirement(selected, finals, order, a)
    for x in selected:
        x["capacity"] = x["annual"]/(12*R[x["product"]])
    exported, imported = _flows(iso3, origins.trade, imports)
    return {"sector": sector, "nodes": selected, "a": [[p, q, x] for (p, q), x in a.items()],
            "requirement": R, "supply_ratio": S, "finals": finals, "demand_scale": scale,
            "annual_totals": dict(totals), "coverage": dict(coverage), "cutoff": cutoff,
            "hhi": hhi, "top_share": top,
            "ncm": ncm, "capacity_basis": basis, "excluded": sorted(map(list, exclude)),
            "bom": B, "missing_baci_quantities": missing, "unparsed_usgs": unparsed,
            "exports": exported, "imports": imported}


def reexport_flags(network):
    """Trade-basis nodes whose country imports at least what it exports of the same HS codes.

    Such exports cannot be shown to be domestic production (test B1)."""
    out = []
    for x in network["nodes"]:
        key = f"{x['country']}:{x['product']}"
        if x["basis"] == "trade" and network["imports"].get(key, 0) >= network["exports"][key]:
            out.append([x["country"], x["product"], network["exports"][key],
                        network["imports"][key]])
    return out


def _closure(f, a):
    """f and every product upstream of f."""
    return {f}.union(*(_closure(p, a) for (p, q) in a if q == f))


def _depth(p, a):
    """Length of the longest path from p to a final product in the acyclic product graph."""
    return max([0, *(1 + _depth(q, a) for (r, q) in a if r == p)])


def blocks(T=24, sigma=0.0, L=6.0, durations=(3, 6, 12)):
    """Block ends on which capacity and demand are constant: disruption ends, ramp months, T."""
    ramp = range(1, min(T, int(np.ceil(L))) + 1) if sigma else ()
    return sorted({T, *(D for D in durations if D < T), *ramp})


def model(network, T=24, h=0.0, sigma=0.0, L=6.0, durations=(3, 6, 12), aggregate=True):
    """Transcribe the network into the T-month recourse LP in requirement units."""
    R = network["requirement"]
    return matrices([(x["country"], x["product"]) for x in network["nodes"]],
                    [x["capacity"] for x in network["nodes"]],
                    {(p, q): x*R[q]/R[p] for p, q, x in network["a"]},
                    {p: [1/12]*T for p in network["finals"]}, h, sigma, L,
                    aggregate=aggregate, ends=blocks(T, sigma, L, durations))
