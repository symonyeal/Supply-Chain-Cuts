# Chokepoint-Lab: design

Implementation clarifications (2026-10-15): [MODEL](../MODEL.md) specifies the dual sign,
immediate-duration predecessor certificates and upper-orthant exclusions. Exact-state
no-goods alone do not remove longer-duration supersets. Enumeration reports completeness
only after solver-proven exhaustion; time limits remain incomplete. A missing supplier
does not remove the corresponding material balance. Joint Li-ion/PV output is normalised
by sector annual demand before aggregating shortages. Policy licensing onsets are not
observed full production outages; absent measured severities, risk is a scenario. The
strict 25% boundary over a 24-month horizon is retained.

Implementation clarifications (2026-10-15, second session): capacities are measured in
years of requirement and the LP is aggregated exactly over blocks of constant data
([MODEL](../MODEL.md), Lemma A). Refined cobalt uses USGS MYB 2023 Table 8 refinery
production (public domain), replacing the BGS source while its licence is unresolved;
China LiOH is converted to LCE as the monohydrate (GB/T 26008-2020). The MILP did not prove
exhaustion within 600 s on the 108-node network (24 monthly periods), so full-network cut lists come from the
lattice search in `brute.py` (Lemma B), which shares no code with `cuts.py`; the MILP
certifies agreement on the pruned network over the sweep and on the full network where it
completes. Products without event exposure borrow the all-product empirical-Bayes prior;
a Jeffreys prior (mean 0.5) is not a credible annual rate. Policy onsets are derived in
`chokepoint/events.py` from the frozen OECD records and national acts.

Agreed with the user, 2026-10-15, through brainstorming Sections 1–5. Evidence base:
`docs/RESEARCH.md` (primary sources, verified 2026-10-15). This spec is canonical; where
`PROMPT.md` differs, this file wins.

## 1. Question and scope

**Question.** Which minimal sets of (country, product) supply losses stop global
lithium-ion cell production, and how likely are they each year? The reader is someone
deciding where supply diversification pays.

**Scope.** Li-ion cells (v0.1.0); then Li-ion and PV modules on one shared network
(v0.2.0). Out of scope: firms, investment or price claims, forecasting.

**Tooling.** System Python 3.14, numpy, scipy (`scipy.optimize.milp`, `linprog`; HiGHS).
House style per skill `math-style`. Public repo `symonyeal/Chokepoint-Lab`, `main` only.

## 2. Architecture

| Module | Input → output |
|---|---|
| `fetch` | sources → `data/raw/<source>/`, `SOURCES.lock` (url, date, SHA-256, licence) |
| `bom` | Xu et al. 2020 SI Tables 4, 23 → `data/bom.yaml`: a_pq and Wh/kg, one citation per number |
| `net` | fetched data + `bom` → V, u_v, a_pq; each u_v labelled `production`, `trade` or `imputed` |
| `recourse` | network, z, r → φ(z) (primal LP) and its dual |
| `cuts` | interdiction MILP + no-good enumeration → 𝒮_k with certificates |
| `brute` | exhaustive check of `cuts` on a pruned network; shares no code with `cuts` |
| `sites` | production-site coordinates → node capacity shares by location |
| `rates` | event records → p_v, ρ, duration distribution |
| `risk` | rates, 𝒮_k, φ → L, U, IS estimate, attribution |
| `site/` | precomputed JSON → GitHub Pages explorer |

Flow: `fetch → net → {cuts, rates, sites} → risk → site`. Results in
`results/<run-id>/` carry code revision, data hashes and parameters. Entry points
`run_data.py`, `run_cuts.py`, `run_risk.py`, `run_site.py`.

## 3. Data

| Role | Source | Licence handling |
|---|---|---|
| Trade flows, all layers | CEPII BACI HS12 v202601, 2012–2024 | Etalab 2.0 |
| Mine production | USGS MCS 2026 data release | CC0 |
| Refined Co, Ni; Li carbonate | BGS World Mineral Statistics OGC API | licence conflicting: raw not committed until BGS answers |
| Li chemicals | Cochilco XLSX (Chile); MIIT releases (China); Eurostat Prodcom (EU) | MIIT transcribed to YAML, URL per figure |
| China midstream, cells | MIIT 《全国锂离子电池行业运行情况》 national totals | as above |
| Japan cells | METI 生産動態統計 via e-Stat | appId from user; fallback annual XLSX |
| China pCAM/CAM/AAM flows | UN Comtrade tariff lines 28429040, 28539030, 28539050, 2504101000, 2504109100, 3801100030, 3824999940 | preview endpoint chunked by partner; free key optional |
| Policy events | OECD Inventory (SDMX, HS2007 → HS2012 concordance); MOFCOM announcements 2023 No. 23, 2023 No. 39, 2024 No. 46, 2025 No. 28, 2025 No. 58, 2025 No. 70/72; national acts (Indonesia ore, Zimbabwe Li ore, DRC cobalt) in `data/events/acts.yaml`, one primary URL per row | cite |
| Natural events | GDACS orange/red alerts, 2012–2024, with coordinates | cite |
| Production sites | to be researched at phase P start (USGS mineral-site data; public refinery and cell-plant lists) | per source |

