# Decisions

Each entry: the decision, the alternatives measured, the measurement, the date.

Decisions taken with the user during design (2026-10-15) are recorded in the
[design](specs/2026-10-15-chokepoint-design.md): country × product nodes over firms;
Li-ion first, then PV; capacity network with recourse; exact interdiction checked by brute
force; hybrid probability (bounds, then importance sampling); policy and natural hazards,
with natural hazards matched to production sites.

## Taken in implementation (2026-10-15)

- **Refined cobalt from USGS MYB 2023 Table 8, not the BACI export proxy.** The proxy put
  88% of refined cobalt in the DRC (HS 810520 hydroxide mass, 635 kt, above world mine
  output) and omitted China, whose exports are 5.3 kt against 147 kt produced. BGS stays
  unused while its licence is unresolved.
- **LiOH converted to LCE as the monohydrate** (0.880 t/t, GB/T 26008-2020), not anhydrous
  (1.543): China's LCE is 987 kt, not 1,225 kt.
- **Requirement units and exact blocks (Lemma A).** With 24 monthly periods the MILP found 12
  of 37 cut sets in 600 s; with 4 blocks it proved exhaustion in 1,236 s (108 nodes) and in
  3,583 s (111 nodes). Rescaling makes every capacity dual bound 1.
- **Lattice search for full-network cut lists (Lemma B).** 13.8 s and 3,714 LPs against
  427 s and 107,416 LPs without the minimality rules; the MILP certifies it where it completes.
- **All-product empirical-Bayes prior for unexposed products**, not Jeffreys: a Jeffreys
  prior gives cells, CAM, pCAM and AAM an annual onset rate of 0.5.
- **Demand equals the undisrupted achievable output** (PV 0.991 of retained modules), so
  φ(0) = 0 and the strict 25% argument of HYPOTHESES holds.
- **Raw files are committed only under verified open terms** (BACI, USGS, Xu et al., OECD
  report) or as transcribed facts; OECD dataset extracts, GDACS, MOFCOM and national acts
  stay local, hash-locked in `SOURCES.lock`.
- **Day-1 (ii) uses the design's midstream (pCAM, CAM, AAM).** The first implementation also
  counted refined chemicals; the definition was corrected before the registered result was
  written, and both readings are reported.
- **B1 is reported literally and narrowly**: cut sets that disappear in the rerun, and cut sets
  that contain a flagged node; the rerun also lowers demand, which the literal rule ignores.
- **Post hoc scenario**: onsets restricted to quotas and prohibitions (OECD M3, M4). Not
  registered; reported as such.
- **Not done**: Comtrade China tariff lines (optional key not supplied), e-Stat Japan cells
  (appId not supplied), BGS (licence).

## 2026-10-16

- **Preserve input bytes in Git (#3).** Four committed CSVs differed from their frozen
  hashes solely because of CRLF conversion (`results/input-bytes-1e7ce2f/checks.json`).
  Their already-verified local bytes are restored to the index; raw files and their
  frozen hashes are unchanged. Git attributes disable conversion for data and the lock.
- **XLS reader for the UN concordance (W2).** The primary workbook is an XLS file, not
  an XLSX; no XLS reader was installed. Added xlrd 2.0.2 (96 kB download). Its one-to-one
  numerical facts are frozen separately; the unlicensed raw workbook stays local.

- **Lower bound plus residual is the reported estimator (W1).** The original joint
  alpha = 10% IS point was 0.684868 below exact L = 0.715669; crude MC was 0.722750.
  New seeded residual draws give 0.715669 (95% interval 0.715669–0.715853). At alpha =
  25%, sample residual SEs are 0, 0 and 0.000335 for Li-ion, PV and joint, against crude
  SEs 0.003535, 0.003057 and 0.002849. The three comparison certificates confirm every
  legacy risk number, network and cut-file byte is unchanged. Zero residuals receive
  a positive-width binomial interval; probabilities remain scenarios.
- **Severity study uses the first full calendar year after onset (W2).** Approved by
  the user; annual trade cannot identify a response within exactly twelve months.
  Controls, exclusions and conversion to capacity scenarios are in the dated design.
  No severity result existed when S1–S3 were registered at `aac556d`.
- **Do not manufacture severity from unidentified responses (W2).** Only four isolated
  events survive, and no measure reaches five. S1/S2 are untestable; all capacity marks
  use the declared full-loss fallback. The site reuses W1's estimator because the laws
  are identical and reports the paired MC reduction separately. Zero reduction does not
  imply actual policies remove full capacity. Expanding the selected HS set or relaxing
  overlap/coverage rules requires a new registered study, not a change after seeing this result.
- **Recover frozen cut witnesses by predecessor coordinates.** Old runs sorted their
  cut lists but stored certificates in enumeration order. Predecessor node and shortened
  duration uniquely recover the cut. The builder uses that key; future runs align the
  lists explicitly. Original bundles remain immutable; cut membership and risk are unchanged.
- **Close W4 with longer unseeded solves.** All seven outstanding MILP legs exhausted
  and exactly matched the lattice lists; the full alpha = 10% run took 7,806.9 s.
  No model strengthening was needed. Original time-limited bundles remain immutable.

## Open

- Natural-hazard site data: located capacity is 0% in every layer (no frozen site table has
  coordinates for capacity), below the 70% threshold, so the sensitivity fallback applies
  (design §5). A located capacity inventory would reopen site matching.

## Tested and refused

- GDELT as an event source: no product field ([Research](RESEARCH.md) §7).
- ACLED, Global Trade Alert: licence terms restrict publication ([Research](RESEARCH.md) §4, §6).
- WTO QR notifications: no filings from the producer countries that matter ([Research](RESEARCH.md) §12).

### 2026-10-16 — keep chemistry flexibility distinct from measured production

Use the approved shared-capacity recipes and 24-month delivered-output share bounds.
Measured outcome: five rather than seven singleton cuts, seven rather than 37 cuts;
all 29 former cobalt/precursor cuts have zero shortfall. Actual line switchability
is unknown. The [25%,75%] bound is nonbinding by the restored-second-year argument,
so identical results are not evidence of robustness to binding chemistry quotas.
The site defaults to choice, offers the fixed-mix reference in the same cut controls,
and explicitly retains fixed-mix labels on the severity study and E1 exhibit.
