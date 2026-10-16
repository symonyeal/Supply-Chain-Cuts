# Validation

What must be checked, how, and what has been. A check is a certificate (feasibility, a
duality gap, a known optimum from a source), never an output snapshot.

| Claim | Check | Status |
| --- | --- | --- |
| φ on a toy network | Shortfalls derived by hand (`tests/test_recourse.py`) | passing |
| φ is monotone (design Prop. 1) | Random comparable disruption pairs on the toy network | passing |
| Block aggregation exact (Lemma A) | Block LP = monthly LP on 60 random states with h, σ > 0 (`test_blocks_exact`) | passing |
| Lattice search loses no cut (Lemma B) | Lattice = exhaustive on random 3- and 4-layer networks (`test_lattice_equals_brute*`) | passing |
| Cut sets complete and minimal (Prop. 2) | exhaustive = lattice = MILP on the pruned network (share ≥ 5%), k ≤ 3, whole sweep; MILP = lattice on the full network at h = σ = 0 | see FINDINGS |
| Strong duality at every certificate | primal − dual ≤ 1e-6 and every immediate duration predecessor ≤ θ, for every reported cut | see FINDINGS |
| Bracket (Prop. 3) | Exact L vs hand-enumerated state space (`test_correlated_duration_union_and_tail`); IS vs crude MC at the headline | passing; see FINDINGS |
| Rate estimator | Planted marginal and ρ recovery; missing exposure stays missing (`test_rates_planted_*`) | passing |
| Network invariants | R_p = Σ a R_q, φ(0) = 0 for Li-ion, PV, joint; basis labels; MYB and MIIT values (`tests/test_net.py`) | passing |
| Events | Derived onsets = research table except Zimbabwe 2022 (`run_data.py`) | passing |
| Data | MIIT parts vs total; exports vs production (DATA.md); Comtrade tariff lines | done; Comtrade not measured |
| Headline numbers | Fresh-subagent recomputation from raw data | see FINDINGS |