**Modelled layers.** Mine → refined chemical → midstream (pCAM, CAM, AAM: China-observed
from tariff lines; other origins imputed as BOM × cell output) → cell. Cells: BACI tonnes
→ kWh by Xu Table 4 specific energy; chemistry mix is a stated parameter.

**Reconciliations**, written to `docs/DATA.md`, never silently rescaled: BACI exports vs
USGS/BGS production by country; Comtrade China tariff-line sums vs BACI HS6; MIIT parts
vs MIIT totals.

## 4. Model

**Data.** v = (c, p) ∈ V ⊆ C × P; capacity u_v (monthly); a_pq units of p per unit of q;
demand d_τ, τ = 1..T, T = 24 months. Recourse r = (h, σ, L): inventory cover (months),
spare-capacity fraction relative to current output, ramp-up lead time (months).

**Disruption.** States j ∈ {0, …, J} with durations 0 = D_0 < D_1 < … < D_J
(3, 6, 12 months). Binary z_vj, Σ_j z_vj ≤ 1. δ_τ(v) = 1 if τ ≤ D_j for the chosen j,
else 0. Disrupted capacity ū_vτ(z) = (1 − δ_τ(v)) · u_v · (1 + σ · min(1, τ/L)).

**Recourse LP.** φ(z) = min Σ_τ g_τ subject to:
- y_vτ ≤ ū_vτ(z);
- Σ_w x_vw,τ ≤ y_vτ;
- I_cp,τ = I_cp,τ−1 + Σ_{v=(·,p)} x_v,(c,q),τ − a_pq · y_(c,q),τ, with I_cp,0 = h · use_cp;
- Σ_c y_(c,cell),τ + g_τ ≥ d_τ;
- x, y, I, g ≥ 0.

Failure: φ(z) > α · Σ_τ d_τ.

**Proposition 1 (monotonicity).** With states ordered by duration, z ≤ z′ implies
φ(z) ≤ φ(z′). *Proof.* ū(z′) ≤ ū(z) componentwise, so the feasible set under z′ is
contained in that under z. Hence failure is an up-set; its minimal elements are the cut
sets, each a set of (node, minimum duration) pairs.

**Interdiction MILP.** By LP duality φ(z) = max_π b(z)′π over the dual polyhedron, with
b(z) affine in z. Then φ(z) ≥ θ iff some dual-feasible π has b(z)′π ≥ θ. Linearise z·π
by w with bounds M_v = the largest product of 1/a along a path from v to the cell layer,
computed by longest path in the acyclic product graph. Solve min Σ z subject to these
constraints and θ = α · Σ d + ε.

**Enumeration.** After each solution S add Σ_{(v,j)∈S}(1 − z_vj) ≥ 1. Stop at |S| > k
(k = 3; 4 if runtime allows) or infeasibility.

**Proposition 2 (minimality).** Each returned S is minimal. *Proof.* Suppose a proper
subset S′ ⊊ S fails. S contains no earlier solution, hence neither does S′. S′ is then
feasible for the same MILP with |S′| < |S|, contradicting optimality.

**Certificates.** For each S ∈ 𝒮_k store φ(S) and φ(S ∖ {e}) for every e ∈ S, from an
independent primal solve, with primal–dual gap ≤ eps.

**Sweep.** α ∈ {0.10, 0.25, 0.50}; D_J ∈ {3, 6, 12}; h ∈ {0, 1, 3}; σ ∈ {0, 0.1, 0.5}
(0.5 ≈ 271/180 − 1, cobalt refinery capacity over output, MYB 2023); L ∈ {6, 24}.
Each value is anchored in RESEARCH.md or labelled an assumption.

## 5. Probability

**Time.** Annual, 2012–2024. At most one onset per node per year. Onsets in one year are
treated as overlapping, which is conservative.

**Events.** E_pol = OECD ∪ MOFCOM ∪ acts.yaml, product-specific; duplicates merged by a
written rule; announced-then-suspended measures kept with zero duration. E_nat = GDACS
orange/red alerts.

**Natural hazards → nodes.** A hazard disrupts node v by the share of v's capacity at
sites inside the alert area (`sites`). Countries with a single known site use the
country-wide rule. *Fallback,* if located sites cover < 70% of capacity in
any layer (checked before any matching, recorded in DATA.md): natural hazards become a sensitivity scenario at
fixed loss fractions, and the headline rests on policy events alone.

