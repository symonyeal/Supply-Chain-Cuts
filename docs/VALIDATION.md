# Validation

What must be checked, how, and what has been. A check is a certificate (feasibility, a
duality gap, a known optimum from a source), never an output snapshot.

| Claim | Check | Status |
| --- | --- | --- |
| φ on a toy network | Shortfalls derived by hand (`tests/test_recourse.py`) | passing |
| φ is monotone (design Prop. 1) | Random comparable disruption pairs on the toy network | passing |
| Block aggregation exact (Lemma A) | Block LP = monthly LP on 60 random states with h, σ > 0 (`test_blocks_exact`) | passing |
| Lattice search loses no cut (Lemma B) | Lattice = exhaustive on random 3- and 4-layer networks (`test_lattice_equals_brute*`) | passing |
| Cut sets complete and minimal (Prop. 2) | exhaustive = lattice = MILP on the pruned network (share ≥ 5%), k ≤ 3, whole sweep; MILP = lattice on the full network at h = σ = 0 | passing: exhaustive = lattice in 45/45 Li-ion and 45/45 PV configurations; MILP agrees wherever it completed (25 exhausted, 15 worst state safe, 5 time limits); full network α = 25% exhausted and equal, α = 10% time limit (FINDINGS §4) |
| Strong duality at every certificate | primal − dual ≤ 1e-6 and every immediate duration predecessor ≤ θ, for every reported cut | passing: largest gap 4.4e-16 over all Li-ion, PV and joint bundles |
| Bracket and residual estimate (Prop. 3, W1) | Exact L vs hand-enumerated state space; residual vs exact toy and crude MC; positive-width interval with zero residuals | passing: all residual points >= L and within four combined SEs of crude MC in the three `*-residual-2395a5c` bundles; joint alpha = 10% is 0.715669, L = 0.715669, interval 0.715669–0.715853. Original IS point 0.685 retained as a comparison (FINDINGS §2) |
| W1 changes only the estimator | `analysis/check_residual.py BEFORE AFTER`: compare every legacy risk field, networks and cut-file bytes | passing for Li-ion, PV and joint; `residual_checks.json` records clean revisions, unchanged source lock, R3 and R4 |
| W2 export estimator | Independent weighted fixed-effects normal equations; planted 10% tax response; unidentified-type fallback (`test_severity.py`) | passing; real-data S1/S2 untestable under registered minimum counts (DATA) |
| W2 partial loss | Paired endpoint and full-loss toy; samplewise partial shortfall <= full; paired difference interval | `severity-26ebd48`: zero monotonicity violation on all three 20,000-state runs; all assignments are full-loss fallbacks; S3 killed under that rule |
| W2 computation terminal states | Read JSON output, clean stamps, native scalar serialization regression | `severity-16be0a8`: export table written, scenario output failed serialization of a NumPy Boolean; `severity-26ebd48`: all three scenario jobs optimal after native-bool conversion; identical export table |
| Exact frozen bytes survive Git | Disk hashes and committed blob hashes (`analysis/check_inputs.py`), CRLF temporary-repo regression | all 88 on-disk sources verify; all 40 committed sources match; four earlier newline-normalized CSVs restored without changing frozen hashes |
| Witnesses belong to their displayed cuts (W7) | Recover cut coordinates from every predecessor; independently recompute each full and shortened state | `witnesses-e0b40e2`: 1,700 Li-ion, 179 PV and 424 joint cut certificates checked; maximum difference zero; original bundles immutable |
| Site controls and exhibits (W7) | Builder asserts witness coverage, exact country unions and severity certificates; hidden Edge at 390/1440 px, three nondefault/reset configurations | 16 browser checks, zero JavaScript exceptions or page overflow; predecessors displayed, PV and attribution use shared controls; E1 interval exhibit distinguishes parameter range from uncertainty; U = 100% explained |
| Rate estimator | Planted marginal and ρ recovery; missing exposure stays missing (`test_rates_planted_*`) | passing |
| Network invariants | R_p = Σ a R_q, φ(0) = 0 for Li-ion, PV, joint; basis labels; MYB and MIIT values (`tests/test_net.py`) | passing |
| Events | Derived onsets = research table except Zimbabwe 2022 (`run_data.py`) | passing |
| Data | MIIT parts vs total; exports vs production (DATA.md); Comtrade tariff lines | done; Comtrade not measured |
| Headline numbers | Fresh-subagent recomputation from raw data, sharing no code: 111 nodes, layer shares and S, the 7 singletons at 12 months and none at 6, the COD–IDN pair, all 37 cuts failing and minimal, 884/61 node-years, ρ, L = 0.485766 exact and by 2,000,000 Monte Carlo draws | passing (2026-10-15); one documented definitional difference in duration counts (DATA.md) |
