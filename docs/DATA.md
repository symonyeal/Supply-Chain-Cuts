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

### Exact reference construction for independent reproduction

These definitions specify the legacy fixed-mix network; they do not supply computed
node capacities or shortfalls. Let nu = 0.5 be the NCM622 share by pack kWh. Let b_L[m]
and b_N[m] be Xu's LFP and NCM622 material kilograms per pack divided by 66 kWh. Set
b[m] = (1−nu)b_L[m] + nu b_N[m]. Atomic masses used as conversion assumptions are
Li 6.94, Fe 55.845, P 30.974, O 15.999, Ni 58.6934, Co 58.9332, Mn 54.938;
OH has mass 17.007. Then, in kg/kWh,

    C_L = b_L[Li](6.94 + 55.845 + 30.974 + 4*15.999)/6.94,
    C_N = b_N[Li]+b_N[Ni]+b_N[Co]+b_N[Mn] + b_N[Li]*2*15.999/6.94,
    P_N = sum_(m=Ni,Co,Mn) b_N[m](1 + 2*17.007/atomic_mass[m]),
    C = (1−nu) C_L + nu C_N,  P = nu P_N,  B_LCE = 5.323 b[Li].

Use pack specific energy E = 1/((1−nu)/E_L + nu/E_N) in Wh/kg. With exports q in
tonnes, cell output is q E / 10^6 GWh. Multiplying GWh by kg/kWh gives kt directly.
Impute every country's CAM = cell GWh times C, AAM = cell GWh times b[Graphite], and
pCAM = cell GWh times P. China CAM and AAM are replaced by MIIT production. pCAM
remains imputed everywhere. Imputation precedes the separate 1% layer cutoffs and uses
all positive cell nodes; it is not restricted to the retained cell roster.

| Product | BACI reference selection | Conversion / production replacement |
| --- | --- | --- |
| cell | HS12 850760 | pack E as above; China replaced by MIIT GWh |
| li_carbonate | HS12 283691 | tonnes / 1000; China carbonate + LiOH·H2O × 73.891/(2×41.964), both MIIT tonnes; Chile carbonate from Cochilco |
| refined_ni | HS12 750210 | tonnes / 1000; no production replacement |
| refined_co | HS12 810520 for trade comparison | reference uses MYB Table 8 production tonnes / 1000 |
| graphite | HS12 380110 synthetic, plus USGS natural | add synthetic export tonnes / 1000 to natural production kt by country; label imputed whenever synthetic is added |
| polysilicon | HS22 280461 | export tonnes / 1000; China replaced by MIIT production kt |
| wafer | HS22 381800 | export tonnes × 60.9 GW / China's export tonnes of this code; China replaced by MIIT production GW |
| pv_cell | HS22 854142 | same conversion with China exports 57.5 GW; production replacement |
| module | HS22 854143 | same conversion with China exports 238.8 GW; production replacement |

USGS mine Li, Co, Ni, Mn, natural graphite, refinery Cu and smelter Al use 2024 rows;
MYB refined Co uses 2023. Mine production is elemental metal mass; no recovery loss is
imposed. A positive capacity is retained iff its share of all positive origins in its
own layer is at least 1%. Layer shares, HHI and top share use the pre-cutoff denominator.

All physical Leontief edges a[input,output] are:

    mine_li -> li_carbonate: 1/5.323;
    li_carbonate -> cam: B_LCE/C;  pcam -> cam: P/C;
    mine_co -> refined_co: 1;  mine_ni -> refined_ni: 1;
    refined_co -> pcam: b[Co]/P;  refined_ni -> pcam: b[Ni]/P;
    mine_mn -> pcam: b[Mn]/P;  graphite -> aam: 1;
    cam -> cell: C;  aam -> cell: b[Graphite];
    refined_cu -> cell: b[Cu];  aluminium -> cell: b[Al];
    polysilicon -> wafer: 2 kt/GW;  wafer -> pv_cell: 1;  pv_cell -> module: 1.

There is no edge between the battery and PV physical product sets. The shared model
couples their shortfalls through the joint failure threshold and country-shock law.
For each sector, start the annual final requirement at retained final output, propagate
R[p] = sum_q a[p,q] R[q] upstream, and scale final demand down by the smallest supply
ratio in that sector's upstream closure if below one. Repeat the propagation after
scaling. Monthly capacity is annual/(12 R[p]), coefficient a' = a R[q]/R[p], and
monthly final demand 1/12. The joint objective sums these normalized sector shortfalls.

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
| Comtrade China tariff lines vs BACI HS6 | W5 supplement below replaces the original unmeasured status; keyless preview remains incomplete and has repeated reporting keys |
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

## W5: primary-source supplement (2026-10-16/17)

The historical networks above remain the reference for W1–W4 and W6. Supplements
are explicit opt-in variants, preserving every original raw hash and result bundle.
`python run_data.py RUN 3.7 eu-sold` writes the combined-data variant; omission of
optional arguments reproduces the reference. `python run_supply.py RUN` compares
headline cut lists at fixed and flexible chemistry. No new onset-rate or probability
fit is implied by a capacity-source change.

