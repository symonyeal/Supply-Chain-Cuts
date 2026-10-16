# Data

The 2024 network as built by `chokepoint/net.py` at revision `60eb399`; numbers are read
from `results/liion-60eb399/network.json` and `data_checks.json` (lock digest
`7908f1c27af4…`). Sources, URLs and licences are in `SOURCES.lock` and
[Research](RESEARCH.md). Nothing below was rescaled to make sources agree.

## Nodes and bases

A node is a (country, product) pair. Origins below 1% of their layer are excluded; the
retained share of each layer is its coverage. Li-ion: 111 nodes, 73 on a production
basis, 20 on trade and 18 imputed. PV: 15 nodes, 4 production and 11 trade.

| Basis | Source | Layers |
| --- | --- | --- |
| production | USGS MCS 2026 (2024 mine output; refined Cu; Al smelters) | mine Li, Co, Ni, Mn; natural graphite; refined Cu; aluminium |
| production | USGS MYB 2023 Table 8 (2023 refinery output, t Co) | refined Co, all origins |
| production | MIIT 2024 national totals | China cells, CAM, AAM, battery-grade Li2CO3 and LiOH·H2O; China PV stages |
| production | Cochilco 2024, `Hoja1!AD21` | Chile Li2CO3 |
| trade | CEPII BACI HS12 2024 exports (HS22 for PV) | other Li chemicals, refined Ni, other cells and PV stages |
| imputed | Xu et al. 2020 BOM × cell output | pCAM everywhere; CAM and AAM outside China; synthetic graphite added to natural |

Conversions: Li 5.323 t LCE per t Li; LiOH·H2O 0.880 t LCE per t (GB/T 26008-2020 defines
battery grade as the monohydrate; MIIT does not state the form). Cells: pack specific
energy of the stated LFP/NCM622 mix applied to BACI accumulator mass. PV: China's export
GW over export tonnes calibrates each non-China stage; polysilicon uses 2.0 g Si/Wp
(Fraunhofer ISE 2026, p. 8).

## Layers

Capacities are measured in years of requirement: S is a layer's retained output divided
by what the demand target requires of it. Demand equals the retained final output scaled
to what the undisrupted chain delivers (Li-ion 1.000; PV 0.991, because retained PV cells
fall 0.9% short of retained modules), so the undisrupted network has no shortfall.

| Layer | Nodes | Coverage | S | Top origin | HHI | Bases |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| cell | 6 | 0.952 | 1.000 | CHN 0.869 | 0.757 | 1 production, 5 trade |
| pcam | 6 | 0.952 | 1.000 | CHN 0.869 | 0.757 | 6 imputed |
| cam | 5 | 0.956 | 1.339 | CHN 0.902 | 0.815 | 1 production, 4 imputed |
| graphite | 7 | 0.893 | 1.431 | CHN 0.765 | 0.588 | 2 production, 5 imputed |
| aam | 4 | 0.949 | 1.443 | CHN 0.910 | 0.828 | 1 production, 3 imputed |
| refined_co | 7 | 0.976 | 1.545 | CHN 0.817 | 0.674 | 7 production |
| mine_li | 7 | 0.995 | 1.570 | AUS 0.371 | 0.235 | 7 production |
| li_carbonate | 3 | 0.988 | 1.732 | CHN 0.748 | 0.598 | 2 production, 1 trade |
| refined_ni | 14 | 0.944 | 2.013 | NOR 0.149 | 0.085 | 14 trade |
| mine_co | 8 | 0.976 | 2.523 | COD 0.769 | 0.608 | 8 production |
| mine_ni | 8 | 0.998 | 9.980 | IDN 0.680 | 0.482 | 8 production |
| refined_cu | 16 | 0.993 | 24.659 | CHN 0.490 | 0.267 | 16 production |
| aluminium | 12 | 1.000 | 35.681 | CHN 0.665 | 0.456 | 12 production |
| mine_mn | 8 | 1.000 | 164.873 | ZAF 0.429 | 0.273 | 8 production |
| pv_cell | 2 | 0.972 | 1.000 | CHN 0.929 | 0.865 | 1 production, 1 trade |
| module | 6 | 0.945 | 1.009 | CHN 0.805 | 0.654 | 1 production, 5 trade |
| wafer | 4 | 0.981 | 1.139 | CHN 0.947 | 0.897 | 1 production, 3 trade |
| polysilicon | 3 | 0.982 | 1.391 | CHN 0.938 | 0.882 | 1 production, 2 trade |

