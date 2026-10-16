# Findings

Every outcome of the registered tests is reported here, rejections included. Numbers are
read from the result bundles named in each section; the bundle's `stamp` records the code
revision and the `SOURCES.lock` digest.

## 1. Answer (Li-ion, v0.1.0)

Bundle `results/liion-60eb399` (cuts at `60eb399`; risk at the revision in `risk.json`).
Headline instance: α = 25% of 24 months' demand, outages up to 12 months, no input stock
(h = 0), no spare capacity (σ = 0).

**Cut sets.** There are 37 minimal cut sets of at most three losses. Seven are single
Chinese nodes out for 12 months: cells (φ = 45.7% of demand), CAM (46.2%), AAM (47.0%), pCAM
(45.7%, imputed), graphite (39.7%), lithium carbonate (29.0%) and refined cobalt (37.4%).
None is a cut at 6 months: with flat demand and no baseline shortage, a 6-month loss cannot
exceed 25% of 24 months, so the six-month part of the day-1 claim fails by construction. The
other 30 involve cobalt mining (the DRC out for 12 months with one or two smaller miners for
3–12 months; the DRC–Indonesia pair is the most probable), lithium mining (Australia and
Chile for 12 months with China or Zimbabwe), and two trade-basis cell triples.

Three singletons hold under every registered test of capacity basis (B2), re-export
removal (B1) and chemistry mix (C1): China's cells, CAM and AAM. Graphite, lithium
carbonate and refined cobalt vanish on the trade basis; pCAM and refined cobalt need
NCM in the mix, and at NCM ≥ 0.75 the DRC's cobalt mines become a singleton too.

At α = 10% there are 135 cut sets: China's cells, CAM, AAM and pCAM are singletons at 3
months, and its graphite, lithium carbonate, refined cobalt and the DRC's cobalt mines at
6 months. At α = 50% there is none: losing every node for 12 of 24 months removes exactly
50%, and failure is strict.

**Annual probability (scenario).** Treating every recorded export-restriction onset as a
full outage of its node, with the recorded spell length (96% bin to 12 months) and
within-country correlation ρ = 0.583, the exact lower bound is L = 0.486. The upper bound U
is 1, uninformative, because about 7.9 nodes are hit per year and P(more than three) = 0.915.
Importance sampling gives 0.490 (95% interval 0.478–0.503); crude Monte Carlo 0.488
(standard error 0.0035). Cut sets containing a Chinese node carry 87.8% of L; those with
the DRC 21.2% (exact unions; shares overlap). The registered predictive test failed (§3,
D1), so these numbers are scenarios under stated rates, not forecasts. Counting only quotas
and prohibitions (post hoc, not registered), L = 0.069 and the estimate is 0.071
(0.065–0.076).

**Natural hazards (scenario).** No country-wide loss of 10%, 25% or 50% of capacity fails at
α = 25% for any duration up to 12 months. Only a total 12-month loss of China fails (φ =
47.0%). GDACS issued orange or red alerts for China in all 13 years 2012–2024; an alert is
not a loss.

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

**Shared network** (bundle `results/joint-ba89465`, h = σ = 0). Each sector's shortfall is
measured in its own annual output, so the two count equally and failure is more than α of
their sum. At α = 25% no single loss suffices: losing all of one sector for 12 months is 25%
of the joint demand, not more. All 180 minimal cut sets combine a battery loss with a PV
loss (61 pairs, 119 triples); the most probable is China's polysilicon out for 12 months
with the DRC's cobalt mines for 3. L = 0.204; importance sampling 0.210 (0.182–0.239); crude
Monte Carlo 0.204 (standard error 0.003). At α = 10% there are 244, twelve of them singletons:
the eight Li-ion singletons of §1 at α = 10%, now at longer durations (China's cells, CAM,
AAM and pCAM at 6 months; its graphite, lithium carbonate, refined cobalt and the DRC's
cobalt mines at 12), and China's four PV stages at 6 months. There failure is common, L = 0.716, and importance
sampling performed badly: 0.685 (0.646–0.724), below the exact L though its interval
contains it, against crude Monte Carlo 0.723 (standard error 0.003). The tilt toward cut
nodes inflates variance when failure is not rare; crude Monte Carlo is the estimate there.

