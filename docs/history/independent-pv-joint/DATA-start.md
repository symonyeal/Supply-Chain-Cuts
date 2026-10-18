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

PV and joint rate fits use the joint node roster, including Li-ion, before PV selects
its marginals. The fitting objective, numerical domain, country-year calibration and
duration-record rule are stated in MODEL for independent recomputation. Scenario shocks
use the minimum marginal among the selected sector's nodes of each country.

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

## Export-severity study (W2, 2026-10-16)

Bundle `results/severity-26ebd48`; protocol approved before acquisition, S1–S3 registered
at `aac556d`. BACI HS12 V202601 selected rows are frozen separately for 2012–2023.
The UN HS2007–HS2012 correspondence supplies verified one-to-one codes. The outcome is
exports in the first full calendar year after onset, relative to the preceding year
and surveyed, unrestricted exporters of the same HS6. It is not production.

| OECD measure | Isolated events | Treated countries | Export loss / baseline volume | Country-bootstrap 95% interval | Identification |
| --- | ---: | ---: | ---: | --- | --- |
| M1 export tax | 2 | 2 | −0.130681 | [−0.912677, 0.550011] | fewer than five events |
| M14 other export measures | 1 | 1 | −0.196687 | [−0.803798, 0.173337] | fewer than five; pretrend |
| M5 fiscal tax on exports | 1 | 1 | 0.041791 | [−0.243097, 0.311436] | fewer than five events |
| M3 quota | 0 | 0 | not estimable | — | no isolated event |
| M4 prohibition | 0 | 0 | not estimable | — | no isolated event |
| M6 licensing | 0 | 0 | not estimable | — | no isolated event |
| M3 or M4 | 0 | 0 | not estimable | — | no isolated event |

Negative loss means a relative export increase. Effects are unclipped changes in units
of each exporter's baseline volume; they can exceed one, so they are not physical loss
fractions. The balanced, equally weighted event estimator equals exporter-within-event
and year-within-event fixed effects (MODEL). Bootstrap: 2,000 country draws, seed 6;
valid draws are 1,713, 1,290 and 1,302 respectively for M1, M14 and M5. All have weak
inference (fewer than ten treated countries). M14's −2 pretrend coefficient is 6.779450,
interval [6.537103, 7.139638], excluding zero.

Sequential exclusions: 36 source records have HS12 codes outside the original selected
set; 74 are outside onset years 2014–2022; four national acts lack verified HS6 coverage.
After deduplication, 43 cohorts have incomplete or zero baseline volumes and 23 have
overlapping measure types. These counts have different units and must not be added
as if all were event counts. The 23 overlaps and their descriptive responses remain in
the bundle; they do not identify effects of a single measure. Tiny baselines can give
large normalized control growth and coefficients.

No type is identified under the registered rules. Every central and endpoint capacity
assignment therefore uses the explicitly assumed f = 1 fallback, including unestimated
marks. This applies to 100% of simulated onsets. The severity scenario consequently has
the same law as full outage; no empirical loss fraction has entered the capacity model.
The pooled measure mix for unexposed products and independence of type and duration are
scenario assumptions. Legal duration is not an observed outage duration.

| Network | Severity/full paired MC | Binomial 95% interval | Reduction, percentage points | 95% reduction interval, points |
| --- | ---: | --- | ---: | --- |
| Li-ion | 0.476000 | [0.469057, 0.482950] | 0 | [0, 0.018443] |
| PV | 0.248950 | [0.242969, 0.255004] | 0 | [0, 0.018443] |
| Joint | 0.202450 | [0.196900, 0.208087] | 0 | [0, 0.018443] |

Each uses 20,000 paired states, seed 7, alpha = 25%, h = sigma = 0. Central, low and high
assignments coincide samplewise with full loss; maximum shortfall monotonicity violation
is zero. These crude MC points are sampling diagnostics, not replacements for W1's
L-plus-residual estimates. Since the laws are identical here, the site reuses W1 for the
severity column and labels that equivalence; it does not clip the crude MC points to L.
In particular, Li-ion's paired MC interval misses exact L = 0.485681. The 2.74-SE
difference passes the registered four-SE comparison but is reported, not concealed.

## Natural hazards

No frozen site table has coordinates for capacity, so located capacity is 0% in every
layer, below the 70% threshold (`data/sites/coverage.json`). Natural hazards are therefore
a sensitivity scenario at fixed country-wide loss fractions 0.1, 0.25, 0.5 and 1, with
GDACS orange/red alert years per country as context; the headline uses policy onsets only.
