# Frozen capacity and material evidence

Verified 2026-10-15. The network can be reconstructed from primary production
statistics and actual bilateral trade. It remains a **mixed production and export
proxy model**, not a census of nameplate industrial capacity. No missing production
figure was filled from memory.

## Files and schemas

`data/research/manifest.json` records the retrieval URL, local file, date, SHA-256,
licence and extraction rule. Original BACI rows are selected by product, without
changing their values. The digest of each complete decompressed source member is
also recorded. The acquisition scripts use HTTP byte ranges to read the requested
archive member; the 1.27 GB HS12 and 301 MB HS22 archives need not be retained.

| File under `data/raw/` | Schema or selection |
| --- | --- |
| `baci/BACI_HS12_Y2024_V202601_selected.csv` | Original `t,i,j,k,v,q`; 28,033 bilateral rows, 194 exporters, 223 importers |
| `baci/BACI_HS22_Y2024_V202601_selected.csv` | Same schema; 36,339 rows, 201 exporters, 223 importers |
| `baci/country_codes_V202601.csv` | `country_code,country_name,country_iso2,country_iso3` |
| `baci/product_codes_HS12_V202601.csv`, HS22 equivalent | Original product codes and descriptions |
| `usgs/MCS2026_Commodities_Data.csv` | Complete source CSV; decode **cp1252** |
| `xu2020/supplement.pdf` | Licensed original; 51 pages |
| `xu2020/bom_mid_size_bev.csv` | `chemistry,material,kg_per_pack,pack_kwh,source_table,pack_source_table,pdf_page,source_url`; 64 rows |
| `xu2020/specific_energy.csv` | `chemistry,wh_per_kg,source_table,pdf_page,basis,source_url`; eight rows |
| `miit/production_2024.csv` | `country,iso3,year,product,statistic,value,unit,qualifier,source_url,published,basis`; 17 rows |
| `cochilco/lithium_chemicals_2024.csv` | Chile chemical production; source label, tonnes, worksheet and cell |
| `cochilco/production_1996_2025.xlsx` | Original downloaded workbook; reuse licence unverified |
| `fraunhofer/silicon_usage_2024.csv` | Approximate 2024 silicon intensity; report date and page |

The MIIT file is a concise transcription of numerical facts. It does not reproduce
the ministries' articles. The Cochilco extract contains numerical facts; the
original workbook has no explicit open licence established here. The downloaded
Comtrade HS reference lists have unverified reuse terms and are unnecessary for
the model because the BACI product metadata supplies the descriptions.

## Trade: CEPII BACI

