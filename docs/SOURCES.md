# Sources

A method is validated by the source it implements. Cite only what this file records, and
add the entry in the change that uses it. Status is **inspected** (read for this project,
with what was read and when) or **cited** (not yet read). Data sources, endpoints and
licences are in [Research](RESEARCH.md).

| Source | Used for | Status |
| --- | --- | --- |
| Wood, R.K., Deterministic network interdiction, *Math. Comput. Modelling* 17(2):1–18, 1993, doi:10.1016/0895-7177(93)90236-R | Single-level interdiction MIP by dualising the inner LP (design §4) | cited (Crossref record verified 2026-10-15) |
| Israeli, E., Wood, R.K., Shortest-path network interdiction, *Networks* 40(2):97–111, 2002, doi:10.1002/net.10039 | Dual-based single-level MIP; supervalid inequalities | cited (Crossref record verified 2026-10-15) |
| Brown, G., Carlyle, M., Salmerón, J., Wood, K., Defending critical infrastructure, *Interfaces* 36(6):530–544, 2006, doi:10.1287/inte.1060.0252 | Attacker–defender model with the operator's recourse LP inside (design §4) | cited (Crossref record verified 2026-10-15) |
| Snyder, L.V. et al., OR/MS models for supply chain disruptions: a review, *IIE Trans.* 48(2):89–109, 2016, doi:10.1080/0740817X.2015.1067735 | Inventory and recourse under disruption | cited (Crossref record verified 2026-10-15) |
| Xu, C., Dai, Q., Gaines, L., Hu, M., Tukker, A., Steubing, B., Future material demand for automotive lithium-based batteries, *Commun. Mater.* 1:99, 2020, doi:10.1038/s43246-020-00095-x | Bill of materials: SI Table 23 (kg per pack), Table 1 (66 kWh pack), Table 4 (Wh/kg) | inspected (SI pp. 42, tables 1, 4, 23; 2026-10-15) |
| USGS, *Cobalt in 2023*, Minerals Yearbook vol. I, advance release, Table 8 (posted 2026-03-16), https://pubs.usgs.gov/myb/vol1/2023/myb1-2023-cobalt.xlsx | Refined cobalt output by country, 2023 (t Co); China 147,000e of 180,000 | inspected (T8, column K; 2026-10-15) |
| SAMR/SAC, GB/T 26008-2020 电池级单水氢氧化锂 (battery-grade lithium hydroxide monohydrate) | Monohydrate as the battery-grade form; LCE factor 0.880 | cited (title and scope verified via chinesestandard.net, 2026-10-15) |
| MIIT 电子信息司, 2024年全国锂离子电池行业运行情况 (2025-02-27) | China 2024 cell, CAM, AAM, Li2CO3 and LiOH output | inspected (page text, 2026-10-15) |
| OECD, Inventory of Export Restrictions on Industrial Raw Materials, SDMX dataflow DSD_QDD_TAD_EXP_RESTRIC, measure codes M1–M14 | Policy onsets 2012–2024; M3 quota and M4 prohibition for the post hoc hard-measure scenario | inspected (structure codelist, 2026-10-15) |
| Rubinstein, R.Y., Kroese, D.P., *The Cross-Entropy Method*, Springer, 2004 | Cross-entropy tilting of the importance-sampling proposal | cited |
| Clopper, C.J., Pearson, E.S., The use of confidence or fiducial limits illustrated in the case of the binomial, *Biometrika* 26(4):404–413, 1934, https://doi.org/10.1093/biomet/26.4.404 | Binomial tail inversion for residual-estimator Monte Carlo intervals | inspected (original paper, binomial tail construction pp. 406–407; 2026-10-16) |
| CEPII, BACI HS12 V202601, annual members 2012–2023, https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_HS12_V202601.zip | W2 exporter–HS6–year export quantities; original selected rows and complete-member digests in SOURCES.lock | inspected (12 byte-range extracts, member CRC and length checked; 2026-10-16); Etalab 2.0 as recorded in RESEARCH §1 |
| UNSD, HS 2012 to HS 2007 Correlation and conversion tables, https://unstats.un.org/unsd/trade/classifications/tables/HS%202012%20to%20HS%202007%20Correlation%20and%20conversion%20tables.xls | Verified one-to-one codes for W2; `data/events/hs07_hs12.json` records numerical concordance facts | inspected (correlation sheet; 2026-10-16); raw workbook local and hash-locked because reuse terms are unverified |

## Nickel metal source sensitivity, 2026-10-20

