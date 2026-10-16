# Chokepoint-Lab

Which minimal sets of (country, product) supply losses stop global lithium-ion cell
production, and how likely are they each year? The supply chain is a capacity network
from mine to refined chemical to cell. Inventory, spare capacity and ramp-up give the
recourse. Cut sets are found exactly by network interdiction, and their probability is
bracketed from the historical record of export restrictions and natural hazards.

Let z be a disruption state. Production fails under z when the least achievable
cumulative shortfall exceeds α of demand:

```
φ(z) = min Σ_τ g_τ  s.t.  y ≤ ū(z),  shipments ≤ output,  inventory balance,  Σ y_cell + g ≥ d   >   α Σ_τ d_τ
```

A cut set is a minimal z with this property. The annual failure probability is
bracketed by L ≤ P(fail) ≤ L + P(|supp Z| > k).

| Model | Module | Source |
| --- | --- | --- |
| Recourse LP φ(z) | `chokepoint/recourse.py` | Brown et al. 2006; Snyder et al. 2016 |
| Interdiction MILP, cut-set enumeration | `chokepoint/cuts.py` (planned) | Wood 1993; Israeli & Wood 2002 |
| Bill of materials | `data/bom.yaml` (planned) | Xu et al. 2020 |

Status: scaffolded 2026-10-15. Design: [docs/specs](docs/specs/2026-10-15-chokepoint-design.md).
Evidence: [docs/RESEARCH.md](docs/RESEARCH.md).

Run: `python -m pytest -q`.
