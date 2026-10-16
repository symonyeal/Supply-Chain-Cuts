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
| Bracket (Prop. 3) | Exact L vs hand-enumerated state space (`test_correlated_duration_union_and_tail`); IS vs crude MC | passing at the Li-ion and PV headlines; on the joint network at α = 10% the IS estimate (0.685) falls below L (0.716) with an interval that contains it, while crude MC gives 0.723 (FINDINGS §2) |
| Rate estimator | Planted marginal and ρ recovery; missing exposure stays missing (`test_rates_planted_*`) | passing |
| Network invariants | R_p = Σ a R_q, φ(0) = 0 for Li-ion, PV, joint; basis labels; MYB and MIIT values (`tests/test_net.py`) | passing |
| Events | Derived onsets = research table except Zimbabwe 2022 (`run_data.py`) | passing |
| Data | MIIT parts vs total; exports vs production (DATA.md); Comtrade tariff lines | done; Comtrade not measured |
| Headline numbers | Fresh-subagent recomputation from raw data, sharing no code: 111 nodes, layer shares and S, the 7 singletons at 12 months and none at 6, the COD–IDN pair, all 37 cuts failing and minimal, 884/61 node-years, ρ, L = 0.485766 exact and by 2,000,000 Monte Carlo draws | passing (2026-10-15); one documented definitional difference in duration counts (DATA.md) |