| Source | Used for | Status |
| --- | --- | --- |
| USGS, [Nickel in 2023, tables-only release](https://www.usgs.gov/media/files/nickel-2023-tables-only-release), published 2025-06-17; [workbook](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/myb1-2023-nicke-ERT.xlsx) | Table T12 country metal production, 2023, metric tonnes nickel content; column K and qualifier column L | inspected 2026-10-20; landing page states Public Domain; exact workbook and ten-row transcription frozen in SOURCES.lock, including cells and estimated flags |

Table T12 footnote 2 distinguishes metal, generally equivalent to INSG Class I, from
chemicals, ferronickel/NPI and oxide sinter. It does not certify battery grade or installed
capacity. Footnote 1 dates available data to 2024-11-13 and describes estimate/total
rounding; France's country footnote 5 includes metal and nickel chloride. The sensitivity
uses only the explicitly labelled metal row, not the country total or chemicals row.

## W5 source audit

| Source | Used for | Status |
| --- | --- | --- |
| METI, Current Production Statistics 2024, annual workbook h2daa2024k, e-Stat statInfId 000040293825, https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040293825&fileKind=0 | Sealed Li-ion production charge, items 0108/0109, actual-values rows 3488/3498, months I:T | inspected 2026-10-16; e-Stat terms section 6(c) permits CC BY 4.0 reuse; 24 numerical observations extracted by `data/research/supplement.py` |
| Eurostat, DS-059358, 2024 Prodcom; SDMX data/structure endpoints in SOURCES.lock | Sold lithium oxide/hydroxide, carbonate purity categories and LFP; quantities, confidentiality/rounding flags, definitions | inspected 2026-10-16; statistical-data reuse authorised with attribution (copyright notice, Decision 2011/833/EU); only EU production indicators selected for redistribution |
| Eurostat, Copyright notice and free re-use of data, https://ec.europa.eu/eurostat/web/main/help/copyright-notice | Reuse scope and attribution for W5 | inspected 2026-10-16; transformed-data attribution and non-responsibility statement included in reconciliation.json |
| UNSD, public Comtrade tariff-line preview, https://comtradeapi.un.org/public/v1/previewTariffline/C/A/HS | China 2024 exports, seven requested national lines; disjoint observed-partner checks; HS22 BACI parent-code diagnostics | inspected 2026-10-16; raw local and hash-locked, reuse licence unverified; missing rows are not zero trade; repeated reporting keys prevent claiming independent unique flows |
| Cobalt Institute, Cobalt Market Report 2024 factsheet, https://www.cobaltinstitute.org/wp-content/uploads/2025/06/Cobalt-Market-Report-2024_Factsheet.pdf | Global battery consumption share 43% EV + 30% portables + 3% other batteries = 76% (page 2) | inspected 2026-10-16; numerical facts transcribed, raw local, reuse licence unverified |
| INSG, The World Nickel Factbook 2024, https://insg.org/wp-content/uploads/2024/09/publist_The-World-Nickel-Factbook-2024.pdf | Estimated 2023 primary-nickel battery-use share about 16%, printed page 32 | inspected 2026-10-16; numerical fact transcribed, raw local, reuse licence unverified |
| KOSIS and Korea Battery Industry Association, https://kosis.kr/ and https://www.k-bia.or.kr/ | Search for domestic physical cell output | inspected public search/home page 2026-10-16; no qualifying annual physical series located; KBIA industry pages repeatedly redirect; trade basis retained |
| Statistics Finland, PRODCOM 2024 classification, https://stat.fi/en/luokitukset/prodcom/prodcom_1_20240101 | Reference-year verification of lithium carbonate and LFP product codes, valid from 2024-01-01 | inspected 2026-10-17; cross-check against frozen Eurostat codelist |
| Eurostat, European business statistics compilers' manual for PRODCOM, 2024 edition, doi:10.2785/46653, https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/w/ks-gq-23-022 | Sold versus actual quantity, confidentiality and E/U reliability flags, printed pp. 23–29 | inspected 2026-10-17; source PDF and flags checked; no production figure inferred from confidential quantity |
| Eurostat, PRODCOM user manual, dissemination chapter, https://ec.europa.eu/eurostat/documents/3859598/16130157/KS-GQ-22-014-EN-N.pdf/3751d778-9c44-2f51-0b20-49a1fd053f04?t=1676566349800&version=2.0 | C/E/U/R dissemination flags and rounded EU totals, printed p. 28 | inspected 2026-10-17; R is rounded, not an unflagged exact quantity |
