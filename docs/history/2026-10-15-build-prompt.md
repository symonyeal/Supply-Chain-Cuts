# Chokepoint-Lab: build prompt

You are building **Chokepoint-Lab** from nothing to a published result. Work autonomously
through every phase below. Stop only for the user actions listed in §10. The design was
agreed with the user on 2026-10-15. Do not reopen decisions marked *fixed*.
The canonical design is `docs/specs/2026-10-15-chokepoint-design.md`; where this prompt
differs, the spec wins.

Read first, in order:
1. `~/.agents/AGENTS.md` (house rules), then load skills `math-style` and `new-project`.
2. `My Projects/Chokepoint-Lab-brief/RESEARCH.md`: verified sources, endpoints, licences
   and the open questions. It is the evidence base; cite it, extend it, never contradict it
   silently.
3. The sibling repos `Electricity-Market-Model` and `Electric-Fleet-Model`. Copy their
   conventions: result bundles carrying code revision, independent checks, and `run_*.py`
   entry points.

## 1. Question (fixed)

Which minimal sets of (country, product) supply losses stop global lithium-ion cell
production? How likely are they, given the historical record of export restrictions and
natural hazards? Later, answer the same question for Li-ion and PV modules on one shared
network.

Out of scope: firms, investment or price claims, forecasts. This is resilience analysis.

## 2. Decisions (fixed)

| Topic | Decision |
|---|---|
| Nodes | v = (c, p) ∈ V ⊆ C × P. Countries × products, not firms |
| Root product | Li-ion cells first; PV modules added last on the same network |
| Failure | Capacity network with recourse (inventory, spare capacity, lead time); failure = cumulative shortfall > α of demand |
| Cut sets | Exact interdiction MILP with no-good enumeration, checked by brute force |
| Probability | Hybrid: Monte Carlo/importance sampling with data-estimated rates is the headline; exact cut sets give the bound and the attribution |
| Hazards | Policy (OECD ∪ MOFCOM ∪ hand-coded national acts) **and** natural (GDACS) |
| Tooling | Python 3.14 system interpreter, numpy, scipy (`scipy.optimize.milp`/`linprog`, HiGHS). Nothing heavier without a written reason. No thesis `fka` dependency |
| Repo | `My Projects/Chokepoint-Lab`, public GitHub `symonyeal/Chokepoint-Lab`, commit and push to `main` only, licence MIT unless a data licence forces otherwise |

## 3. Data (phase D)

Freeze every input in `data/raw/<source>/` with `SOURCES.lock` (url, retrieval date,
SHA-256, licence). Fetchers are idempotent and verify hashes. Commit raw files only where
the licence permits; otherwise commit the fetcher and hash, and gitignore the file.

| Layer / role | Source (endpoint in RESEARCH.md) | Licence handling |
|---|---|---|
| Trade flows, all layers | CEPII BACI HS12 v202601 (2012–2024) | Etalab 2.0, commit derived tables |
| Mine production | USGS MCS 2026 data release (CSV) | CC0 |
| Refined Co, Ni; Li carbonate by country | BGS World Mineral Statistics OGC API | Licence conflicting: do not commit raw; e-mail BGS (§10) |
| Li chemicals | Cochilco XLSX (Chile), MIIT releases (China), Eurostat Prodcom API (EU) | Cite; MIIT is HTML, transcribe into a YAML with URL per figure |
| China midstream and cells | MIIT 《全国锂离子电池行业运行情况》 national totals | as above |
| Japan cells | METI 生産動態統計 via e-Stat API | needs e-Stat appId (§10) |
| China cathode/precursor/anode flows | UN Comtrade tariff-line API: 28429040, 28539030, 28539050, 2504101000, 2504109100, 3801100030, 3824999940 | preview endpoint (500 rows) chunked by partner; key optional (§10) |
| Export restrictions | OECD Inventory via SDMX (HS2007 → HS2012 concordance) | cite |
| Export-control acts | MOFCOM announcements 2023 No. 23, 2023 No. 39, 2024 No. 46, 2025 No. 28, 2025 No. 58, 2025 No. 70/72; Indonesia ore bans, Zimbabwe Li-ore ban, DRC cobalt suspension: hand-coded in `data/events/acts.yaml`, one primary URL per row | fields: country, HS codes, announce, effect, end, scope (all/destination-specific), status (in force/suspended) |
| Natural hazards | GDACS event feed, orange/red alerts, 2012–2024 | cite |
| Bill of materials | Xu et al. 2020, *Commun. Mater.*, doi:10.1038/s43246-020-00095-x, SI Table 23 (kg per pack) and Table 4 (Wh/kg) | transcribe into `data/bom.yaml`, table and row per number |

