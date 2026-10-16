# Chokepoint-Lab: data and literature verification

Checked 2026-10-15 against primary sources (dataset pages, documentation, official PDFs, first-party APIs, Crossref/DOI records). Small samples only were downloaded (MCS 2026 commodity CSV, 3 MB; one OECD SDMX slice, 1 MB; Comtrade HS reference lists). "Unverified" means I could not reach the owning source. §12 adds foreign-language and alternative primary sources (Chinese, Japanese, Korean, Spanish, Indonesian, French); its samples are in `dl2/`.

## Verdict

**Usable as stated**
- **CEPII BACI** (HS12, 2012–2024, v202601): the edge/flow backbone. Open licence (Etalab 2.0), direct ZIP download with no account, value and quantity in tonnes. [BACI doc](https://www.cepii.fr/DATA_DOWNLOAD/baci/doc/baci_webpage.html)
- **USGS MCS 2026 data release** (CC0, ScienceBase CSV, no account): country **mine** production 2024–2025 for Li, Co, Ni, natural graphite, Mn, Cu; Cu refinery production; Al smelter production and capacity. [doi:10.5066/P1WKQ63T](https://doi.org/10.5066/P1WKQ63T)
- **OECD Inventory of Export Restrictions on (Critical) Raw Materials**: country × HS6 (HS2007) × year × measure type, with introduction and end dates. It is scriptable through the public OECD SDMX API without an account, which makes it the best open event record for the export-restriction hazard.
- **Interdiction literature**: all citations verified (§9).
- **BOM**: Xu et al. (2020, Supplementary Table 23) gives BatPaC-derived pack-level kg of Li, Ni, Co, Mn, Al, Cu, graphite and Si for LFP, NCA, NCM111/523/622 and NCM811-graphite(Si), from which kg/kWh follows (§8).

**Usable with restrictions**
- **USGS Minerals Yearbook**: country refinery **capacity** is published only for cobalt (MYB 2023 Table 6). The other chapters give production only.
- **GTA**: website exports are CC BY-NC 4.0 and capped. Full or API data require a licensed order, and third-party-facing "Derived Use" must be granted expressly. Use it at most as a cross-check on OECD.
- **EM-DAT**: free for non-commercial use after registration. Substitute or derivative databases are prohibited, and the archive is CC BY-NC-ND. Grain is country-event, with no product dimension. Usable only for a country-level common shock (natural and technological hazards).
- **ACLED**: non-commercial licence. Published derivatives "must be transformative, such that they cannot be reverse engineered". Commercial entities are excluded and scraping is prohibited. Country-level conflict shock only.

**Added by the foreign-source pass (§12)**
- **Refined Co and Ni by country**: BGS World Mineral Statistics OGC API, 1970–2024, JSON, no key. Licence is conflicting (OGL vs BGS Digital Data Licence).
- **Li chemicals by country, partial**:
  - Chile: Cochilco XLSX gives Li2CO3, LiOH and Li2SO4 for 1996–2025.
  - China: MIIT gives battery-grade Li2CO3 and LiOH as national totals.
  - EU: Prodcom (SDMX API) gives Li2CO3, LiOH and LFP by member state.
- **China midstream national totals**: MIIT reports CAM, AAM, separator, electrolyte and cells (GWh) at irregular intervals, 2023 to 2026H1. The figures are association estimates, and there is no API.
- **Cells by country, partial**:
  - China: MIIT (GWh).
  - Japan: METI 生産動態統計, monthly in units, kAh and yen, via e-Stat API.
  - EU: Prodcom 27202350, in pieces and EUR.
- **Tariff lines below HS6**: China's national tariff has distinct 8-digit lines for LFP CAM (28429040) and NCM/NCA pCAM (28539030/28539050), cited in MOFCOM 2025 No. 58. They are reachable by script through the UN Comtrade tariff-line API (preview without key, 500-row cap; free key 100k rows). The EU CN8 separates NMC and LFP only from 2026. Japan classes LFP cathode under 3824.99-999 (catch-all).
- **Event records outside OECD**: MOFCOM announcements (2023 No. 23, 2023 No. 39, 2024 No. 46, 2025 No. 28, 2025 No. 58 and the 2025 No. 70/72 suspensions) carry issue and effective dates and tariff-line codes. Coverage includes destination-specific and dual-use measures that OECD omits.
- **Open hazard feed**: GDACS gives event × country × coordinates, free with no key, but no product field.

**Not usable for the stated purpose**
- **GDELT**: free and redistributable, but its records are actor–action (CAMEO) events with no commodity or product field. It cannot identify country × product disruptions without a bespoke text-classification layer.
- **WTO QR notifications**: free API, but no notifications from Indonesia, Zimbabwe, DRC, Chile or Bolivia, and none for China's graphite or battery measures.
- **World Mining Data and SIACAM**: mine stage only, or compiled from USGS.
- **Still open**:
  - Country-level production or capacity for pCAM, CAM, AAM (natural spherical and synthetic), LiPF6/electrolyte and separators outside China and the EU, notably Korea, Japan materials, Indonesia (MHP, NiSO4) and the US.
  - Global cell capacity by country from a primary source.
  - Korea HSK treatment of CAM.
  - Utilisation (开工率) other than cobalt.

**Design changes the evidence forces**
1. **The node capacity proxy must be split by stage.**
   - Upstream nodes use USGS mine production.
   - Refined Co and Ni use BGS refinery production.
   - Li chemicals use Cochilco (Chile), MIIT (China) and Prodcom (EU); other countries use the BACI export proxy.
   - China's midstream and cell nodes take MIIT national totals. Other midstream and cell nodes fall back to BACI export quantity, which understates production in integrated producers.
   - The model should state per node whether capacity is *production-based* or *trade-based*.
2. **CAM, pCAM, AAM and electrolyte have no distinct HS6 code**, but **China-origin LFP CAM and NCM/NCA pCAM flows are observable at partner level** through China's 8-digit lines (28429040, 28539030, 28539050) in Comtrade tariff-line data. China is the dominant exporter, so these edges can be data-driven. Other origins remain latent: impute them from BOM × cell output, or use EU CN8 from 2026. Doped NCM oxide, by contrast, sits in catch-all codes elsewhere (CBP N321598: HTSUS 3824.99; Japan 3824.99-999).
3. **Use HS12 or later.** HS6 850760 (Li-ion accumulators) does not exist in HS2007 (the Comtrade H3 list), so BACI HS12 (2012–2024) is the earliest usable revision. The OECD Inventory is coded in HS2007 and needs an HS2007→HS2012 concordance.
4. **PV cells and modules split only from HS2022** (854142/854143). Earlier revisions put them in 854140 together with LEDs and other photosensitive devices, so BACI HS22 offers only 2022–2024. Wafers (381800) and polysilicon (280461) are shared with semiconductor-grade material.
5. **BACI quantity is mass.** Cells (850760) are reported in tonnes, not kWh, so demand in kWh needs a pack/cell specific-energy conversion (Xu et al. SI Table 4 gives Wh/kg by chemistry).
6. **Recourse parameters are mostly scenario assumptions.** Primary anchors exist only for:
   - mine lead time (IEA 2021: 16.9 years on average from discovery to production);
   - cobalt refinery utilisation (MYB 2023: 180 kt produced against 271 kt capacity, about 66%);
   - Korea's achieved stockpile (KOMIR: 64.5 days, average of 10 minerals, 2016);
   - the US NDS cobalt solicitation.

   Japan's target days are officially undisclosed (非公開), and the Korean 100-day target is not verified at primary. China discloses no battery-metal reserve. Inventory cover and lithium and graphite utilisation have no open primary source.
7. **The OECD Inventory records only measures applied to all trading partners and excludes dual-use export controls** (OECD 2026, §4). The China graphite licensing requirement from 1 Dec 2023 does appear in the SDMX data (as M6, licensing). Destination-specific and dual-use measures should be added from MOFCOM announcements (§12B), which give dates and tariff-line codes. This makes the hazard record OECD ∪ MOFCOM ∪ hand-coded national acts (Indonesia 2020, Zimbabwe 2022, DRC 2025), with GTA only as a cross-check. Measures that were announced and then suspended (2025 No. 58) should be coded as events with zero realised duration.
8. **Tariff-line edges need reporter-specific concordance.** China's 8-digit lines change across tariff years, and some preview queries returned no rows, so pull with a key and validate totals against HS6 BACI.

---

## 1. CEPII BACI

| Item | Finding | Source |
|---|---|---|
| Access | Direct ZIP links, no registration. Example: `https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_HS12_V202601.zip` | [BACI item page](https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37) |
| Licence | Etalab Open Licence 2.0: "any use is authorized, provided the source is mentionned" | [BACI doc, FAQ](https://www.cepii.fr/DATA_DOWNLOAD/baci/doc/baci_webpage.html) |
| Latest vintage | 202601 (release notes dated 22 Jan 2026; item page says last update 30 Jan 2026). Updated every January | [release notes](https://www.cepii.fr/DATA_DOWNLOAD/baci/doc/release_notes_202601.pdf) |
| Revisions and years | HS92 1995–2024; HS96 1996–; HS02 2002–; HS07 2007–; HS12 2012–; HS17 2017–; HS22 2022–2024 | BACI doc |
| Format and size | One CSV per year inside a ZIP, plus country and product metadata. ZIP sizes from HTTP Content-Length: HS22 301 MB, HS17 795 MB | BACI doc; HTTP HEAD on the ZIPs |
| Variables | t year, k HS6 (keep as string), i exporter, j importer (Comtrade 3-digit codes, not ISO), **v = value, thousand current USD (FOB-reconciled)**, **q = quantity, metric tons**. Only strictly positive flows are recorded | BACI doc |
| Taiwan | Not in Comtrade or BACI; code 490 "Asia nes" is a near-proxy | BACI doc, FAQ |

**Caveats on quantity** (Gaulier and Zignago 2010, CEPII WP 2010-23, pp. 10–11):
- About 15% of reported quantities are in non-ton units. These are converted to tons using implicit rates estimated from mirror flows, and only if at least 10 mirror flows are available and the standard deviation is below 2.5. About 8.5% of final quantities are converted this way.
- Quantities in unknown units or kWh are dropped.
- UNSD changed its quantity treatment from 2005, which introduces a break in unit values.
- The latest year is provisional and is revised in the next release, so versions should not be mixed.

[WP 2010-23](http://www.cepii.fr/PDF_PUB/wp/2010/wp2010-23.pdf)

## 2. USGS Mineral Commodity Summaries 2026 and Minerals Yearbook

**MCS 2026 data release.** Published 6 Feb 2026 (report doi:10.3133/mcs2026), with data for 2024 and 2025e. CC0 1.0. ScienceBase parent item [696a75d5…](https://www.sciencebase.gov/catalog/item/696a75d5d4be0228872d3bf8). The child item "Commodity Salient U.S. and World Statistics" [69837e43…](https://www.sciencebase.gov/catalog/item/69837e43b66b01367d7ec7c7) holds `MCS2026_Commodities_Data.csv` (3.19 MB, long format: chapter, section, commodity, country, statistic, detail, unit, year, value, notes). Files are fetchable by script through `?format=json` and then the file URLs, with no account. Verified by download.

World statistics in that CSV, for the commodities requested (2024 and 2025 unless noted):

| Commodity | Unit | Country mine production | Country refinery or processing | Capacity |
|---|---|---|---|---|
| Lithium | t Li content | yes (11 countries; US withheld) | no | no |
| Cobalt | t Co content | yes (13) | no | no |
| Nickel | t Ni content | yes (10) | no | no |
| Graphite (natural) | t | yes (19) | no | no |
| Manganese | kt gross weight | yes (10) | no | no |
| Copper | kt | yes (18) | **refinery production** (18) | no |
| Bauxite and alumina | kt dry | bauxite (20) | **alumina refinery production** (20) | no |
| Aluminum | kt | n/a | smelter production (13) | **year-end smelter capacity** (13) |
| Silicon | kt | n/a | silicon metal and ferrosilicon production (17) | no |

Narrative facts in the 2026 chapter PDFs:
- Cobalt: China "remained the world leading producer of refined cobalt".
- Cobalt: the DRC export ban (Feb 2025) was replaced by quotas of 18,125 t for the rest of 2025 and up to 96,600 t/yr for 2026–27.
- Cobalt: the US solicited purchases of 7,480 t of cobalt for the NDS over 5 years.
- Lithium: "Government Stockpile: Not available".
- Graphite: stockpile "None"; China exported 37,400 t of spherical purified graphite in 9M 2025.

[cobalt](https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-cobalt.pdf), [lithium](https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-lithium.pdf), [graphite](https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-graphite.pdf). The MCS 2026 also ships `MCS2026_T4_Country_Export_Control.csv`, a snapshot of export controls in effect in Jan 2026. One example is Namibia's 2023 ban on Co, graphite, Li and Mn ores. It cannot serve as a time series because lifted controls are excluded.

**Minerals Yearbook** (latest chapter found per commodity):
- **Cobalt 2023** (advance release) adds **Table 6, world annual cobalt refinery capacity by country, 31 Dec 2023**: total 271,000 t Co, of which China is 182,000e; capacity includes standby. It also adds Table 8, refinery production by country (world 180,000 t, China 82%), and Table 7, mine production. [myb1-2023-cobalt](https://pubs.usgs.gov/myb/vol1/2023/myb1-2023-cobalt.pdf)
- **Nickel 2021** (latest found): Table 10 mine production, Table 11 intermediate products for export, Table 12 primary (refined) production by country and product. No capacity table. [myb1-2021-nickel](https://pubs.usgs.gov/myb/vol1/2021/myb1-2021-nickel.pdf)
- **Lithium 2022**: Table 4 lithium minerals and brine production by country. No refinery production or capacity table found. [myb1-2022-lithium](https://pubs.usgs.gov/myb/vol1/2022/myb1-2022-lithium.pdf)
- **Graphite 2022**: Table 9 natural graphite production by country. No processing or anode capacity. [myb1-2022-graphite](https://pubs.usgs.gov/myb/vol1/2022/myb1-2022-graphite.pdf)
- **Manganese 2023**: Table 6 ore production; Table 7 ferromanganese and silicomanganese production by country. No battery-grade MnSO4. [myb1-2023-manganese](https://pubs.usgs.gov/myb/vol1/2023/myb1-2023-manganese.pdf)

The MYB tables are in PDF and, for older years, in XLSX "tables-only" releases. I did not confirm XLSX availability for 2023.

## 3. OECD Inventory of Export Restrictions

| Item | Finding | Source |
|---|---|---|
| Name and edition | Renamed "…on **Critical** Raw Materials", 2026 edition (Apr 2026), covering **2009–2024** | [OECD 2026 report PDF](https://www.oecd.org/content/dam/oecd/en/publications/reports/2026/04/oecd-inventory-of-export-restrictions-on-critical-raw-materials-2026_2cedac0b/d5ca8f62-en.pdf), p. 5 |
| Products | 65 commodities (58 minerals and metals, 6 wood, metal waste and scrap); **HS2007 6-digit, 489 products**. Lithium, cobalt, nickel, natural graphite, manganese, copper, aluminium and silicon are included | Report §4, Table 4.1 |
| Countries | 80 producing countries (≥3% of world production or top-5 producer of any covered product) | Report Table 4.2 |
| Measure types | Export tax (M1), fiscal tax on exports (M5), export surtax, quota, prohibition, licensing (M6), minimum export price, VAT rebate reduction (M9), customs-point restriction, qualified exporters list, domestic market obligation, captive mining, other | Report Table 4.3; [methodological note (20 Apr 2026)](https://www.oecd.org/content/dam/oecd/en/topics/policy-sub-issues/export-restrictions-on-critical-raw-materials/methodological-note-inventory-export-restrictions-industrial-raw-materials_2025.pdf), Table 1 |
| Exclusions | Measures under international conventions, **dual-use export controls**, and measures not applied to all partners | Report §4 |
| Dates | Yes. `dati` = date of introduction or change (DD/MM/YYYY); `end` = ending date; `temp` = temporary flag; `dir` = direction of change (introduction, increase, elimination, …); plus value, unit, legal basis and source link | Methodological note, Table 3, pp. 8–9 |
| Download | **OECD SDMX API, no account.** Dataflow `OECD.TAD.ADM,DSD_QDD_TAD_EXP_RESTRIC@DF_QDD_TAD_EXP_RESTRIC,3.0`; dimensions REF_AREA, COMMODITY (e.g. `HS07_250410`), POLICY_TYPE, POLICY_VARIATION, POLICY_DESCRIPTION (DATI, END, VAL, DIR, TEMP, …), TIME_PERIOD. A CSV query for CHN, 2023–24, returned 1.08 MB, including M6 licensing on 250410 with DATI 01/12/2023 and END 31/12/2024 | Queried `https://sdmx.oecd.org/public/rest/data/OECD.TAD.ADM,DSD_QDD_TAD_EXP_RESTRIC@DF_QDD_TAD_EXP_RESTRIC,/CHN......?startPeriod=2023` |
| Licence | Report: CC BY 4.0 (p. 2). Dataset licence: **unverified** (the OECD terms page returned 403) | Report p. 2 |

## 4. Global Trade Alert

| Item | Finding | Source |
|---|---|---|
| Access | Free website Data Center with CSV and Excel exports; self-serve exports are capped. A "full research download is available for approved accounts". The API is for "system integration"; premium datasets are "licensed per order". A demo API key is self-serve. Data files are by enquiry | [data-access](https://globaltradealert.org/data-access), [data-center](https://globaltradealert.org/data-center), [API quickstart](https://globaltradealert.org/api-access/quickstart) |
| Licence | Website content is CC BY-NC 4.0 "except where otherwise stated". Licensed data has three classes (Internal, Derived, Redistribution); **Derived Use (third-party-facing outputs) must be expressly granted**. Academic scopes exist (§9.1.7) | [terms](https://globaltradealert.org/terms); [General Terms PDF](https://sgeptupload.s3.eu-west-1.amazonaws.com/terms/GTA+Licensed+Data+-+General+Terms.pdf) §4 |
| Grain | Intervention within a state act. Implementing and affected jurisdictions; affected products at **HS2012 6-digit**, with an "official tariff line" flag when the source gave codes (otherwise GTA staff choose the likely lines) | [GTA handbook/taxonomy](https://gtaupload.s3.eu-west-1.amazonaws.com/Uploads/web/GTA+taxonomy.pdf), §4.2.6 |
| Export measures | Export ban, export licensing requirement, export quota, export tax, export tariff quota, export-related NTM | Handbook §4.1.2 |
| Dates | Announcement, implementation, prolongation and removal dates | Handbook §4.2.3 |

## 5. EM-DAT

- **Access:** free for non-commercial use after registration on [public.emdat.be](https://public.emdat.be). Download is an .xlsx flat table, and a GraphQL API at `https://api.emdat.be/v1` uses a key in the Authorization header ([Python API guide](https://files.emdat.be/docs/emdat_api_python.pdf)). The API documentation is first-party, so scripted access by registered users is evidently intended. The terms do not address automated download explicitly. [Data accessibility](https://doc.emdat.be/docs/data-accessibility/)
- **Terms:** no commercial use "including its data and derivate products". No redistribution of "a substantial part"; no "substitute or derivative databases"; proper citation required. [Terms of use](https://doc.emdat.be/docs/legal/terms-of-use/). The archive version on the UCLouvain Dataverse is CC BY-NC-ND 4.0 (data accessibility page).
- **Grain:** one row per disaster × country (DisNo.), with start and end year, month and day (months and days optional). Natural and technological groups; damages in thousand USD. No sector or product field. [Public table](https://doc.emdat.be/docs/data-structure-and-content/emdat-public-table/)
- **Entry criteria:** at least 10 deaths, at least 100 affected, or a declaration or appeal for international assistance. [Entry criteria](https://doc.emdat.be/docs/protocols/entry-criteria/). A mine flood or refinery fire below these thresholds is absent, so this is a lower bound on facility-level disruptions.

## 6. ACLED

EULA (last updated 8 July 2025; [acleddata.com/eula](https://acleddata.com/eula)):
- §3.1 grants a licence "to develop, publish, and distribute materials incorporating the Licensed Content for non-commercial purposes". Such materials "must be transformative, such that they cannot be reverse engineered to recreate the Licensed Content".
- §1.2: commercial entities need a corporate licence, and public bodies need a public-sector licence.
- §3.3: download is via API or platforms only, and "scraping and crawling the Site is prohibited".
- The Attribution Policy requires prominent acknowledgement, including for manipulated data ([attributionpolicy](https://acleddata.com/attributionpolicy)).

Openly published aggregate results (e.g. country-year event rates feeding a Beta-binomial prior) appear permitted if they are transformative and non-commercial. Publishing the event-level extract in the repository is not permitted.

## 7. GDELT

- **Access:** raw files at data.gdeltproject.org (1.0 daily, 2.0 every 15 minutes) and all datasets in Google BigQuery. [Data](https://www.gdeltproject.org/data.html)
- **Licence:** "unlimited and unrestricted use for any academic, commercial, or governmental use of any kind without fee"; redistribution allowed with citation. [About/Terms](https://www.gdeltproject.org/about.html)
- **Suitability: refuted for country × product disruptions.** Event records are dyadic CAMEO actor–action events with actor, country and geography fields. The Event Codebook V2.0 has no commodity or product field (searched; none present), and the GKG offers only free-text-derived themes. [Event Codebook V2.0](http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf)
- **Mapping cost:** mapping to (country, HS6) would require building and validating a news classifier, which is a separate project. At most, GDELT could provide a country-level unrest or tension intensity.

## 8. Li-ion bill of materials

**Primary numbers used: Xu, Dai, Gaines, Hu, Tukker, Steubing (2020)**, *Communications Materials* 1:99, doi:10.1038/s43246-020-00095-x.
- Material compositions are computed with **Argonne BatPaC v3.1**. NCM523 and the Si-anode variants are adapted by stoichiometry.
- Supplementary Table 23 (SI p. 42) gives **kg per pack**. Supplementary Table 1 gives the mid-size BEV pack as **66 kWh** (total capacity, 85% usable).
- The kg/kWh values below are my division (Table 23 mid-size BEV ÷ 66). They are **pack level**, so Al and Cu include the pack enclosure, busbars and current collectors.
- [Article](https://www.nature.com/articles/s43246-020-00095-x); [SI PDF](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs43246-020-00095-x/MediaObjects/43246_2020_95_MOESM1_ESM.pdf); model and data at doi:10.6084/m9.figshare.13042001.v1.

| kg/kWh (pack) | Li | LCE* | Ni | Co | Mn | Graphite | Cu | Al |
|---|---|---|---|---|---|---|---|---|
| LFP | 0.100 | 0.53 | 0 | 0 | 0 | 1.195 | 0.853 | 1.619 |
| NCA | 0.104 | 0.55 | 0.671 | 0.126 | 0 | 1.075 | 0.745 | 1.264 |
| NCM622 | 0.120 | 0.64 | 0.530 | 0.177 | 0.165 | 1.064 | 0.735 | 1.275 |
| NCM811-graphite(Si)** | 0.113 | 0.60 | 0.671 | 0.084 | 0.078 | 0.705 | 0.736 | 1.197 |

\*LCE = Li × 5.323 (stoichiometric Li2CO3/2Li). This is my conversion, not the source's.
\*\*Xu et al. model NCM811 only with a Si-doped graphite anode (Si 0.070 kg/kWh), so graphite is lower than for a pure-graphite NCM811 cell. Small-BEV and PHEV packs give different per-kWh values because of fixed pack overhead (Table 23).

- **Electrolyte and separator per kWh:** not in Xu et al. Table 23. These are in BatPaC itself, which I could not reach (anl.gov returned 403 or a bot challenge). **Unverified.**
- **IEA (2021)**, *The Role of Critical Minerals in Clean Energy Transitions*, p. 89, gives kg per vehicle by chemistry for a 75 kWh pack (sources: Argonne 2020a,b) **only as a chart**, without tabulated numbers. [PDF](https://iea.blob.core.windows.net/assets/ffd2a83b-8c30-4e9d-980a-52b6d9a86fdc/TheRoleofCriticalMineralsinCleanEnergyTransitions.pdf)
- **IEA GCMO 2025** (CC BY 4.0) gives no per-kWh chemistry table in the text. Projections are in the Critical Minerals Data Explorer. [PDF](https://iea.blob.core.windows.net/assets/ef5e9b70-3374-4caa-ba9d-19c72253bfc4/GlobalCriticalMineralsOutlook2025.pdf)

**HS6 mapping** (verified against the UN Comtrade reference lists H3 = HS2007, H4 = HS2012, H5 = HS2017, H6 = HS2022, `comtradeapi.un.org/files/v1/app/reference/H*.json`):

| Stage | HS6 | HS2022 text (abridged) | Distinct? |
|---|---|---|---|
| Spodumene and Li ores | 253090 | Mineral substances n.e.c. | **Shared** (all ch. 25 n.e.c.) |
| Lithium carbonate | 283691 | Lithium carbonate | distinct |
| Lithium hydroxide | 282520 | Lithium oxide and hydroxide | distinct |
| Natural graphite | 250410 / 250490 | Powder or flakes / other | distinct, but spherical and purified graphite is not separated |
| Synthetic graphite | 380110 | Artificial graphite | distinct (not anode-specific) |
| Cobalt ores | 260500 | Cobalt ores and concentrates | distinct |
| Cobalt intermediates and metal | 810520 | Mattes, intermediates, unwrought cobalt, powders | **Shared** within stage (hydroxide intermediates and metal together) |
| Cobalt oxides and hydroxides | 282200 | Cobalt oxides and hydroxides | distinct |
| Cobalt sulphate | 283329 | Sulphates n.e.c. | **Shared** (also MnSO4) |
| Nickel ores | 260400 | Nickel ores and concentrates | distinct |
| Nickel matte | 750110 | Nickel mattes | distinct |
| Nickel MHP and other intermediates | 750120 | Oxide sinters and other intermediates | mixed |
| Nickel sulphate | 283324 | Sulphates of nickel | distinct |
| Manganese ore | 260200 | Manganese ores and concentrates | distinct |
| Cu cathode / Al unwrought / Al foil | 740311 / 760110 / 760711 | as named | distinct, not battery-specific |
| CAM and pCAM (NMC, NCA, LFP) | none | candidates 284190, 284290, 382499 | **No distinct code.** CBP ruling N321598 (2021) classed doped NCM oxide under HTSUS 3824.99.3900 ([CBP CROSS](https://rulings.cbp.gov/ruling/N321598)) |
| Electrolyte salt LiPF6 | 282690 (likely) | Other complex fluorine salts | **Shared**; classification unverified |
| Li-ion cells, modules, packs | 850760 | Li-ion accumulators | distinct **from HS2012 only**; cells and packs share the code |

**How the literature handles missing codes:** proxies or grouping by metal. This is reported in an UNCTAD 2023 technical note, which lists 284190, 285390 and 382499 among cobalt- and lithium-cathode codes. I saw it only in a search snippet (the PDF returned 403), so it is **unverified**. Alternatively, intermediate stages are imputed from BOM coefficients.

## 9. Network interdiction literature (verified via Crossref)

| Reference | Contribution |
|---|---|
| Wood, R.K. (1993). Deterministic network interdiction. *Mathematical and Computer Modelling* 17(2):1–18. doi:10.1016/0895-7177(93)90236-R | Proves max-flow interdiction NP-complete; the single-level MIP is obtained by dualising the inner max-flow (min-cut) LP. This is the canonical **LP-duality reformulation (a)** |
| Israeli, E., Wood, R.K. (2002). Shortest-path network interdiction. *Networks* 40(2):97–111. doi:10.1002/net.10039 | Max-min shortest-path interdiction; dual-based single-level MIP and a Benders decomposition with supervalid inequalities |
| Cormican, K.J., Morton, D.P., Wood, R.K. (1998). Stochastic network interdiction. *Operations Research* 46(2):184–197. doi:10.1287/opre.46.2.184 | Interdiction with uncertain success and capacities; sequential-approximation bounds |
| Morton, D.P., Pan, F., Saeger, K.J. (2007). Models for nuclear smuggling interdiction. *IIE Transactions* 39(1):3–14. doi:10.1080/07408170500488956 | Bilevel stochastic interdiction reduced to a single-level MIP via LP duality, a template for (a) under scenarios |
| Brown, G., Carlyle, M., Salmerón, J., Wood, K. (2006). Defending critical infrastructure. *Interfaces* 36(6):530–544. doi:10.1287/inte.1060.0252 | Attacker–defender and **defender–attacker–defender (b)** models in which the inner problem is the operator's recourse LP; dualise and decompose |
| Alderson, D.L., Brown, G.G., Carlyle, W.M., Wood, R.K. (2011). Solving defender-attacker-defender models for infrastructure defense. *12th INFORMS Computing Society Conf.*, 28–49. doi:10.1287/ics.2011.0047 | Decomposition algorithms for trilevel DAD models (b) |
| Alderson, D.L., Brown, G.G., Carlyle, W.M. (2015). Operational models of infrastructure resilience. *Risk Analysis* 35(4):562–586. doi:10.1111/risa.12333 | Resilience as worst-case operational loss under attack: operator model + attacker-defender framing (b) |
| Smith, J.C., Song, Y. (2020). A survey of network interdiction models and algorithms. *EJOR* 283(3):797–811. doi:10.1016/j.ejor.2019.06.024 | Current survey of formulations (duality, decomposition, multi-level) |
| Church, R.L., Scaparra, M.P. (2007). Protecting critical assets: the r-interdiction median problem with fortification. *Geographical Analysis* 39(2):129–146. doi:10.1111/j.1538-4632.2007.00698.x | Facility (node) interdiction with fortification, the node-removal analogue of the design |
| Snyder, L.V. et al. (2016). OR/MS models for supply chain disruptions: a review. *IIE Transactions* 48(2):89–109. doi:10.1080/0740817X.2015.1067735 | Review of disruption models, including inventory and recourse (c) |
| Klimek, P., Obersteiner, M., Thurner, S. (2015). Systemic trade risk of critical resources. *Science Advances* 1(10):e1500522. doi:10.1126/sciadv.1500522 | Trade-network cascade model of export-restriction shocks for critical resources (c) |
| Sun, X., Shi, Q., Hao, X. (2022). Supply crisis propagation in the global cobalt trade network. *Resources, Conservation and Recycling* 179:106035. doi:10.1016/j.resconrec.2021.106035 | Shock propagation on the cobalt trade network (c) |
| Xu, C. et al. (2020), §8 | Chemistry-level material demand for EV batteries (c, BOM) |

## 10. Recourse anchors

| Parameter | Primary anchor | Status |
|---|---|---|
| (a) Mine lead time | IEA (2021) p. 122: global average discovery→production 2010–19 = 12.5 (discovery to feasibility) + 1.8 (construction planning) + 2.6 (construction to production) ≈ 16.9 years, from the top 35 projects. The same chart has per-mineral bars (Cu, Ni laterite and sulfide, Li South America and Australia) without tabulated values. GCMO 2025 p. 178: newly announced rare-earth projects average 8 years | anchor (mine). **Refinery lead time: no primary number found** |
| (b) Stockpiles | US NDS: cobalt solicitation 7,480 t over 5 years (MCS 2026 cobalt); MCS lists the NDS acquisition and disposal plan. Japan (JOGMEC): target generally 60 days of consumption, up to 180 days for high-risk minerals; quantities undisclosed ([IEA policy database](https://www.iea.org/policies/16639-international-resource-strategy-national-stockpiling-system), secondary to METI). Korea (KOMIR): rare-metal target 100 days, up from 54 ([IEA policy database](https://www.iea.org/policies/17940-the-national-program-for-metal-nonferrous-and-rare-stockpiling)). China: no official disclosure found. DRC: 9,600 t/yr of its cobalt quota earmarked for national strategic reserves (MCS 2026) | targets in days are anchors; actual holdings are scenario |
| (c) Spare capacity and utilisation | Cobalt refining: 180 kt production / 271 kt capacity (incl. standby) ≈ 0.66 in 2023 (MYB 2023 Tables 6 and 8). PV manufacturing: "capacity utilisation worldwide never exceeded 70% during the last decade" (IEA 2022 PV report, p. 25). GCMO 2025 p. 183 notes "significant excess capacity" for Chinese high-purity MnSO4 in early 2024 (no number). **Lithium and graphite refining: none found** | Co anchored; Li and graphite are scenario |
| (d) Inventory cover (days) | No primary source for the battery chain. US cobalt industry year-end stocks are in the MCS CSV (US only) | **scenario assumption** |

## 11. Solar PV (later extension)

- **Polysilicon intensity:** about 2.0 g/Wp in 2024, down from about 16 g/Wp in 2004 (Fraunhofer ISE, *Photovoltaics Report*, 14 July 2026, p. 8; trend chart on p. 36). [PDF](https://www.ise.fraunhofer.de/content/dam/ise/de/documents/publications/studies/Photovoltaics-Report.pdf)
- **Module mass composition** (IEA 2022, *Special Report on Solar PV Global Supply Chains*, p. 21): glass 68–72%, Al 12–14%, polymers 8–10%, Si 3–4%, Cu 2–4%, Ag 0.03–0.08%. [PDF](https://iea.blob.core.windows.net/assets/d2ee601d-6b1a-4cd2-a0e8-db02dc64332c/SpecialReportonSolarPVGlobalSupplyChains.pdf)
- **Silver mg/W:** ITRPV 2026 is reported in trade press as about 10 mg/W for TOPCon, 8.9 for PERC and 12.0 for SHJ (2025). I could not access the primary ITRPV report, so these are **unverified**.
- **HS6 codes** (Comtrade H3–H6):
  - polysilicon 280461 (Si ≥ 99.99%, shared with electronic grade);
  - wafers 381800 (doped elements for electronics, shared with semiconductor wafers);
  - cells 854142 and modules 854143 **from HS2022 only**; HS2007–HS2017 had a single 854140 covering cells, modules and LEDs;
  - silver 710691 / 710692;
  - PV glass, frames and backsheet have no PV-specific codes.

## 12. Foreign and alternative sources

Checked 2026-10-15. Samples in `scratchpad/dl2/`: METI 2025 annual workbook (`h2daa2025k.xlsx`, 2.2 MB), Cochilco non-metallic production (`cochilco_nometal.xlsx`), Eurostat Prodcom slice (`prodcom_sample.csv`), BGS OGC API extracts (`bgs_{Cobalt,Nickel,Lithium}.json`), Comtrade tariff-line preview for China 28429040 (`cn_2024_28429040_X.json`), WTO QR notifications (`wto_qrs.json`). "Press only" means the figure was seen only in secondary reporting.

### 12A. Midstream production, capacity and product codes

**Production statistics**

| Source (publisher) | Access, licence | Scriptable | Grain | Coverage, vintage | Closes |
|---|---|---|---|---|---|
| **MIIT 工业和信息化部电子信息司, 《全国锂离子电池行业运行情况》** (National Li-ion battery industry operation). Latest: 《2026年上半年…》, released 2026-09-15 [MIIT](https://www.miit.gov.cn/gyhxxhb/jgsj/dzxxsnew/xyyx/art/2026/art_3343e14c0d9a4ddc9fb9f63189aa7c0d.html); 2024 full year, released 2025-02-27 [MIIT](https://www.miit.gov.cn/jgsj/dzs/gzdt/art/2025/art_dc20a4d4b3a74dcf91ac1b212f87bbfc.html) | Free HTML; no licence stated | No API; scrape HTML text | **China national total only.** Cells by use (consumer, ESS, traction) in GWh; CAM, AAM and electrolyte in t; separator in m²; battery-grade Li2CO3 and LiOH in t | 2023 to 2026H1 seen; irregular (bimonthly to semi-annual). 2024: cells 1,170 GWh (84/260/826); CAM 3.10 Mt, AAM 2.00 Mt, separator 21.0 bn m², electrolyte 1.30 Mt; Li2CO3 0.67 Mt, LiOH 0.36 Mt. 2026H1: cells >1,240 GWh; CAM ~4.75 Mt, AAM ~3.00 Mt, separator ~33.0 bn m², electrolyte ~2.20 Mt; Li2CO3 0.62 Mt, LiOH 0.18 Mt | China row of CAM, AAM, separator, electrolyte, Li chemicals and cells. Basis is "锂电池行业规范公告企业信息和行业协会测算", i.e. listed firms plus association estimates, so not a census. pCAM, LiPF6 and synthetic graphite are not separated |
| **NBS 国家统计局**, monthly 规模以上工业 output of 锂离子电池 | Free; data.stats.gov.cn | Web query (unverified as an API) | China, monthly, firms with revenue ≥ 20 M CNY | Growth rates seen in releases (Jul 2025 +29.4% y/y [NBS](https://www.stats.gov.cn/sj/sjjd/202508/t20250815_1960811.html); 2026Q1 +40.8% [NBS](https://www.stats.gov.cn/sj/sjjd/202604/t20260416_1963332.html)). Unit and series length **unverified** | China cells (count, not kWh) |
| **CABIA 中国汽车动力电池产业创新联盟**, 《动力电池月度信息》 | Monthly PDF; official URL **unverified** (distributed via CAAM and press) | No | China: traction plus ESS production, sales, installation (GWh) | Press only: 2025 production 1,755.6 GWh, installation 769.7 GWh | China cells, monthly. Not citable as primary until the PDF is obtained |
| **METI 経済産業省生産動態統計** (Current Production Statistics), 機械器具月報（その39）電池. 2025 annual, released 2026-06-30 [e-Stat](https://www.e-stat.go.jp/stat-search/files?page=1&bunya_l=05&layout=dataset&toukei=00550200&stat_infid=000040475159) | Free XLSX; e-Stat API needs a free appId | Yes (e-Stat API, XLSX) | Japan, monthly. リチウムイオン蓄電池（車載用）and（その他）: production count (千個), **capacity in 千Ah**, value (百万円), sales, inventory. Verified in the sample | Monthly; 2025 annual seen | Japan cells (Ah, not Wh). **No battery materials**: the chemical survey has no CAM, AAM, electrolyte or separator item (searched the 2025 workbook; only 人造黒鉛電極 and catalyst cobalt consumption) |
| **Eurostat Prodcom** DS-059358 (NACE/CPA 2.1, to 2024) and DS-059368 (CPA 2.2, 2025) [Comext SDMX](https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/data/DS-059358/A..27202350./?startPeriod=2019&format=SDMX-CSV) | Free, no account; Eurostat reuse policy (licence page not re-read) | **Yes**, SDMX 2.1 REST, CSV | EU member state × PRODCOM8 × year; quantity and value | 2019–2024 (CPA 2.1), 2025 (CPA 2.2, updated 29 Sep 2026). Codes: 27202350 Li-ion accumulators (pieces; EU27 2024 = 199.5 M pieces, €18 bn); 27202410 separators (value); 20134281 LiFePO4 (kg; EU27 2024 = 12 kt); 20134351/52 Li2CO3; 20132500 LiOH; 23991400 artificial graphite and preparations (EU27 2024 = 108 kt); 20134161/62 Ni and Co sulphates | EU rows for LFP, Li chemicals, Ni/Co sulphate, artificial graphite and cells. Many national values are confidential (blank) while still included in EU27; cells and packs share 27202350 (JRC notes double counting) |
| **Cochilco** (Comisión Chilena del Cobre), *Producción Minería No Metálica (1996–2025)* [XLSX](https://www.cochilco.cl/web/download/140/estadisticas-estadisticas-de-la-mineria-no-metalica/16945/produccion-mineria-no-metalica-1996-2025.xlsx) | Free; no licence stated | Direct XLSX | Chile × product × year (t) | 1996–2025. Carbonato de litio 250,605 t (2024), 259,571 t (2025); hidróxido de litio 21,364 t, 29,817 t; sulfato de litio 53,515 t, 107,509 t. BGS's Chile "Carbonate" row equals the Cochilco figure | **Chile row of Li2CO3 and LiOH**, closed |
| **BGS World Mineral Statistics**, OGC API [collection](https://ogcapi.bgs.ac.uk/collections/world-mineral-statistics) | Free, no key. Licence **conflicting**: BGS datasets page says open data is OGL ([BGS](https://www.bgs.ac.uk/datasets/uk-and-world-mineral-statistics-datasets/)); the dataset metadata cites the BGS Digital Data Licence | **Yes**, JSON with property filters (`erml_group=Cobalt`) | Country × commodity × year | 1970–2024 (the API text still says 2022, but 2024 rows are returned). Tables: **Production of refined cobalt** (2024: China 175 kt, Finland 12.0 kt, Canada 4.9 kt, Japan 4.2 kt); **Smelter/refinery production of nickel** (2024: Indonesia 1,609 kt, China 1,029 kt); lithium minerals by type, including **Carbonate** for Chile (250,605 t in 2024) and Argentina (81,000 t) | **Refined Co and Ni by country**, closed. Ni is not split into class 1, NiSO4 or MHP |
| **World Mining Data 2026** (Austrian BMF, Reichl) [page](https://www.bmf.gv.at/en/topics/mining/mineral-resources-policy/wmd.html) | Free PDF and XLSX; **no licence** stated ("not an official record") | Direct XLSX | Country × 65 commodities, last 5 years | WMD 2026, data to 2024 | Mine stage only (Li as Li2O, Co, Ni, graphite). **Does not close midstream** |
| **SIACAM** (Secretaría de Minería, Argentina), *Producción mundial de litio* [CKAN](https://datos.gob.ar/dataset/produccion-mundial-de-litio-tablero-global-del-litio-siacam) | CC BY 4.0, CSV | Yes (CKAN API) | Country × year, kt LCE, 1995–2024 | Compiled from BP, Energy Institute and USGS, so secondary | Nothing new over USGS |
| **IEA Critical Minerals Dataset** 2026 [page](https://www.iea.org/data-and-statistics/data-product/critical-minerals-dataset) | CC BY 4.0; free account required | Download or .Stat | Demand projections; 2026 adds mining and refining supply projections. Country grain **unverified** | Jul 2026 | Possibly refining shares; unverified |
| **Australia REQ** (Office of the Chief Economist), Sep 2026, historical and forecast XLSX | Landing page seen via search; page timed out on fetch | Unverified | Australia | **Unverified** | Possibly Australian LiOH output |
| **JRC RMIS** supply viewer [page](https://rmis.jrc.ec.europa.eu/uploads/bvc/supply.htm) | Free | No | Shares attributed to IEA (2025) and Benchmark Mineral Intelligence (2025) | n/a | Not primary (Benchmark is commercial) |
| Korea KOSIS (광업제조업조사), KOMIR, Indonesia ESDM/MODI, DRC EITI | Not reached | n/a | n/a | n/a | **Unverified**. ESDM press releases give per-project HPAL targets only (e.g. 55 kt/yr MHP), not a series |

**Product codes beyond HS6** (this changes design change 2 in the Verdict)

| Jurisdiction | Finding | Source |
|---|---|---|
| **China** (8-digit 税则号列, 10-digit 海关商品编号) | MOFCOM–GACC Announcement 2025 No. 58 cites **28429040 磷酸铁锂正极材料** (LFP CAM), **28539030 镍钴锰氢氧化物** (NCM pCAM), **28539050 镍钴铝氢氧化物** (NCA pCAM) and 85076000 cells. Announcement 2023 No. 39 cites 2504101000 and 2504109100 for natural flake graphite "含球化石墨" (incl. spherical), and 3801100030 and 3824999940 for high-purity artificial graphite | [2025 No. 58](https://www.mofcom.gov.cn/zwgk/zcfb/art/2025/art_79646f0161564975a938fe00fee158d5.html); [2023 No. 39](https://www.mofcom.gov.cn/zcfb/blgg/art/2023/art_f6b1bc49e2c8482f8eb749012bc66dec.html) |
| China, as reported to Comtrade | The China tariff-line export data contain the 8-digit lines 25041010/25041091/25041099, 28269010/20/90, 28252010/90, 28332910/20/30/90, **28539030/40/50**, **28429040**, 38249920/30/92/99, 39202010/90, 81052020/90 and 75012010. Line descriptions other than those MOFCOM cites (e.g. 28269020 = LiPF6, 25041091 = spherical graphite) are from third-party tariff sites only: **unverified** | Comtrade preview API (below) |
| **EU CN8 from 1 Jan 2026** | New subheadings: "Lithium nickel manganese cobalt oxides" and "Lithium iron phosphate" (CN 2841 90 40, 2841 90 70, 2842 90 20, 2842 90 70) and "Artificial graphite" (3801 10), under Implementing Regulation (EU) 2025/1926. **Usable only from reference year 2026** | [EC Access2Markets](https://trade.ec.europa.eu/access-to-markets/en/news/combined-nomenclature-and-common-customs-tariff-applicable-eu-1-january-2026) |
| Japan (9-digit statistical codes) | Import schedule: 2826.90 has no LiPF6 line; 2853.90.010 is LiFSI; 2841.90 and 2842.90 have no cathode line. An advance ruling puts LFP–C cathode material under **3824.99-999** (catch-all). Japan does not separate CAM | [Japan tariff ch. 28](https://www.customs.go.jp/english/tariff/2026_04_01/data/e_28.htm); [ruling 124001871, 2024-07-12](https://www.customs.go.jp/tetsuzuki_search/bunrui/J5/24/J52400298.htm) |
| Korea (HSK 10-digit) | KCS open API on data.go.kr: free, "이용허락범위 제한 없음" (no restriction on use), HS 2/4/6/10 by country, monthly; needs a free key. **Whether HSK separates CAM or pCAM is unverified** | [data.go.kr 15100475](https://www.data.go.kr/data/15100475/openapi.do) |
| US (HTS 10-digit) | Comtrade tariff lines show 3824.99.39.10 and other subdivisions (description "of lithium nickel cobalt manganese oxides" from third-party sites only) | Comtrade preview |

**Reaching tariff lines.** The UN Comtrade public preview endpoint `https://comtradeapi.un.org/public/v1/previewTariffline/C/A/HS?reporterCode=156&period=2024&cmdCode=28429040` returns partner-level rows (net weight, FOB value) with **no key** but caps output at 500 rows. A free registered key allows 100k records per call and 500 calls per day; bulk tariff-line files are premium only ([Comtrade subscriptions](https://comtradeplus.un.org/Subscriptions)). The results below were obtained from this endpoint.
- Not every reporter publishes national lines: in 2024 China (8-digit), Japan (9-digit) and the US (10-digit) did, but Korea and Germany reported only HS6.
- China's exports summed from the preview (capped, indicative): 28539030 NCM hydroxide 179 kt in 2023 and 135 kt in 2024. 28429040 LFP was 3.3 kt in 2024 and 32 kt in 2025 (partial year).
- Some years returned no rows on repeat queries, so preview completeness is **unverified**.

**China customs portal** (海关统计数据在线查询平台, `stats.customs.gov.cn`): monthly official data by 8-digit code × partner × trade mode × province. Free, no account, but behind a JavaScript anti-bot challenge (HTTP 412 to curl), so **not scriptable**. GACC also provides free custom extracts by e-mail (≤500 eight-digit codes, ≤5 grouping fields, ≤50 MB) ([GACC 海关统计服务指南](http://www.customs.gov.cn/customs/302249/zfxxgk/2799825/302274/tjfwzn/2319672/index.html), seen via search only; the page failed TLS).

### 12B. Disruption event sources beyond OECD

**MOFCOM announcements (primary; dates and reference codes in the text)**

| Announcement | Issued | Effective | Content | Grain | In OECD? |
|---|---|---|---|---|---|
| 商务部 海关总署公告2023年第23号 (Ga, Ge export control) | 2023-07-03 | 2023-08-01 | Licensing, 8 Ga and 6 Ge items, with customs codes | China × 10-digit code | Dual-use, so excluded |
| 2023年第39号 关于优化调整石墨物项临时出口管制措施的公告 (adjusting temporary graphite export controls) | 2023-10-20 | 2023-12-01 | High-purity, high-strength, high-density artificial graphite; natural flake graphite incl. spherical; codes as in 12A | China × 10-digit | Appears as M6 (§3) |
| 商务部公告2024年第46号 (dual-use items to the US) | 2024-12-03 | on publication | Ga, Ge, Sb and superhard materials "原则上不予许可" (in principle not licensed) to the US; graphite to the US under stricter end-use review ([MOFCOM](https://exportcontrol.mofcom.gov.cn/article/gndt/202412/1068.html)) | China × destination | **No** (destination-specific) |
| 商务部 科学技术部公告2025年第28号 (tech export catalogue) | 2025-07-15 | 2025-07-15 | Adds to 限制出口 (export-restricted) technology: battery LFP and LMFP preparation; phosphate cathode precursor preparation; spodumene → Li2CO3 and LiOH; brine Li extraction ([MOFCOM](https://www.mofcom.gov.cn/zcfb/zgdwjjmywg/art/2025/art_67e2a41850ec428eb1b7be6ec2f2bded.html)) | China × technology | No |
| 商务部 海关总署公告2025年第58号 | 2025-10-09 | 2025-11-08 (suspended) | Li-ion cells ≥300 Wh/kg (85076000); LFP CAM 28429040; NCM and NCA pCAM 28539030/50; Li-rich Mn CAM; artificial graphite anode; equipment and process technology | China × 8-digit | No |
| 2025年第70号 | 2025-11-07 | to 2026-11-10 | Suspends 2025 Nos. 55–58, 61, 62 ([MOFCOM](https://www.mofcom.gov.cn/zwgk/zcfb/art/2025/art_b1ec77dd3f0d4762952904df7cdaadec.html)) | | |
| 商务部公告2025年第72号 | 2025-11-09 | to 2026-11-27 | Suspends para. 2 of 2024 No. 46 ([MOFCOM](https://www.mofcom.gov.cn/zwgk/zcfb/art/2025/art_5c68985a6b1a46778e2e8dbff1bb1601.html)) | | |

Access: free HTML and PDF on mofcom.gov.cn and exportcontrol.mofcom.gov.cn; no API or licence statement. These are the only primary records found that name battery midstream products (CAM, pCAM, anode) at tariff-line grain. The 2025 measures were announced and then suspended, so they are hazard events with zero realised duration. Whether the suspension is renewed after 2026-11-10 is **unknown** as of this check.

**Other national measures**

| Measure | Primary record | Status |
|---|---|---|
| Indonesia: Permen ESDM No. 11/2019 (second amendment to Permen 25/2018), enacted 2019-08-28, **in force 2020-01-01** | [JDIH BPK](https://peraturan.bpk.go.id/Details/142232/permen-esdm-no-11-tahun-2019); [peraturan.go.id](https://peraturan.go.id/id/permen-esdm-no-11-tahun-2019) | Dates verified. The provision (nickel ore < 1.7% Ni export end) was read in secondary sources only: **unverified** |
| Zimbabwe: SI 213 of 2022, *Base Minerals Export Control (Lithium Bearing Ores and Unbeneficiated Lithium) Order* (Ministerial permit required) | [Veritas Zimbabwe PDF](https://www.veritaszim.net/sites/veritas_d/files/SI%202022-213%20Base%20Minerals%20Export%20Control%20%28Lithium%20Bearing%20Ores%20and%20Unbeneficiated%20Lithium%29%20Order%2C%202022.pdf) (gazette text, NGO host) | Located, PDF not parsed. The 25 Feb 2026 suspension of all unprocessed mineral exports, incl. Li concentrate, is from a law-firm note only: **unverified** |
| DRC: ARECOMS Décision 001/ARECOMS/2025 (cobalt export suspension, 22 Feb 2025); 004/ARECOMS/2025 (20 Sep 2025: suspension to 15 Oct, quotas from 16 Oct; 2026 = 96,600 t incl. 9,600 t strategic) | IEA policy database [28969](https://www.iea.org/policies/28969-temporary-suspension-of-cobalt-export-from-the-democratic-republic-of-congo), [29138](https://www.iea.org/policies/29138-drc-arecoms-decision-no-0042025-cobalt-quota-system); consistent with MCS 2026 (§2) | ARECOMS original **unverified**. The 6 Aug 2026 Cu/Co concentrate export ban is press only |

**Databases**

| Source | Access, licence | Scriptable | Grain | Coverage | Product field |
|---|---|---|---|---|---|
| **WTO QR notifications** API `https://qr-notification.wto.org/api/itip/qrs` | Free, no key; WTO copyright page (licence not read) | **Yes** (JSON, 5 MB, 2,379 records) | Reporter × measure × HS codes (HS6) × date_start/date_end | Notifications 1995→ (latest start 2026-09-10) | Yes (HS6). **Useless for this chain**: no notifications from Indonesia, Zimbabwe, DRC, Chile or Bolivia; China's notified QRs omit graphite and battery items; Argentina's entries are unrelated |
| WTO I-TIP Goods (NTMs) [data.wto.org](https://data.wto.org/dataset/ext_itip_1) | Free | HTML and API | Measure × HS | 1995–2021, last updated 2022 | Yes; stale |
| **IEA Critical Minerals Policy Tracker** [page](https://www.iea.org/data-and-statistics/data-tools/critical-minerals-policy-tracker) | **CC BY 4.0** | No bulk download found (methodology PDF, Jul 2026, only) | Policy × country | 600+ policies, 60+ countries; annual update | Mineral named in text; includes the DRC, Indonesia and Zimbabwe measures. A curated secondary record, not primary |
| **GDACS** API `gdacs.org/gdacsapi/api/events/geteventlist/SEARCH` | Free, no key; attribution "GDACS"; "as is" ([terms](https://www.gdacs.org/About/termofuse.aspx)) | **Yes** (GeoJSON; verified) | Event × country × coordinates × alert level (EQ, TC, FL, VO, DR, WF) | Automatic alerts, c. 2000→ (start year unverified) | No. Open substitute for EM-DAT natural hazards, with coordinates usable to match facilities |
| ReliefWeb API v2 | Free but needs an **approved appname** (HTTP 403 otherwise); v1 decommissioned | Yes after approval | Disaster × country × type × date | n/a | No |
| DesInventar Sendai (UNDRR) [site](https://www.desinventar.net/) | Software Apache-2; **data licence per country unverified** | Web export | Sub-national event × losses | Varies by country (c. 120 countries) | No |

### 12C. Recourse anchors in foreign sources

| Parameter | Finding | Status |
|---|---|---|
| China state reserve (国家粮食和物资储备局) | Only metal-reserve actions found: releases of Cu, Al and Zn (公告2021年第2号; first batch 100 kt on 2021-07-05) ([NFSRA](https://www.lswz.gov.cn/html/tzgg/2021-06/16/content_266225.shtml), [NFSRA](https://www.lswz.gov.cn/html/xinwen/2021-07/07/content_266631.shtml)). No announcement of Li, Co, Ni or graphite purchases or holdings | No primary anchor; **scenario** |
| Japan (JOGMEC 国家備蓄) | JOGMEC states its rare-metal stockpile role, but its page gives no days ([JOGMEC](https://www.jogmec.go.jp/activities/stockpiling/metal/rare-meta.html)). Search snippets of METI/ANRE pages say: target "国内基準消費量の60日分（一部鉱種は30日）" (60 days of reference consumption, 30 for some minerals), set in 1986; revised under the 2020 「金属鉱産物の備蓄に係る基本方針」 to mineral-specific days; **target days and holdings are 非公開** (undisclosed). The METI pages returned 403 | **Unverified** (snippet); the 60/180-day figures in §10 stay secondary |
| Korea (KOMIR 비축) | KOMIR: by 2016, average **64.5 days** of domestic demand for 10 minerals; took over 9 rare metals from PPS (조달청) in 2019 ([KOMIR](https://www.komir.or.kr/kor/contents/59)). The 100-day average target is attributed to MOTIE 「희소금속 산업 발전대책 2.0」 (2021-08-05) ([korea.kr](https://www.korea.kr/briefing/pressReleaseView.do?newsId=156465017)), but the attached PDF was not read | 64.5 days verified; 100 days **unverified** at primary |
| Utilisation (开工率) | MIIT reports production, not capacity. A Li2CO3 utilisation of 47.08% (2023), attributed to the CNIA lithium branch, was seen only in a third-party report. Weekly 开工率 for cathode, LiPF6 and graphite come from SMM and Mysteel (commercial; not checked) | **No open primary**; cobalt (§10) remains the only anchor. Indicative open proxy: MIIT production ÷ capacity from a single-year capacity source (none found) |

---

## Sources

- CEPII BACI: https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37 ; https://www.cepii.fr/DATA_DOWNLOAD/baci/doc/baci_webpage.html ; https://www.cepii.fr/DATA_DOWNLOAD/baci/doc/release_notes_202601.pdf ; http://www.cepii.fr/PDF_PUB/wp/2010/wp2010-23.pdf
- USGS MCS 2026 data release: https://doi.org/10.5066/P1WKQ63T ; https://www.sciencebase.gov/catalog/item/696a75d5d4be0228872d3bf8 ; https://www.sciencebase.gov/catalog/item/69837e43b66b01367d7ec7c7 ; chapters https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-{cobalt,lithium,graphite,nickel}.pdf
- USGS MYB: https://pubs.usgs.gov/myb/vol1/2023/myb1-2023-cobalt.pdf ; https://pubs.usgs.gov/myb/vol1/2021/myb1-2021-nickel.pdf ; https://pubs.usgs.gov/myb/vol1/2022/myb1-2022-lithium.pdf ; https://pubs.usgs.gov/myb/vol1/2022/myb1-2022-graphite.pdf ; https://pubs.usgs.gov/myb/vol1/2023/myb1-2023-manganese.pdf
- OECD: report 2026 PDF (above); methodological note (above); SDMX https://sdmx.oecd.org/public/rest/dataflow/OECD.TAD.ADM/DSD_QDD_TAD_EXP_RESTRIC@DF_QDD_TAD_EXP_RESTRIC/latest
- GTA: https://globaltradealert.org/data-access ; https://globaltradealert.org/terms ; https://sgeptupload.s3.eu-west-1.amazonaws.com/terms/GTA+Licensed+Data+-+General+Terms.pdf ; https://gtaupload.s3.eu-west-1.amazonaws.com/Uploads/web/GTA+taxonomy.pdf
- EM-DAT: https://doc.emdat.be/docs/data-accessibility/ ; https://doc.emdat.be/docs/legal/terms-of-use/ ; https://doc.emdat.be/docs/protocols/entry-criteria/ ; https://files.emdat.be/docs/emdat_api_python.pdf
- ACLED: https://acleddata.com/eula ; https://acleddata.com/attributionpolicy
- GDELT: https://www.gdeltproject.org/data.html ; https://www.gdeltproject.org/about.html ; http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf
- BOM: https://doi.org/10.1038/s43246-020-00095-x (+ SI); IEA 2021 and GCMO 2025 PDFs (above)
- HS: https://comtradeapi.un.org/files/v1/app/reference/H3.json (and H4, H5, H6); https://rulings.cbp.gov/ruling/N321598
- Literature: DOIs in §9 (Crossref)
- PV: Fraunhofer ISE Photovoltaics Report (2026); IEA Solar PV Global Supply Chains (2022)
- China, MIIT 《全国锂离子电池行业运行情况》 (National Li-ion battery industry operation): https://www.miit.gov.cn/gyhxxhb/jgsj/dzxxsnew/xyyx/art/2026/art_3343e14c0d9a4ddc9fb9f63189aa7c0d.html ; https://www.miit.gov.cn/jgsj/dzs/gzdt/art/2025/art_dc20a4d4b3a74dcf91ac1b212f87bbfc.html ; https://wap.miit.gov.cn/gyhxxhb/jgsj/dzxxs/dzjc/art/2025/art_d39a290e42b542b7a9a688355c52c768.html
- China, NBS: https://www.stats.gov.cn/sj/sjjd/202508/t20250815_1960811.html ; https://www.stats.gov.cn/sj/sjjd/202604/t20260416_1963332.html
- China, MOFCOM 公告 (announcements): 2023 No. 23 http://www.mofcom.gov.cn/zcfb/dwmygl/art/2023/art_52b9a321087f402bb3d310d18b07967e.html ; 2023 No. 39 https://www.mofcom.gov.cn/zcfb/blgg/art/2023/art_f6b1bc49e2c8482f8eb749012bc66dec.html ; 2024 No. 46 https://exportcontrol.mofcom.gov.cn/article/gndt/202412/1068.html ; 2025 No. 28 https://www.mofcom.gov.cn/zcfb/zgdwjjmywg/art/2025/art_67e2a41850ec428eb1b7be6ec2f2bded.html ; 2025 No. 58 https://www.mofcom.gov.cn/zwgk/zcfb/art/2025/art_79646f0161564975a938fe00fee158d5.html ; 2025 No. 70 https://www.mofcom.gov.cn/zwgk/zcfb/art/2025/art_b1ec77dd3f0d4762952904df7cdaadec.html ; 2025 No. 72 https://www.mofcom.gov.cn/zwgk/zcfb/art/2025/art_5c68985a6b1a46778e2e8dbff1bb1601.html
- China, NFSRA (国家粮食和物资储备局): https://www.lswz.gov.cn/html/tzgg/2021-06/16/content_266225.shtml ; https://www.lswz.gov.cn/html/xinwen/2021-07/07/content_266631.shtml
- UN Comtrade tariff line: https://comtradeapi.un.org/public/v1/previewTariffline/C/A/HS ; https://comtradeplus.un.org/Subscriptions
- Japan: METI 生産動態統計 2025 annual (Current Production Statistics) https://www.e-stat.go.jp/stat-search/files?page=1&bunya_l=05&layout=dataset&toukei=00550200&stat_infid=000040475159 ; Customs tariff ch. 28 https://www.customs.go.jp/english/tariff/2026_04_01/data/e_28.htm ; ruling https://www.customs.go.jp/tetsuzuki_search/bunrui/J5/24/J52400298.htm ; JOGMEC https://www.jogmec.go.jp/activities/stockpiling/metal/rare-meta.html
- Korea: KCS API https://www.data.go.kr/data/15100475/openapi.do ; KOMIR https://www.komir.or.kr/kor/contents/59 ; MOTIE https://www.korea.kr/briefing/pressReleaseView.do?newsId=156465017
- EU: Prodcom via Comext SDMX https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/ (DS-059358, DS-059368) ; CN 2026 https://trade.ec.europa.eu/access-to-markets/en/news/combined-nomenclature-and-common-customs-tariff-applicable-eu-1-january-2026 ; RMIS https://rmis.jrc.ec.europa.eu/uploads/bvc/supply.htm
- BGS: https://ogcapi.bgs.ac.uk/collections/world-mineral-statistics ; https://www.bgs.ac.uk/datasets/uk-and-world-mineral-statistics-datasets/
- World Mining Data 2026: https://www.bmf.gv.at/en/topics/mining/mineral-resources-policy/wmd.html
- Chile, Cochilco: https://www.cochilco.cl/web/estadisticas-mineria/ (file 16945)
- Argentina, SIACAM: https://datos.gob.ar/dataset/produccion-mundial-de-litio-tablero-global-del-litio-siacam
- Indonesia: https://peraturan.bpk.go.id/Details/142232/permen-esdm-no-11-tahun-2019
- Zimbabwe: SI 213/2022 (Veritas PDF, §12B)
- DRC: https://www.iea.org/policies/28969 ; https://www.iea.org/policies/29138
- IEA: https://www.iea.org/data-and-statistics/data-tools/critical-minerals-policy-tracker ; https://www.iea.org/data-and-statistics/data-product/critical-minerals-dataset
- WTO: https://qr-notification.wto.org/api/itip/qrs ; https://data.wto.org/dataset/ext_itip_1
- GDACS: https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH ; https://www.gdacs.org/About/termofuse.aspx ; ReliefWeb API https://api.reliefweb.int/v2 ; DesInventar https://www.desinventar.net/

## Unverified

- BatPaC: current version, download terms and per-kWh electrolyte and separator masses (anl.gov blocked). The 2022 "Manual for BatPaC v5.0" (ANL/CSE-22/1) exists per search results only.
- OECD Inventory dataset licence (the terms page is blocked; only the report's CC BY 4.0 was seen).
- GTA: coverage start date; whether free website exports count as "Licensed Data"; academic waiver terms (§9.1.7 not read in full).
- EM-DAT: explicit permission for automated API pulls beyond the existence of first-party API guides.
- ACLED: current registration tiers and access-level restrictions.
- UNCTAD 2023 technical note HS mapping for cathode materials (PDF blocked).
- LiPF6 → 282690 and battery separators → 8507 parts versus 3920 (no ruling checked).
- ITRPV silver mg/W (trade press only).
- Per-mineral IEA lead-time bars (chart values not tabulated).
- Japan's stockpile target days: METI and ANRE pages returned 403. Search snippets say 60 days (30 for some minerals), now mineral-specific and undisclosed. Korea's 100-day target: the MOTIE 2021 attachment was not read.
- MYB 2023 XLSX availability; Lithium, Graphite and Nickel MYB editions later than those listed.
- China State Reserve holdings of battery minerals (none disclosed; no purchase announcement found).
- Chinese 8-digit line descriptions not cited by MOFCOM: 28269020 (LiPF6), 25041091 (spherical graphite), 28332930, 28539040; also the year each line was created.
- Completeness of the Comtrade tariff-line preview (some years return no rows); the UN Comtrade data licence.
- GACC custom-extract terms (page failed TLS; seen via search only); NBS 锂离子电池 series unit and start year.
- CABIA monthly releases at primary (press only); CNIA lithium-branch capacity and utilisation (third-party only).
- Korea HSK 10-digit treatment of CAM and pCAM; KOSIS battery output series.
- Indonesia ESDM/MODI MHP, NiSO4 and HPAL production series; DRC ARECOMS original decisions; DRC Aug 2026 concentrate ban; Zimbabwe Feb 2026 suspension; content of Permen ESDM 11/2019.
- Australia REQ Sep 2026 workbooks (page timed out); IEA Critical Minerals Dataset country grain for refining.
- BGS World Mineral Statistics licence (OGL vs BGS Digital Data Licence); Eurostat Prodcom reuse terms not re-read.
- DesInventar data licence; GDACS terms PDF (Mar 2025) not read; GDACS start year.
