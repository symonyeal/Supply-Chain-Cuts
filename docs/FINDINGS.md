# Findings

Every outcome of the registered tests is reported here, rejections included. Numbers are
read from the result bundles named in each section; the bundle's `stamp` records the code
revision and the `SOURCES.lock` digest.

## 1. Answer (Li-ion, v0.1.0)

PENDING: filled from `results/liion-60eb399/risk.json`.

## 2. PV and the shared network (v0.2.0)

Bundle `results/pv-ba89465` (cuts at `ba89465`, risk at `afd3164`).

At α = 25%, h = σ = 0, outages up to 12 months, the PV chain has 22 minimal cut sets of at
most three losses. Four are single Chinese nodes out for 12 months: polysilicon, wafers,
cells and modules (China holds 94%, 95%, 93% and 81% of the retained layers). The five pairs
combine a six-month Chinese loss with a twelve-month loss of Viet Nam's modules or
Thailand's cells; the thirteen triples add smaller origins. At α = 10% the four Chinese stages are cut sets at 3 months.
At α = 50% there is none: a 12-month total outage is exactly 50% of 24 months, and failure
is strict.

Under the scenario rates, L = 0.244 and U = 0.306 at α = 25%; importance sampling gives
0.244 (95% interval 0.239–0.249) and crude Monte Carlo 0.249 (standard error 0.003). The
importance-sampling point lies 0.0007 below the exact L, within its sampling error; it is
reported unclipped. China's polysilicon carries 76% of L because it is the only PV node
with OECD exposure and recorded onsets (2013, 2018, 2019; p = 0.193); the other PV nodes
borrow the all-product prior (p = 0.069). The bracket is tight here because the network
has 15 nodes.

Certificates: in all 45 PV configurations, exhaustive search on the whole network returns
the lattice list; every cut has zero primal–dual gap and immediate predecessors at or
below the threshold.

Shared network: PENDING (`results/joint-ba89465`).

## 3. Registered tests

PENDING.

## 4. What the data cannot show

- Trade is not production. Outside China, cells and refined nickel rest on export mass;
  China's export proxy is 31% of its cell output and 4% of its refined cobalt.
- pCAM everywhere, and CAM and AAM outside China, are imputed from cell output, so their
  cut sets mirror the cell layer. No pCAM production statistic was found.
- Upstream layers have no competing demand: all copper, aluminium, nickel, manganese,
  cobalt, lithium and graphite output may serve batteries. Upstream cut sets are therefore
  harder to reach than in reality.
- A policy onset is a legal measure, not an observed outage. Durations are legal-measure
  lengths. No record measures lost capacity.
- The OECD survey covers raw materials only; cells, CAM, pCAM, AAM and three PV stages
  borrow a pooled rate.
- No located capacity: natural hazards are a country-wide scenario, not matched to sites.
- Not measured: Comtrade tariff lines for China's midstream; BGS refinery statistics
  (licence unresolved); national cell output outside China.