**Japan.** METI annual 2024 workbook h2daa2024k, actual-values sheet rows 3488/3498,
items 0108 (automobile) and 0109 (other sealed Li-ion). Twelve monthly observations
per item sum to 4,334,353 and 801,958 kAh, total 5,136,311 kAh. These are quantities
produced in electrical-charge units, not installed plant capacity. Energy equals
kAh times assumed nominal voltage / 1,000,000 GWh: 19.0043507 GWh at 3.7 V or
16.4361952 GWh at 3.2 V. Voltage is not measured by this table, so Japan cells are
`imputed`, as are their BOM-derived upstream materials. The sealed-cell scope is
retained; it is not asserted to cover every industrial cell category. e-Stat terms
section 6(c) permits CC BY 4.0 reuse. The source workbook and selected observations
are frozen. No appId is needed for this annual file.

**Eurostat.** DS-059358 2024, annual Prodcom, quantity unit KG. The frozen API metadata
and Statistics Finland's 2024 classification identify 20121955 as lithium oxide/
hydroxide, 20134351/52 as carbonate at least/below 99.5%, and 20134281 as lithium
iron phosphate. PRODQNT is sold quantity; no APRODQNT actual-production observations
are returned for these slices. Missing/confidential quantities are not zero.

| Product | Germany sold quantity, kg | EU27 sold quantity, kg | Adoption |
| --- | ---: | ---: | --- |
| Oxide/hydroxide 20121955 | 0 | 0 | no positive observation; no LiOH replacement |
| Carbonate >=99.5%, 20134351 | 12,364,000 (:E) | 12,364,080 (:R) | both purity rows retained |
| Carbonate <99.5%, 20134352 | 12,364,000 (:E) | 12,364,000 (:E) | combined code checked before summing |
| Combined carbonate 201343Z1 | 24,728,000 (:E) | 24,728,060 (:R) | German sold-output proxy variant, `imputed` |
| LFP 20134281 | missing (:C) | 12,000,000 (:R) | France 1,840,475 kg; does not replace aggregate CAM |

The combined code confirms the German sum despite equal component estimates; EU
rounding leaves a 20 kg discrepancy against the component sum. :E is an estimate,
:R denotes rounded publication, :C confidential; original flags remain in the
snapshots. Carbonate sold quantity includes technical grades and need not equal
actual 2024 production. LFP sales alone neither measure total CAM nor reveal
shared/dedicated plant capacity; no recipe split is invented. Eurostat's statistical
reuse policy permits the selected EU production rows with attribution; unfiltered
snapshots stay local. Source: Eurostat, extracted 2026-10-16. Supply-Chain-Cuts selected
rows and made comparisons; Eurostat is not responsible for those transformations
or conclusions.

**China tariff lines.** Seven keyless preview queries, row cap 500, and disjoint
batches of all observed partners for the three nonempty lines. The batches reproduce
the unfiltered row multisets exactly; they cannot establish coverage of unseen
partners. The current tariff rows identify H6 (HS2022), so comparisons use the
frozen BACI HS22 parent rather than silently mixing HS revisions.

| National line | Rows / partners | Repeated reporting keys | Returned-row mass / BACI parent mass, t |
| --- | ---: | ---: | --- |
| 28429040 | 189 / 41 | 148 | 3,285.214 / 53,001.725 (6.198%) |
| 28539030 | 76 / 22 | 54 | 134,821.812 / 47,349.835 (284.736%) |
| 28539050 | 19 / 4 | 15 | 3,146.458 / 47,349.835 (6.645%) |
| 2504101000, 2504109100 | 0 | 0 | no rows; not evidence of zero trade |
| 3801100030, 3824999940 | 0 | 0 | no rows; 382499 is absent from the frozen BACI subset |

Rows with identical published reporting dimensions have different masses; their
underlying subdivisions and overlap are unverified. The raw sums above are
reconciliation diagnostics, not asserted exports or capacity. The precursor line
exceeds its BACI parent by a factor 2.847, preventing an agreed aggregate. No pCAM
capacity becomes `production`. Early HTTP 429 responses were retried after a pause;
the final four graphite queries returned valid empty responses. Raw Comtrade bytes
remain local, hash-locked, with licence and completeness unverified. The first
reconciliation snapshot is retained as `reconciliation-v1.json`; its zero for the
unselected BACI 382499 parent is corrected to missing in `reconciliation.json`.

**Korea.** Public KOSIS/Statistics Korea and KBIA searches did not locate a qualifying
annual domestic physical cell-output series. KBIA industry-statistics pages repeatedly
redirected; company/global sales, won values and production indices do not establish
domestic GWh. The Korean cell node retains its flagged trade basis. This is a search
outcome, not proof that no such series exists.

**Competing demand.** The approved, preregistered N1/N2 sensitivity reserves non-battery
uses using global battery shares: Co 76% (2024) and Ni 16% (2023). Country and metal-form
allocation are assumptions. Cu/Al/Mn availability of 100%, 10%, 1% is explicitly assumed;
no matching global battery-only primary share was located. Demand and normalisation
stay fixed, including if baseline shortage appears. FINDINGS reports both recipe
models and every contrary result. No reservation is inferred from an onset.

The workbook audit required openpyxl (XLSX; xlrd supports the earlier XLS concordance)
and the independent source audit used pypdf. Both were already installed globally;
they are now recorded dependencies. No second Python environment was created.