Upstream layers are fully available to batteries: the model has no competing non-battery
demand. This is the reason S is large for Cu, Al, Mn and Ni, and it makes upstream cuts
harder to reach than in reality. pCAM, and CAM and AAM outside China, are imputed from cell
output, so their shares mirror the cell layer; a cut on an imputed node is labelled as such.

## Reconciliations

| Check | Result |
| --- | --- |
| MIIT cell parts vs total | 84 + 260 + 826 = 1,170 GWh, equal |
| China cells: BACI export proxy vs MIIT | 362 GWh vs 1,170 GWh (0.31) |
| China refined Co: exports vs MYB | 5.3 kt vs 147 kt (0.036) |
| China Li2CO3: exports vs MIIT LCE | 3.8 kt vs 987 kt (0.004) |
| Chile Li2CO3: exports vs Cochilco | 240.9 kt vs 250.6 kt (0.96) |
| Refined Co exports above MYB output | AUS 1.56, BEL 2.39, CAN 1.73, FRA 6.28, IDN 6.17, JPN 1.09, MAR 1.32, RUS 5.76, ZAF 5.93 (ratio) |
| Comtrade China tariff lines vs BACI HS6 | not measured: tariff lines not fetched (optional key not supplied) |
| BGS refinery statistics | not used: licence unresolved |
| BACI rows without mass | HS12 863, HS22 1,439; excluded from sums, not zero |
| USGS rows unparsed | aggregates and withheld values only (test `test_every_country_row_mapped`) |

The export proxy understates integrated producers by one to three orders of magnitude for
China's midstream; test B2 reruns the cuts on it. HS 810520 mixes intermediates with metal,
so export mass above refinery output is expected and is why refined Co uses MYB.

Re-export flags (test B1): a trade-basis node whose country imports at least what it
exports of the same codes. Flagged: DEU, KOR, USA cells; CHN, DEU, FRA, JPN, NLD refined Ni.

## Events

`chokepoint/events.py` derives node-year onsets from the frozen OECD Inventory records
(HS2007 mapped to products in `data/events/product_map.json`) and national acts
(`data/events/acts.yaml`). Exposure is a surveyed (country, commodity, year) in the OECD
coverage table; unsurveyed node-years are missing, never zero. On the 111 Li-ion nodes,
884 node-years are observed and 61 contain an onset. Cells, CAM, pCAM and AAM have no
exposure (the OECD survey covers raw materials only), so their rates borrow the
all-product prior. The derivation reproduces the research table
`observed_node_years.csv` exactly except one onset it missed: Zimbabwe lithium ore, 2022
(SI 213/2022, effective 2022-12-16).

Spell lengths come from the records that create an onset, i.e. that fall in a surveyed
node-year; they bin onto (3, 6, 12) months as 4, 3 and 169, and 8 censored spells shorter
than six months are reported and unused. Durations are legal-measure lengths, not observed
outages. The independent recomputation counted every in-window record instead and found 170
in the 12-month bin; the extra record is a 2016 Viet Nam lithium export tax
(OECD-a43d88b43b745c9f) in an unsurveyed node-year. It changes L by 8.6e-5.

## Natural hazards

No frozen site table has coordinates for capacity, so located capacity is 0% in every
layer, below the 70% threshold (`data/sites/coverage.json`). Natural hazards are therefore
a sensitivity scenario at fixed country-wide loss fractions 0.1, 0.25, 0.5 and 1, with
GDACS orange/red alert years per country as context; the headline uses policy onsets only.
