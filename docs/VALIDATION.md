# Validation

## Redundancy refactor checks, 2026-10-30

The [structure review](STRUCTURE.md) accounts for all 1,175 baseline files and
four added modules/documentation files. The 1,039 frozen vendor, input, evidence
and generated files retain their exact bytes. Local checks after the refactor:

| Check | Result |
| --- | --- |
| Release build, formatting, Clippy with warnings denied, Rust tests | Passed; 5 Rust tests |
| Full Python suite, Ruff, installed dependency check | 76 tests passed, none skipped; static/dependency checks passed |
| Native recourse comparison | 192 cases, 5,962 states, all 23,848 numeric fields bit-identical |
| Native networks and context | 64 checks, zero differences; exact context CSV bytes |
| Native site payload | 90,912 JSON nodes agree at full precision and presentation precision |
| Exact union and complete brackets | 432 cases; exact L, attribution, U and tail |
| Seeded native sampling | 12 streams across three sectors and four seeds, including a 64-bit seed; exact categorical states |
| Complete cut searches | Solar, flexible battery, fixed battery, flexible shared network and stock/ramp solar: 22, 7, 37, 100 and 4 cuts; two-way differences empty |
| Python sampler extraction | Before/after binary64 equality for residual, marked partial-loss and pilot-based importance sampling; nonzero failures exercised |
| Runner grid and display labels | All 57/45/2 sector tasks and all 28 page-specific capacity labels unchanged |
| Generated files | Native rebuild of `data.js`, `context.js` and `context.csv` byte-identical to committed files |
| Browser | 417 configurations, 12 responsive/theme views, 8 preference/reload/storage-denial cases; zero page errors |

Comparators rejected planted wrong values and missing keys/states before their
passes were accepted. These checks preserve the measured numerical scope below;
they do not establish a whole-pipeline speedup or extend the scientific model.

## Native Rust pipeline, 2026-10-27

| Check | Measured result |
| --- | --- |
| Recourse primal/dual comparison, `analysis/check_native_model.py` | 192 cases, 5,962 states and 23,848 numerical fields; no structural, missing-key or numerical differences; every compared number binary64-identical |
| Native data comparison, `analysis/check_native_data.py` | 62 network configurations plus context JSON and exact CSV bytes: 64 checks with no differences |
| Native explorer builder, `analysis/check_native_site.py` | 90,912 JSON nodes, including 63,956 scalar/empty-container leaves; full-precision and presentation outputs match Python, and presentation output matches committed `site/data.js` |
| Exact probability kernel, `analysis/check_rust.py` | All 417 saved configurations and 15 boundary cases binary64-identical; saved-value and two-way key differences empty |
| Comparator controls | Incorrect numbers, missing keys and structural changes are rejected before the comparisons are accepted |

The native recourse range uses the reference T = 24 months. Stock cases are limited
to the comparison inputs; other horizons are unmeasured. These results establish
equivalence for their stated inputs, not new empirical support for capacities,
chemistry switchability or policy probabilities. Full native cut-search and
whole-pipeline checks are separate from the LP and payload comparisons.
Whole-pipeline performance is unmeasured.

The `supply` source implements verification, context and network construction,
recourse, cut enumeration, frozen-law risk, payload building and serving directly.
Python remains the independent oracle and historical calibration toolkit. The new
market observations remain separate from the frozen reference model.

## Earlier explorer and optional-kernel checks, 2026-10-27

| Check | Result |
| --- | --- |
| Baseline full Python suite before changes | 45 passed in 134.12 s |
| Full Python suite with Rust executable after implementation | 55 passed in 149.74 s |
| Full-precision Python/Rust comparison | 432 probabilities binary64-identical: 417 saved configurations and 15 boundary cases; no missing keys or saved-value differences |
| Comparator negative controls | Incorrect probability and disjoint-key cases rejected |
| Independent timing of the same complete input batch | Python 30.216494 s; Rust including process/JSON 5.043552 s; 5.991 times faster for this batch |
| Source manifest | 131 sources checked; 76 permitted local-only inputs absent; no committed source missing or changed |
| Offline observational context | 240 production records, 16 refining points, 16 summaries; deterministic JS and 256-row CSV |
| IEA reacquisition | Named chart extracted from the live source and matched the frozen numerical JSON SHA-256 |
| Browser configuration sweep | All 417 saved configurations display the expected cut counts, singletons and lower bound |
| Browser interaction checks | Filtered cut/node downloads, reset, scenario pinning, URL reload, unavailable shared settings, malformed settings and theme button passed |
| Responsive views | 1440, 768 and 390 px in light and dark; no page overflow, unlabelled form inputs, text below 12 px or chain-caption overflow |
| Theme contrast | Muted text 5.03:1 light / 8.44:1 dark; accent 6.07:1 / 9.13:1; chart mark/track contrast at least 3:1 |
| Static checks | Ruff, Rustfmt, Clippy with warnings denied, JavaScript syntax and pip dependency check passed |
| Frozen scientific output | No changes to existing result bundles, reference payload or historical USGS/BACI inputs |