The [BACI documentation](https://www.cepii.fr/DATA_DOWNLOAD/baci/doc/baci_webpage.html)
defines quantities `q` in **metric tonnes** and values `v` in **thousand current
US dollars**. Country codes are the supplied Comtrade codes, not ISO numeric
identifiers. Revision v202601 provides 2024 observations. BACI is distributed
under [Etalab Open Licence 2.0](https://www.etalab.gouv.fr/wp-content/uploads/2018/11/open-licence.pdf),
with attribution to BACI and CEPII. The owning documentation was read directly by
Python; the browser returned a 403 error.

For this capacity reconstruction, 2024 is frozen. The wider 2012–2024 trade history
has **not** been downloaded. The official source archives remain available at
[HS12](https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_HS12_V202601.zip) and
[HS22](https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_HS22_V202601.zip).

Selected HS6 codes are listed exactly in the manifest: natural and synthetic
graphite; mine ores; lithium chemicals; selected metal oxides, sulfates and metal
products; broad cathode/precursor proxies; lithium-ion accumulators; polysilicon;
wafers; and PV cells/modules. A broad HS6 description is not evidence that every
tonne is battery-grade. In particular, 284190, 284290 and 285390 cannot identify
CAM or pCAM globally. Their use is a proxy and must be labelled.

HS12 has 863 selected rows with missing `q`; HS22 has 1,439. Exclude those rows from
mass sums, report their count and retained value coverage, and do not substitute
zero as an observed mass. China 850760 exports have no missing mass rows.

| China exports, 2024 | HS12 tonnes | HS22 tonnes | HS22 missing quantity rows |
| --- | ---: | ---: | ---: |
| Lithium-ion accumulators, 850760 | 2,445,500.136 | 2,438,627.682 | 0 |
| Polysilicon, 280461 | 42,507.410 | 44,025.822 | 3 |
| Wafers, 381800 | 67,049.312 | 66,368.620 | 3 |
| PV cells, 854142 | Not defined | 109,415.235 | 0 |
| PV modules, 854143 | Not defined | 10,328,629.278 | 0 |

HS revisions can yield different reconciled totals. Use the stated revision for
each technology. Never rescale a source silently to reconcile production and
exports. Re-export hubs and integrated domestic production make export mass an
imperfect production proxy.

## Mine and metal production: USGS

The [MCS 2026 data release](https://doi.org/10.5066/P1WKQ63T) supplies the complete
frozen CSV. Its [metadata](https://www.sciencebase.gov/catalog/item/69837e43b66b01367d7ec7c7)
identifies CC0 1.0, explicitly allowing reuse without use constraints.

Use `Year == "2024"`, `Section` beginning `World`, `Statistics == "Production"`,
then select the appropriate `Statistics_detail`. Columns are:
`MCS chapter,Section,Commodity,Country,Statistics,Statistics_detail,Unit,Year,Value,Notes,Is critical mineral 2025,Other notes`.
Strip numeric commas and multiply `thousand metric tons` by 1,000. Retain source
notes, including estimates. `World total` and `Other countries` are aggregates;
neither is an identified country. `W` is withheld and the dash is not a reported
positive quantity. Do not impute either without declaring the rule.

| Chapter | Relevant 2024 production | Source unit |
| --- | --- | --- |
| LITHIUM | Mine production; Li content | t |
| COBALT | Mine production; Co content | t |
| NICKEL | Mine production; Ni content | t |
| GRAPHITE (NATURAL) | Mine production; natural graphite only | t |
| MANGANESE | Mine production; **manganese content** | kt |
| COPPER | Mine production and refinery production; separate measures | kt |
| ALUMINUM | Smelter production; capacity appears separately | kt |
| SILICON | Silicon metal and ferrosilicon; separate measures | kt |

The earlier research note called manganese gross weight. The actual source section
is `World Mine Production (manganese content) and Reserves`; use metal content.
MCS does not provide country Li chemical, Co refinery or Ni refinery production.
The official 2023 cobalt Yearbook PDF/XLSX download returned 403. Its indexed
Table 6 contains 2023 refinery capacity, including standby; this was not substituted
for 2024 production.

Natural graphite production excludes synthetic graphite. Xu's graphite requirement
does not impose natural graphite. Connecting all anode demand to natural mines
defines an all-natural-graphite scenario, not the observed complete supply chain.
Synthetic graphite trade (380110) is separately available as a trade proxy.

## BOM: Xu et al. (2020)

[Xu et al., Communications Materials 1:99](https://doi.org/10.1038/s43246-020-00095-x)
and the [supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs43246-020-00095-x/MediaObjects/43246_2020_95_MOESM1_ESM.pdf)
are CC BY 4.0. The extract transcribes Table 23, mid-size BEV, in **kg per pack**.
Table 1 specifies **66 kWh** for this pack. Divide each mass by 66 to obtain
kg/kWh. Table 4 supplies **pack** specific energy: LFP 129, NCA 178, NCM111 160,
NCM523 163, NCM622 174, NCM622-Si 186, NCM811-Si 193, NCM955-Si 202 Wh/kg.

These are pack-level material coefficients and pack-specific energies. Applying
them to the gross trade mass of 850760 is an explicit approximation; the trade
code contains heterogeneous cells and assembled accumulators. Cu and Al include
pack components. Xu does not tabulate a separator or electrolyte mass in Table 23.
No coefficients for these inputs were invented. MIIT cathode and anode totals do
not independently establish the stoichiometric mass/yield of a pCAM-to-CAM process.

## China: MIIT 2024 observations

The [Li-ion release](https://www.miit.gov.cn/jgsj/dzs/gzdt/art/2025/art_dc20a4d4b3a74dcf91ac1b212f87bbfc.html)
and [PV release](https://www.miit.gov.cn/gyhxxhb/jgsj/dzxxs/dzjc/art/2025/art_da51f7f47c75477ea1fa6732155536db.html)
were published 2025-02-27. Both use the information of listed firms plus industry
association estimates. These are national output estimates, not nameplate capacity
or a complete establishment census. No explicit open licence was found; the frozen
CSV transcribes numerical facts with a primary URL in every row.

Li-ion output was 1,170 GWh: consumer 84, stationary storage 260 and traction 826.
Approximate material output was CAM 3.10 Mt, AAM 2.00 Mt, separator 21.0 billion m²
and electrolyte 1.30 Mt. Battery-grade lithium carbonate was 0.67 Mt and hydroxide
0.36 Mt. Chemistry shares, pCAM output and synthetic/natural graphite fractions
are not separated.

PV output was **more than** 1.82 Mt polysilicon, 753 GW wafers, 654 GW cells and
588 GW modules. The lower-bound qualifier is preserved. Approximate exports were
60.9 GW wafers, 57.5 GW cells and 238.8 GW modules.

For PV, those exports can calibrate a **separate** tonnes/GW conversion at each
stage from the China BACI export mass above. Such a calibration is an imputed
conversion: wafer HS381800 also includes semiconductor material and the measured
mass missingness is nonzero. Never apply polysilicon g/W to complete-module mass.
The [Fraunhofer ISE Photovoltaics Report, 14 July 2026](https://www.ise.fraunhofer.de/content/dam/ise/de/documents/publications/studies/Photovoltaics-Report.pdf),
p. 8, reports approximately **2.0 g/Wp silicon usage in 2024**. This is a cited
silicon conversion, not a module-mass conversion. PV process yields and a universal
module mass/W coefficient were not established.

## Chile: Cochilco

The [owning statistical page](https://www.cochilco.cl/web/estadisticas-mineria/)
links the [1996–2025 production workbook](https://www.cochilco.cl/web/download/140/estadisticas-estadisticas-de-la-mineria-no-metalica/16945/produccion-mineria-no-metalica-1996-2025.xlsx).
`Hoja1!AD21:AD24` gives 2024 lithium carbonate 250,605 t, lithium chloride 0 t,
lithium sulfate 53,515 t and lithium hydroxide 21,364 t. These are tonnes of the
chemical compounds. The aggregate 325,484 t sums products with different lithium
contents. Do not treat it as lithium metal or independently add an intermediate
sulfate supply to final chemical output without checking double counting.

## Evidence limits

Public production coverage is strongest for mines, China midstream/cells, Chile
lithium chemicals and selected base metals. Other country midstream and cell
nodes require a clearly labelled trade or BOM-imputed basis. Missing national
production is not evidence of zero production. No BGS data were downloaded or
published because its licence remains unresolved. No national cell-production
data outside China, complete site-capacity inventory, 2024 chemistry split,
separator/electrolyte BOM or PV conversion yields were established in this pass.
These limits condition any headline about worldwide physical production.

## Checks performed

`data/research/validation.json` records successful readback of all 17 frozen file
hashes and byte counts. All 64 transcribed BOM masses were independently compared
with the original PDF text. Both selected BACI files were parsed; every recorded
mass and value is positive, and missing mass counts are reported above. Research
scripts pass `python -m ruff check data/research`. Network reconciliation and model
results are outside this research pass.
