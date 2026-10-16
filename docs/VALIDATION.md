# Validation

What must be checked, how, and what has been. A check is a certificate (feasibility, a
duality gap, a known optimum from a source), never an output snapshot.

| Claim | Check | Status |
| --- | --- | --- |
| φ on a toy network | Shortfalls derived by hand (`tests/test_recourse.py`) | passing |
| φ is monotone (design Prop. 1) | Random comparable disruption pairs on the toy network | passing |
| Cut sets complete and minimal (Props. 2) | `brute` = `cuts` on the pruned network, k ≤ 3, whole sweep | open |
| Strong duality at every certificate | primal − dual ≤ eps | open |
| Bracket (Prop. 3) | IS estimate within [L, U]; crude MC agreement where not rare | open |
| Rate estimator | Planted-truth recovery of p_v, ρ on synthetic events | open |
| Data | BACI vs USGS/BGS; Comtrade tariff lines vs BACI HS6; MIIT parts vs totals | open |
| Headline numbers | Fresh-subagent recomputation from raw data | open |