These earlier checks cover the initial optional probability kernel and explorer.
The new context does not certify new cut lists or refit probabilities. Browser values use the existing
five-significant-digit payload; parity uses full-precision result bundles. The batch
timing does not measure whole-pipeline or browser acceleration.

What must be checked, how, and what has been. A check is a certificate (feasibility, a
duality gap, a known optimum from a source), never an output snapshot.

| Claim | Check | Status |
| --- | --- | --- |
| φ on a toy network | Shortfalls derived by hand (`tests/test_recourse.py`) | passing |
| φ is monotone (design Prop. 1) | Random comparable disruption pairs on the toy network | passing |
| Block aggregation exact (Lemma A) | Block LP = monthly LP on 60 random states with h, σ > 0 (`test_blocks_exact`) | passing |
| Lattice search loses no cut (Lemma B) | Lattice = exhaustive on random 3- and 4-layer networks (`test_lattice_equals_brute*`) | passing |
| Cut sets complete and minimal (Prop. 2) | exhaustive = lattice = MILP on the pruned network (share ≥ 5%), k ≤ 3, whole sweep; MILP = lattice on the full network at h = σ = 0 | passing: exhaustive = lattice in 45/45 Li-ion and 45/45 PV configurations; W4 completes all seven previously unfinished MILP legs, exactly equal to their reference lists (`milp-e0b40e2`); full Li-ion α = 10% exhausted in 7,806.9 s, joint pruned α = 25% in 651.9 s; FINDINGS §4 |
| Strong duality at every certificate | primal − dual ≤ 1e-6 and every immediate duration predecessor ≤ θ, for every reported cut | passing: largest gap 4.4e-16 over all Li-ion, PV and joint bundles |
| Bracket and residual estimate (Prop. 3, W1) | Exact L vs hand-enumerated state space; residual vs exact toy and crude MC; positive-width interval with zero residuals | passing: all residual points >= L and within four combined SEs of crude MC in the three `*-residual-2395a5c` bundles; joint alpha = 10% is 0.715669, L = 0.715669, interval 0.715669–0.715853. Original IS point 0.685 retained as a comparison (FINDINGS §2) |
| W1 changes only the estimator | `analysis/check_residual.py BEFORE AFTER`: compare every legacy risk field, networks and cut-file bytes | passing for Li-ion, PV and joint; `residual_checks.json` records clean revisions, unchanged source lock, R3 and R4 |
| W2 export estimator | Independent weighted fixed-effects normal equations; planted 10% tax response; unidentified-type fallback (`test_severity.py`) | passing; real-data S1/S2 untestable under registered minimum counts (DATA) |
| W2 partial loss | Paired endpoint and full-loss toy; samplewise partial shortfall <= full; paired difference interval | `severity-26ebd48`: zero monotonicity violation on all three 20,000-state runs; all assignments are full-loss fallbacks; S3 killed under that rule |
| W2 computation terminal states | Read JSON output, clean stamps, native scalar serialization regression | `severity-16be0a8`: export table written, scenario output failed serialization of a NumPy Boolean; `severity-26ebd48`: all three scenario jobs optimal after native-bool conversion; identical export table |
| Exact frozen bytes survive Git | Disk hashes and committed blob hashes (`analysis/check_inputs.py`), CRLF temporary-repo regression | W5: all 128 on-disk sources verify; all 52 committed sources match (`inputs-7b810a3`); all original 88 hashes unchanged; four earlier newline-normalized CSVs restored without changing frozen hashes |
| Witnesses belong to their displayed cuts (W7) | Recover cut coordinates from every predecessor; independently recompute each full and shortened state | `witnesses-e0b40e2`: 1,700 Li-ion, 179 PV and 424 joint cut certificates checked; maximum difference zero; original bundles immutable |
| Site controls and exhibits (W7) | Builder asserts witness coverage, exact country unions and severity certificates; hidden Edge at 390/1440 px, three nondefault/reset configurations | 16 browser checks, zero JavaScript exceptions or page overflow; predecessors displayed, PV and attribution use shared controls; E1 interval exhibit distinguishes parameter range from uncertainty; U = 100% explained |
| Rate estimator | Planted marginal and ρ recovery; missing exposure stays missing (`test_rates_planted_*`) | passing |
| Network invariants | R_p = Σ a R_q, φ(0) = 0 for Li-ion, PV, joint; basis labels; MYB and MIIT values (`tests/test_net.py`) | passing |
| Events | Derived onsets = research table except Zimbabwe 2022 (`run_data.py`) | passing |
| Data | MIIT parts vs total; exports vs production (DATA.md); Comtrade tariff lines | W5: keyless preview and observed-partner chunks frozen; counts match but precursor/parent totals disagree; no production inference (DATA) |
| Headline numbers | Fresh-subagent recomputation from raw data, sharing no code: 111 nodes, layer shares and S, the 7 singletons at 12 months and none at 6, the COD–IDN pair, all 37 cuts failing and minimal, 884/61 node-years, ρ, L = 0.485766 exact and by 2,000,000 Monte Carlo draws | passing (2026-10-15); one documented definitional difference in duration counts (DATA.md) |

