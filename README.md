# Chokepoint-Lab

**Explorer: https://symonyeal.github.io/Chokepoint-Lab/**

Which minimal sets of (country, product) supply losses stop global lithium-ion cell
production, and how likely are they each year?

## Answer

**Seven single losses, all in China, each stop more than a quarter of two years' Li-ion cell
output if they last a year:** cells, cathode material (CAM), anode material (AAM), cathode
precursor (pCAM, imputed), graphite, lithium carbonate and refined cobalt. Three of them,
cells, CAM and AAM, survive every registered test of capacity basis, re-export removal and
chemistry mix, and they are the only cut sets left when every plant holds three months of
input stock. In all, 37 minimal sets of at most three losses do so; the rest combine the
DRC's cobalt mines with smaller miners, or Australia's and Chile's lithium mines with a third.
Over the 24-month horizon no combination of outages of six months or less can remove more
than a quarter, and outages of up to a year cannot remove more than half.

**How likely is a scenario, not a forecast.** If every export restriction recorded 2012–2024
were a full outage of its node for its recorded length, the annual probability would be about
0.486 (exact lower bound L = 0.485681; lower bound plus residual 0.485681, 95% binomial
interval 0.485681–0.485866). Counting only quotas and bans, L and the residual estimate
are 0.069423 (interval 0.069423–0.069607; post hoc). Recorded onsets do not predict later years
better than a constant, so neither number is a forecast; cut sets containing a Chinese node
carry 88% of the scenario risk.

**Solar is more concentrated still.** Each of China's polysilicon, wafer, cell and module
stages is a cut set on its own (v0.2.0). On one network with batteries, no single loss
suffices at 25%, but 180 battery–PV pairs and triples do.

**What the data cannot show.** Outside China, cell and refined-nickel capacity rests on export
mass; precursor capacity is imputed from cell output; upstream metals have no competing
demand; a recorded policy measure is not an observed outage; no production site has located
capacity, so natural hazards are a scenario. Details: [FINDINGS](docs/FINDINGS.md).

## Model

The supply chain is a capacity network from mine to refined chemical to cell, built from
2024 production statistics where they exist and export mass where they do not; every node
is labelled `production`, `trade` or `imputed` ([DATA](docs/DATA.md)). Let z be a
disruption state: each node out for 0, 3, 6 or 12 months. With shipments rerouted,
inventory drawn and spare capacity ramped, the least cumulative shortfall over 24 months is

```
φ(z) = min Σ_t g_t   s.t.  y ≤ ū(z),  shipments ≤ output,  inventory balance,  Σ y_cell + g ≥ d,
```

and production fails when φ(z) > α Σ_t d_t. A cut set is a minimal failing state. Cut sets of
up to three losses are enumerated exactly, three ways that share no code: an interdiction
MILP built from the LP dual, a lattice search pruned by capacity dominance, and exhaustive
search; their lists agree wherever all three ran ([MODEL](docs/MODEL.md),
[VALIDATION](docs/VALIDATION.md)). The annual probability is bracketed,
L ≤ P(fail) ≤ min(1, L + P(more than three losses)), with L exact. The estimate adds to L
a Monte Carlo estimate of failures containing no enumerated cut. It cannot fall below L;
its binomial interval stays informative with zero observed residuals. Legacy importance
sampling and crude MC remain comparisons. The law uses export-policy onsets 2012–2024
([HYPOTHESES](docs/HYPOTHESES.md),
[FINDINGS](docs/FINDINGS.md)).

| Model | Module | Source |
| --- | --- | --- |
| Recourse LP φ(z), exact blocks | `chokepoint/recourse.py` | Brown et al. 2006; Snyder et al. 2016 |
| Interdiction MILP, cut-set enumeration | `chokepoint/cuts.py` | Wood 1993; Israeli & Wood 2002 |
| Exhaustive and lattice enumeration | `chokepoint/brute.py` | Lemma B, docs/MODEL.md |
| Network and bill of materials | `chokepoint/net.py`, `chokepoint/bom.py` | USGS, MIIT, Cochilco, CEPII BACI; Xu et al. 2020 |
| Policy onsets, rates | `chokepoint/events.py`, `chokepoint/rates.py` | OECD Inventory of Export Restrictions |
| Bracket, residual MC, importance sampling | `chokepoint/risk.py` | MODEL §Annual probability; Clopper & Pearson 1934 |

## Reproduce

```text
python -m pytest -q                               # fast gate; -m slow for the long tests
python run_data.py RUN                            # networks and reconciliations
python run_cuts.py RUN 7 [liion|pv|joint]         # cut sweep with certificates
python run_risk.py RUN                            # rates, bracket, estimates, tests
python run_severity.py RUN                        # registered trade responses and loss scenarios
python analysis/build_site.py LIION_RUN PV_RUN JOINT_RUN SEVERITY_RUN  # generated site/data.js
python analysis/check_residual.py BEFORE AFTER    # unchanged legacy results and W1 checks
```

System Python 3.14 with numpy and scipy (HiGHS). Raw inputs are frozen in `data/` with URL,
date, SHA-256 and licence in `SOURCES.lock`; sources whose licence is unverified stay out
of git and are re-fetchable by URL. `site/data.js` is generated by `analysis/build_site.py`
from the committed bundles in `results/`. No investment or price claim is made.
Published W1 bundles: `liion-residual-2395a5c`, `pv-residual-2395a5c`,
`joint-residual-2395a5c`; their predecessor bundles remain immutable.
The approved severity study (`severity-26ebd48`) retains only four isolated events and
identifies no measure-type loss fraction. Its declared full-loss fallbacks leave the
scenario law unchanged. The site shows this identification failure beside the full-outage
and quota/ban scenarios; no measured production loss or calibrated forecast is claimed.