**Rates.** Thirteen years cannot identify a separate country shock and per-product
sensitivity, so:
- Marginals p_v ~ Beta(a_p, b_p), pooled by product; (a_p, b_p) by empirical Bayes
  (beta-binomial likelihood over node-years).
- Within-country correlation: one ρ ∈ [0, 1] per hazard type. Country c has a shock with
  probability s_c = ρ · min_{v∈c} p_v that disrupts all its nodes together; otherwise
  node v fails independently with p′_v = (p_v − s_c)/(1 − s_c), so marginals stay p_v
  (s_c ≤ p_v by construction). ρ = 0 is independence. ρ is fitted to the observed
  frequency of multi-product same-year events.
- Durations: empirical OECD/MOFCOM distribution binned onto D_1..D_J.

**Proposition 3 (bracket).** Let Z be the random disruption state and
L = P(∪_{S∈𝒮_k} {S ⊆ Z}). Then L ≤ P(fail) ≤ U := L + P(|supp Z| > k). *Proof.* Every
failing state contains a minimal cut set (Proposition 1). If one has size ≤ k it is in
𝒮_k, by completeness of the enumeration; otherwise |supp Z| > k.

**Computation.** L: condition on the shocks of the m countries in 𝒮_k (2^m cases); given
those, nodes are independent and the union probability is exact by inclusion–exclusion
or a decision diagram. P(|supp Z| > k): exact convolution of per-country count
distributions, each mixed over its country shock. Estimate: importance sampling with a
cross-entropy proposal tilted toward nodes in 𝒮_k, with 95% CI. Attribution: P(S ⊆ Z)/L
per cut set, summed by country and product; shares overlap and may exceed 1.

## 6. Hypotheses and validation

Pre-registered in `docs/HYPOTHESES.md`, committed before any probability result exists.

**Day-1 answer.** At α = 0.25, D ≥ 6, h = σ = 0: (China, graphite) is a size-1 cut set;
≥ 80% of L is carried by cut sets containing a Chinese midstream node; annual P(fail) ∈
[1%, 10%].

**Tree and kill conditions.**

| Leaf | Test | Kill condition |
|---|---|---|
| A1 network vs concentration (steelman) | Spearman of cut-set attribution vs HHI/top-share by product | ≥ 0.9 ⇒ report "concentration suffices" |
| B1 re-export hubs (premortem) | flag nodes with exports > production; rerun without them | a cut set that vanishes is withdrawn as artefact |
| B2 capacity basis | rerun with China midstream from MIIT production totals | changed cut sets reported as basis-dependent |
| C1 chemistry substitution (weakest rung) | LFP/NCM mix as bounded decision variable | Co/Ni cut sets that vanish are restated as conditional on mix |
| D1 rate predictiveness | fit 2012–2019, prequential log-loss 2020–2024 vs pooled constant | no improvement ⇒ probabilities downgraded to scenarios; only [L, U] under stated rates |
| E1 sensitivity | tornado over h, σ, L, D, α | ranks the inputs; no kill |

**Certificates.** `brute` = `cuts` on the pruned network (nodes with ≥ 5% share in some
layer), k ≤ 3, whole sweep. Strong duality on every certificate. IS estimate within
[L, U]; agreement with crude MC where failure is not rare. Data reconciliations (§3).
Hand-derived toy networks in `tests/` (test-first). Planted-truth recovery of p_v and ρ
on synthetic events. Before publication, a fresh subagent recomputes every headline
number from raw data.

Every outcome, rejections included, goes to `docs/FINDINGS.md`.

## 7. Deliverables

| Item | Content |
|---|---|
| README | Answer first for a general reader: [L, U], top cut sets, what the data cannot show |
| docs | MODEL (Props 1–3 with proofs), DATA, RESEARCH, HYPOTHESES, VALIDATION, FINDINGS, CHANGELOG |
| results | bundles with revision, hashes, parameters |
| site | `insight-site` pattern on GitHub Pages; one control set (α, D, h, σ, L) drives: Answer; Cut sets with witnesses; Network by layer with capacity labels; Attribution; Kill conditions; Provenance. Figures per `exhibit` |
| releases | v0.1.0 Li-ion; v0.2.0 PV on the shared network (polysilicon 280461, wafers 381800, cells/modules 854142/854143; HS22 only, 2022–2024; shared-code caveat) |

Gate: `ruff check`, `pytest -q` (fast < 2 min; long runs marked `slow`), GitHub Actions.

## 8. User actions

1. Optional UN Comtrade key (`COMTRADE_KEY`).
2. e-Stat appId (`ESTAT_APPID`).
3. Licence enquiry to BGS before publishing BGS-derived tables.
4. Confirm the repo is public.