## W3: alternative recipes

`tests/test_recipes.py` checks the hand-derived LFP route, bounded-share duals,
monthly/block equivalence, capacity dominance, random exhaustive/lattice/MILP equality,
baseline-failure empty cuts, and the restored-second-year share equivalence on 40
random states. The single LP matrix construction supplies the primal and MILP dual.
All 94 saved cut configurations are complete with certified primal/dual values and
immediate duration predecessors. Both registered singleton claims survive; every
former Co/Ni/pCAM headline cut is explicitly restated in CHEMISTRY. Risk checks the
unchanged network, rate law and feasible monthly 50/50 reference before reusing the
same failure event for the bounded interval. These are model certificates, not
evidence that actual plants can change chemistry.

## W6: fresh independent PV/shared reconstruction

Fresh agent, no production code, tests, analysis or result access. Portable programs
and named comparison inputs: `independent/pv_joint`; immutable report and numerical
artifacts: `results/independent-pv-joint`. The agent separately parsed BACI, USGS,
OECD SDMX, all 1,521 exposure rows from the methodology PDF, and selected primary
workbook/SI cells. All checked frozen hashes match. No coverage-row discrepancy.

Independent enumeration gives exactly 22 PV cuts (4/5/13 by support) and 180 fixed-mix
joint cuts (0/61/119). It visits 13,275 PV states and 2,802,195 mixed joint states;
no supplied cut is missing and no additional cut appears. Separate monthly LPs check
all 202 cuts and 532 predecessors; the greatest difference from the independent
cumulative-output recurrence is 2.998e-15. Independent L values are
0.2444939846405121 (PV) and 0.20382804118895667 (joint), versus production
0.2444939846075459 and 0.2038280411830003: numerical rate-fit differences below
3.3e-11. Counts (4,3,169), rho = 0.6557026896815004 and the roster agree.

Two diagnosed definition issues are retained in the report. Linked OECD/national
records count separately in duration weighting but once in node-year onset counts;
deduplicating durations would give (2,3,167). The preserved independent HHI output
initially omitted excluded origins from its numerator, changing cobalt/CAM rounding;
the portable script uses all origins. Neither issue changes the accepted cut/L
comparison. MIIT/Fraunhofer transcriptions, product mapping, legal completeness,
censoring and whole-node outage severity remain shared assumptions. W6 validates
the fixed-mix PV/shared headlines, not the later chemistry-choice scenario or the
predictive validity of rates. Raw excerpts with unverified reuse terms remain local.


## W8: located-capacity coverage

`results/sites-4ae36c1/site_coverage.json`, producer `4ae36c1`, clean stamp,
recomputes all 18 active joint-model layers. Each denominator is the sum of retained
annual physical output, with its own kt/GWh/GW unit; all verified located-capacity
numerators are zero. The candidate records have no coordinates; the frozen global
and US facility workbooks provide administrative/location text, not coordinate
fields, and no midstream/cell table exists. No administrative centroid is labelled
as a measured plant. The registered 70% threshold fails in every layer; hazard
matching remains unmeasured and country-wide loss fractions remain scenarios.
This is the terminal coverage audit, not a claim that site geocoding was completed.


## W5: source and allocation checks

Full gate: 40 tests passed, including both supply-accounting tests. METI kAh-to-GWh
conversion and imputed labels are checked at 3.2/3.7 V. A reservation toy verifies
unchanged demand and exposes a baseline shortfall instead of rescaling it away.
`data.research.supplement` regenerated all selected observations and reconciliation
bytes exactly. All nine disjoint partner batches reproduce the three nonempty
preview multisets; neither that check nor counts below 500 prove completeness.
The five Eurostat slices retain quantity flags; combined German carbonate equals
the two purity-category estimates. Missing/confidential is never converted to zero.

All 14 `supply-4ae36c1` cases have complete lists and optimal baseline certificates,
with zero dirty paths. N1 survives (67.794261% fixed-mix baseline shortage); N2
survives (75.341298% fixed / 74.819450% choice at 1% Cu/Al/Mn). METI changes choice
cuts 7 -> 6; German sold-carbonate proxy 7 -> 7. Capacity-source variants do not
reuse a newly fitted probability or claim independent recomputation of W3/W5.

Final v0.3.0 gate (2026-10-17): 40 passed in 86.51 s; ruff: All checks passed; pip: No broken requirements found; all 128 sources verify and all 52 committed input blobs match. Final browser audit: 22 checks at 390/1440 px, including choice/fixed mode counts, shared controls and all 14 supply rows; zero JavaScript exceptions or page overflow.