Rules:
- Every node capacity carries a label, `production` or `trade`. Trade-based capacity
  (BACI exports) understates integrated producers; claims built on it must say so.
- Layers actually modelled: **mine → refined chemical → (China-observed pCAM/CAM/AAM) →
  cell**. Unobserved non-Chinese midstream is imputed as BOM × cell output and labelled
  `imputed`.
- Cells: BACI tonnes → kWh via Xu Table 4 specific energy; chemistry mix is a stated
  parameter (default NCM622 / LFP split from MIIT if published, else a sweep).
- Reconcile, and record in `docs/DATA.md`: BACI export sums vs USGS/BGS production per
  country; Comtrade China tariff-line sums vs BACI HS6 totals; MIIT totals vs the sum of
  their parts. Report discrepancies; never silently rescale.
- Extend `RESEARCH.md` → `docs/RESEARCH.md` with anything new. Mark unverified claims.

## 4. Model (phase M)

Write `docs/MODEL.md` (definition, claim, proof) and transcribe it one-to-one in code.

**Data.** Capacity u_v (monthly). Input coefficient a_pq (units of p per unit of q).
Demand d_τ, τ = 1..T (months, T = 24). Recourse r = (h, σ, L): initial inventory cover in
months, spare-capacity fraction, ramp-up lead time in months.

**Disruption.** For each node, one disruption level j ∈ {0, 1, …, J} with durations
0 = D_0 < D_1 < … < D_J (default 3, 6, 12 months). Binary z_vj with Σ_j z_vj ≤ 1.
Let δ_τ(v) = 1 if τ ≤ D_j for the chosen j, else 0. Disrupted capacity

  ū_vτ(z) = (1 − δ_τ(v)) · u_v · (1 + σ·min(1, τ/L)).

**Recourse LP.** φ(z) = min Σ_τ g_τ subject to:
- y_vτ ≤ ū_vτ(z) (capacity);
- Σ_w x_vw,τ ≤ y_vτ (shipments ≤ output);
- I_cp,τ = I_cp,τ−1 + Σ_{v=(·,p)} x_v,(c,q),τ − a_pq · y_(c,q),τ, with I_cp,0 = h · use_cp
  (inventory balance);
- Σ_c y_(c,cell),τ + g_τ ≥ d_τ (demand);
- x, y, I, g ≥ 0.

Failure: φ(z) > α · Σ_τ d_τ.

**Monotonicity (prove in MODEL.md).** Order the disruption states by duration. Then
z ≤ z′ implies φ(z) ≤ φ(z′), so failure is an up-set and its minimal elements, the
*cut sets*, are well defined.

**Interdiction MILP.** Write the LP dual. b(z) is affine in z, so φ(z) ≥ θ iff there is a
dual-feasible π with b(z)′π ≥ θ. Linearise z·π with w = z·π under bounds M_v. Derive M_v
exactly: the largest product of 1/a along a path from v to the cell layer, computed by
longest path in the acyclic product graph. Do not guess big-M. Objective min Σ z (or a
weighted version by −log P later), θ = α·Σd + ε.

**Enumeration.** After each solution S add Σ_{(v,j)∈S}(1 − z_vj) ≥ 1. Prove in MODEL.md
that every solution returned in order of non-decreasing |S| is minimal. Stop at |S| > k
(k = 3 default; 4 if runtime allows) or infeasibility.

**Certificates.** For every reported cut set, re-solve the primal LP independently and
store φ(S) and φ(S \ {e}) for each e ∈ S. These are the failure and minimality witnesses.

**Sweep.** α ∈ {0.10, 0.25, 0.50}; D_J grid as above; h ∈ {0, 1, 3} months;
σ ∈ {0, 0.1, 0.5} (0.5 ≈ 271/180 − 1, cobalt refinery capacity over output, MYB 2023); L ∈ {6, 24}
months. Anchor each value to RESEARCH.md or label it an assumption.

## 5. Probability model (phase P)