Certificates on the pruned joint network (45 nodes with share ≥ 5%): at α = 10% exhaustive,
lattice and MILP lists agree (MILP exhausted in 416 s); at α = 25% exhaustive and lattice
agree (110 cut sets) and the MILP reached its 900 s limit, an incomplete result.

## 3. Registered tests

From [HYPOTHESES](HYPOTHESES.md), committed before any probability existed (`58e8aba`).

| Leaf | Kill condition | Result | Verdict |
| --- | --- | --- | --- |
| Day-1 (i) | China graphite a singleton at α = 25%, D ≥ 6 | singleton at 12 months only | 6-month part rejected; 12-month part holds |
| Day-1 (ii) | cut sets with a Chinese midstream node carry ≥ 80% of L | 35.3% with midstream = pCAM, CAM, AAM (design §3) | killed |
| Day-1 (iii) | annual P(fail) in [1%, 10%] | L = 0.486; estimate 0.490 | killed |
| A1 | Spearman(attribution, concentration) ≥ 0.9 | 0.67 with HHI, 0.70 with top share | survives: the network adds information |
| B1 | cut sets that disappear without re-export nodes are withdrawn | see below | applied |
| B2 | cut sets that change on the trade basis are basis-dependent | 33 vanish, 30 appear at α = 25% | applied |
| C1 | Co/Ni cut sets that vanish at some NCM share are conditional | every Co/Ni cut set changes somewhere in NCM ∈ {0, 0.25, 0.75, 1} | applied: all Co/Ni claims are conditional on the mix |
| D1 | no out-of-sample log-loss gain ⇒ probabilities are scenarios | 0.327 vs 0.297 for a pooled constant, 340 node-years 2020–2024 | killed: probabilities are scenarios |
| E1 | tornado over α, D, h, σ, L | §5 | no kill condition |

Day-1 (ii), secondary readings, reported because their values were seen before the
definition was fixed to the design's: 62.1% with refined chemicals counted as midstream,
80.6% with graphite as well.

A1. Attribution concentrates where the network is tight, not where shares are high:
cobalt mining (HHI 0.61) has attribution 0.31 through the DRC, while lithium carbonate
(HHI 0.60) has 0.05 and lithium mining none. Concentration ranks products with ρ_S = 0.67.

B1. Flagged as re-export nodes (imports ≥ exports of the same codes): DEU, KOR, USA cells;
CHN, DEU, FRA, JPN, NLD refined nickel. One cut set rests on a flagged node (China cells 6
months with Poland and US cells 12 months) and is withdrawn. Applied literally, the rule
withdraws 29 of 37: removing the flagged cells lowers demand by 4.7%, which moves the
near-threshold cobalt- and lithium-mining combinations (shortfalls within 3% of the
threshold) across it; 19 new combinations appear. The seven singletons and the
DRC–Indonesia pair survive. The registered rule is reported as written; the combinations it
withdraws are best read as boundary-sensitive.

B2. On the trade basis China's midstream shrinks to its exports (cells 31%, refined cobalt
4%, lithium carbonate 0.4% of production). China's graphite, lithium carbonate and refined
cobalt singletons vanish; Chile's lithium carbonate becomes one; the cobalt-mining
combinations are replaced by two triples that need the DRC and Indonesia out for 12 months,
because the smaller trade-basis cell output lowers the cobalt requirement. These are
basis-dependent. China's cells, CAM, AAM and pCAM do not
change.

C1. At NCM 0 (all LFP) the singletons are China's cells, CAM, AAM, graphite and lithium
carbonate; pCAM appears at 0.25, refined cobalt and the DRC's cobalt mines at 0.75.

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