Implement `docs/specs/2026-10-15-chokepoint-design.md` §5 exactly: natural hazards matched to
production sites (fallback: sensitivity scenario if located sites cover < 70% of a layer),
Beta–binomial marginals pooled by product, within-country correlation ρ with
s_c = ρ · min p_v, bracket L ≤ P(fail) ≤ L + P(|supp Z| > k) (Proposition 3), importance
sampling inside the bracket. Begin phase P with a `research` pass on production-site data.

## 6. Hypotheses (phase H, pre-registered)

Implement spec §6: Day-1 answer, leaves A1–E1 with their kill conditions, certificates and
the fresh-subagent verifier. Commit `docs/HYPOTHESES.md` before any probability result.

## 7. Validation (phase V)

`docs/VALIDATION.md` lists each check and its result:
- `brute`: enumerate all |S| ≤ k on a pruned network (nodes with capacity share ≥ 5% in
  some layer), solve φ directly, reduce to minimal sets. The result must equal the MILP
  list exactly. No shared code with `cuts`.
- LP strong duality: primal = dual objective within eps for every certificate.
- Property tests: monotonicity of φ on random comparable pairs; φ(0) = 0 at baseline
  (current flows are feasible); unit consistency (kWh, t, months).
- Hand-checked toy networks in `tests/` with cut sets derived on paper (TDD: tests
  first, skill `tdd`).
- The [L, U] bracket contains the IS estimate (above).
- Data reconciliations from §3.

## 8. Code layout

Package `chokepoint/`, functions not classes, docstrings stating the problem (math-style):

`fetch.py` (sources → data/raw, hashes) · `bom.py` · `net.py` (V, u, a, labels) ·
`recourse.py` (φ, LP primal and dual) · `cuts.py` (interdiction MILP, enumeration,
certificates) · `brute.py` · `rates.py` (events → q, κ, ψ, durations) · `risk.py`
(L, U, IS, attribution) · `site/` build. Entry points: `run_data.py`, `run_cuts.py`,
`run_risk.py`, `run_site.py`. Results go in `results/<run-id>/` with code revision, data
hashes and parameters. Long runs go in the background; record them as they finish.

Gate: `ruff check`, `pytest -q` (fast suite < 2 min; long benchmarks marked `slow`), CI
on GitHub Actions as `new-project` sets it up.

## 9. Phases and definition of done

Each phase ends with the gate green, a commit to `main` and a push.

| Phase | Done when |
|---|---|
| 0 Scaffold | `new-project` layout; `docs/RESEARCH.md` copied in; spec `docs/specs/2026-10-15-chokepoint-design.md` written from this prompt |
| D Data | All sources frozen with hashes; `net` builds V, u, a with labels; DATA.md reconciliations written |
| M Model | MODEL.md with proofs; `recourse` and `cuts` pass toy tests; φ(0) = 0 on real data |
| V Validation | `brute` = `cuts` on the pruned network for k ≤ 3 across the sweep |
| H Hypotheses | HYPOTHESES.md committed before phase P results exist |
| P Probability | Rates estimated; L, U, IS for the sweep; bracket check passes or failure documented |
| S Site | Skill `insight-site`: answer-first explorer of cut sets by (α, D, r), risk attribution, the bracket, data labels per node; GitHub Pages; `exhibit` for each figure |
| R Report | README answer-first for a general reader; FINDINGS.md; CHANGELOG; release v0.1.0 |
| X Extension | PV modules on the shared network (polysilicon 280461, wafers 381800, cells/modules 854142/854143, HS22 only, 2022–2024); joint cut sets with Li-ion; caveat that polysilicon and wafers share codes with semiconductor material |

Finish with `verification-before-completion`: every claim in README and FINDINGS traces
to a result bundle.

## 10. User actions (ask once, continue meanwhile with fallbacks)

1. Optional free UN Comtrade API key (`COMTRADE_KEY`); fallback is the preview endpoint
   chunked by partner.
2. e-Stat appId for METI data (`ESTAT_APPID`); fallback is the published annual XLSX.
3. A licence enquiry to BGS before publishing BGS-derived tables; until answered, the
   site shows aggregates only and cites BGS.
4. Approval of the repo going public (default: public, as siblings).

## 11. Conduct

- State uncertainty; never fill a data gap from memory. Unverified ⇒ labelled.
- Claims are conditional on (α, D, r) and on the capacity labels; the site and README say
  so in plain words.
- No fabricated numbers, no silent rescaling, no dropped negative results.
- Voice: human, academic, succinct.
