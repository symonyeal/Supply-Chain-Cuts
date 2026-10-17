# Findings

Every outcome of the registered tests is reported here, rejections included. Numbers are
read from the result bundles named in each section; the bundle's `stamp` records the code
revision and the `SOURCES.lock` digest.

## 1. Answer (Li-ion, v0.1.0)

Bundle `results/liion-60eb399` (cuts at `60eb399`; risk at the revision in `risk.json`).
W1 probability rerun: `results/liion-residual-2395a5c` (risk at `2395a5c`). The comparison
certificate confirms identical networks, cut bytes and every legacy risk result.
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
removal (B1) and chemistry mix (C1): China's cells, CAM and AAM. They are also the only cut
sets left with three months of input stock (§4). Graphite, lithium
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
The lower-bound-plus-residual estimate is 0.485681, with exact L = 0.485681 and a 95%
binomial interval 0.485681–0.485866. No residual failure appeared in 20,000 draws; this
does not prove the residual probability is zero. Crude MC gives 0.488050 (SE 0.003535),
0.67 combined standard errors away. The old IS estimate remains a comparison in the
bundle. Cut sets containing a Chinese node carry 87.8% of L; those with
the DRC 21.2% (exact unions; shares overlap). The registered predictive test failed (§3,
D1), so these numbers are scenarios under stated rates, not forecasts. Counting only quotas
and prohibitions (post hoc, not registered), lower bound plus residual gives 0.069423,
with L = 0.069423 and a 95% interval 0.069423–0.069607 (zero residual failures in 20,000
draws). At alpha = 10%, L = 0.596762 and the residual estimate is 0.596812 (one residual
failure; interval 0.596764–0.597041).

**Natural hazards (scenario).** No country-wide loss of 10%, 25% or 50% of capacity fails at
α = 25% for any duration up to 12 months. Only a total 12-month loss of China fails (φ =
47.0%). GDACS issued orange or red alerts for China in all 13 years 2012–2024; an alert is
not a loss.

## 2. PV and the shared network (v0.2.0)

Bundle `results/pv-ba89465` (cuts at `ba89465`; data and risk at `524b9d3`).
W1 probability rerun: `results/pv-residual-2395a5c`; its comparison certificate confirms
identical networks, cut bytes, rates, bounds and legacy IS/MC results.

At α = 25%, h = σ = 0, outages up to 12 months, the PV chain has 22 minimal cut sets of at
most three losses. Four are single Chinese nodes out for 12 months: polysilicon, wafers,
cells and modules (China holds 94%, 95%, 93% and 81% of the retained layers). The five pairs
combine a six-month Chinese loss with a twelve-month loss of Viet Nam's modules or
Thailand's cells; the thirteen triples add smaller origins. At α = 10% the four Chinese stages are cut sets at 3 months.
At α = 50% there is none: a 12-month total outage is exactly 50% of 24 months, and failure
is strict.

Under the scenario rates, L = 0.244494 and U = 0.306183 at α = 25%. The lower-bound-plus-
residual estimate is 0.244494 (95% binomial interval 0.244494–0.244678), with no residual
failures in 20,000 draws. A zero residual count is not proof that L is the full probability.
Crude MC gives 0.248750 (standard error 0.003057), a difference of 1.39 combined standard
errors. The legacy importance-sampling point remains in the bundle as a comparison;
it lies 0.0007 below L. China's polysilicon carries 76% of L because it is the only PV node
with OECD exposure and recorded onsets (2013, 2018, 2019; p = 0.193); the other PV nodes
borrow the all-product prior (p = 0.069). The bracket is tight here because the network
has 15 nodes.

Certificates: in all 45 PV configurations, exhaustive search on the whole network returns
the lattice list; every cut has zero primal–dual gap and immediate predecessors at or
below the threshold.

**Shared network** (bundle `results/joint-ba89465`: cuts at `ba89465`, with `analysis/build_site.py` uncommitted at launch and unused by the run; data and risk at `524b9d3`; h = σ = 0). Each sector's shortfall is
measured in its own annual output, so the two count equally and failure is more than α of
their sum. At α = 25% no single loss suffices: losing all of one sector for 12 months is 25%
of the joint demand, not more. All 180 minimal cut sets combine a battery loss with a PV
loss (61 pairs, 119 triples); the most probable is China's polysilicon out for 12 months
with the DRC's cobalt mines for 3. L = 0.204; importance sampling 0.210 (0.182–0.239); crude
Monte Carlo 0.204 (standard error 0.003) were the original comparisons. The W1 rerun
`results/joint-residual-2395a5c` gives L = 0.203828 and lower bound plus residual 0.206078
(95% interval 0.205470–0.206838; 45 residual failures in 20,000 draws). At α = 10% there
are 244, twelve of them singletons:
the eight Li-ion singletons of §1 at α = 10%, now at longer durations (China's cells, CAM,
AAM and pCAM at 6 months; its graphite, lithium carbonate, refined cobalt and the DRC's
cobalt mines at 12), and China's four PV stages at 6 months. There failure is common, L = 0.716, and importance
sampling performed badly: 0.685 (0.646–0.724), below the exact L though its interval
contains it, against crude Monte Carlo 0.723 (standard error 0.003). The tilt toward cut
nodes inflates variance when failure is not rare. The W1 estimate is now lower bound plus
residual: 0.715669, with L = 0.715669 and a 95% binomial interval 0.715669–0.715853 (zero
residual failures in 20,000 draws). Crude MC remains 0.722750 (SE 0.003165), 2.24 combined
standard errors away. Its 95% interval and the residual interval do not overlap; the
registered four-standard-error check survives. The smaller error of the residual method
comes from treating the cut-union probability exactly. It does not remove scenario
uncertainty. Every legacy number and cut file is unchanged in the comparison certificate.

Certificates on the pruned joint network (45 nodes with share ≥ 5%): at α = 10% exhaustive,
lattice and MILP lists agree (MILP exhausted in 416 s); at α = 25% exhaustive and lattice
agree (110 cut sets) and the MILP reached its 900 s limit, an incomplete result.

## 3. Registered tests

From [HYPOTHESES](HYPOTHESES.md), committed before any probability existed (`58e8aba`).

| Leaf | Kill condition | Result | Verdict |
| --- | --- | --- | --- |
| Day-1 (i) | China graphite a singleton at α = 25%, D ≥ 6 | singleton at 12 months only | 6-month part rejected; 12-month part holds |
| Day-1 (ii) | cut sets with a Chinese midstream node carry ≥ 80% of L | 35.3% with midstream = pCAM, CAM, AAM (design §3) | killed |
| Day-1 (iii) | annual P(fail) in [1%, 10%] | L = 0.486; lower bound plus residual 0.486 | killed |
| A1 | Spearman(attribution, concentration) ≥ 0.9 | 0.67 with HHI, 0.70 with top share | survives: the network adds information |
| B1 | cut sets that disappear without re-export nodes are withdrawn | see below | applied |
| B2 | cut sets that change on the trade basis are basis-dependent | 33 vanish, 30 appear at α = 25% | applied |
| C1 | Co/Ni cut sets that vanish at some NCM share are conditional | every Co/Ni cut set changes somewhere in NCM ∈ {0, 0.25, 0.75, 1} | applied: all Co/Ni claims are conditional on the mix |
| D1 | no out-of-sample log-loss gain ⇒ probabilities are scenarios | 0.327 vs 0.297 for a pooled constant, 340 node-years 2020–2024 | killed: probabilities are scenarios |
| E1 | tornado over α, D, h, σ, L | §4 | no kill condition |

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

W1, registered at `50d69fe`, evaluated from the three `*-residual-2395a5c` bundles and
their `residual_checks.json` certificates:

| Leaf | Result | Verdict |
| --- | --- | --- |
| R1 | Hand-enumerated toy probability is inside the binomial interval; positive residual and incomplete-enumeration path tested | survives |
| R2 | Random-network residual and crude MC differ by less than four combined SEs | survives |
| R3 | Joint alpha = 10% estimate equals L and is 2.24 combined SEs from crude MC | survives |
| R4 | At alpha = 25%, residual SEs are 0, 0 and 0.000335 for Li-ion, PV and joint; crude SEs are 0.003535, 0.003057 and 0.002849 | survives on all three instances |

R1–R2 are certified by `tests/test_risk.py`; R3–R4 by the named bundles. Zero sample SE
has a positive-width binomial interval. All probabilities remain conditional scenarios;
this change estimates the scenario law more precisely without validating that law.

### W2: the approved study cannot identify export severities

Bundle `results/severity-26ebd48`, code `26ebd48`, clean stamps. Twelve BACI years and a
verified HS concordance yield only four isolated cohorts under the approved coverage,
baseline and overlap rules. No measure reaches the registered five-event minimum.
M1's export loss estimate is −0.130681 [−0.912677, 0.550011] on two events; M14 is
−0.196687 [−0.803798, 0.173337] on one, with a failed pretrend check; M5 is 0.041791
[−0.243097, 0.311436] on one. No isolated quota, prohibition or licensing event survives.
DATA reports definitions, exclusions and bootstrap counts. These are weak descriptive
trade responses, not measured capacity losses.

| Registered claim | Result | Verdict |
| --- | --- | --- |
| S1: quota/prohibition export loss >= 50% | zero isolated events, separately and jointly | untestable: insufficient observations |
| S2: export-tax loss < 20% | two events; loss −0.130681 [−0.912677, 0.550011] | untestable: insufficient observations |
| S3: capacity scenario lowers risk >= 5 points in each network | reduction 0 points [0, 0.018443] on each network | killed under the declared fallback rule |

All simulated onsets receive unidentified-type full-loss fallbacks. Partial and full
shortfalls are therefore equal on every one of 20,000 paired states per sector (maximum
monotonicity violation zero). Paired MC probabilities are 0.476000 [0.469057, 0.482950]
for Li-ion, 0.248950 [0.242969, 0.255004] for PV and 0.202450 [0.196900, 0.208087] for
joint. These independent draws agree with W1 within the registered four combined SEs;
Li-ion's 95% MC interval does not contain L, a 2.74-SE deviation. The laws coincide, so
the site reports the more precise W1 residual estimate in the severity column and says
why. No reduction has been empirically established; this study leaves the main scientific
gap open. S3's verdict describes this specified assignment rule, not true policy severity.

The post hoc quota-and-ban comparison at alpha = 25% gives L-plus-residual estimates
0.069423 [0.069423, 0.069607] for Li-ion, 0.040464 [0.040464, 0.040648] for PV and
0.009126 [0.009126, 0.009310] for joint. Each point equals its exact L, with zero residual
failures in 20,000 draws; positive interval width remains. Quota/ban onset frequency is
not a measured severity of the measures themselves.

## 4. Sensitivity (E1)

Cut sets of support ≤ 3 at D_J = 12 and the exact L, over the whole sweep (generated by
`analysis/sweep_table.py liion-60eb399`). L for a scenario row is computed under the same
scenario rates; only recourse and the threshold change.

| h | σ | L (months) | α = 10%: cut sets | L | α = 25%: cut sets | L |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | – | 135 | 0.597 | 37 | 0.486 |
| 0 | 0.1 | 6 | 33 | 0.596 | 17 | 0.469 |
| 0 | 0.1 | 24 | 51 | 0.596 | 30 | 0.482 |
| 0 | 0.5 | 6 | 29 | 0.592 | 12 | 0.456 |
| 0 | 0.5 | 24 | 32 | 0.596 | 20 | 0.467 |
| 1 | 0 | – | 46 | 0.467 | 29 | 0.341 |
| 1 | 0.1 | 6 | 45 | 0.466 | 27 | 0.324 |
| 1 | 0.1 | 24 | 57 | 0.467 | 33 | 0.326 |
| 1 | 0.5 | 6 | 19 | 0.466 | 8 | 0.322 |
| 1 | 0.5 | 24 | 32 | 0.466 | 21 | 0.324 |
| 3 | 0 | – | 63 | 0.277 | 4 | 0.171 |
| 3 | 0.1 | 6 | 58 | 0.254 | 3 | 0.171 |
| 3 | 0.1 | 24 | 35 | 0.273 | 3 | 0.171 |
| 3 | 0.5 | 6 | 15 | 0.233 | 3 | 0.171 |
| 3 | 0.5 | 24 | 26 | 0.251 | 3 | 0.171 |

Headline: 37 cut sets, L = 0.486

| Change from the headline | cut sets | L | ΔL |
| --- | ---: | ---: | ---: |
| α = 50% | 0 | 0.000 | -0.486 |
| D ≤ 6 | 0 | 0.000 | -0.486 |
| D ≤ 3 | 0 | 0.000 | -0.486 |
| h = 3 | 4 | 0.171 | -0.314 |
| h = 1 | 29 | 0.341 | -0.145 |
| α = 10% | 135 | 0.597 | +0.111 |
| σ = 0.5, L = 6 | 12 | 0.456 | -0.030 |
| σ = 0.5, L = 24 | 20 | 0.467 | -0.018 |
| σ = 0.1, L = 6 | 17 | 0.469 | -0.017 |
| σ = 0.1, L = 24 | 30 | 0.482 | -0.004 |

The threshold and the outage cap dominate: with outages capped at six months no cut set
exists at α = 25%. Inventory comes next: one month of input stock lowers L from 0.486 to
0.341, three months to 0.171. Spare capacity matters least (|ΔL| ≤ 0.03). The number of cut
sets is not monotone in recourse: removing a singleton can create several larger minimal
sets. With three months of stock, with or without spare capacity, the only cut sets left at
α = 25% are China's cells, CAM and AAM (and, without spare capacity, one trade-basis cell
triple): the same three singletons that survive the B1, B2 and C1 tests.

Certificates over the sweep: every reported cut set has primal–dual gap ≤ 4.4e-16 and every
immediate predecessor at or below the threshold. On the pruned network (40 nodes with share
≥ 5%) exhaustive search equals the lattice list in all 45 configurations; the MILP proved
exhaustion and agreed in 25, proved even the worst state safe in the 15 at α = 50%, and
reached its 900 s limit in 5 (h > 0, L = 24). On the full network the MILP equals the lattice
list at α = 25% (exhausted, 3,583 s) and reached its 5,400 s limit at α = 10%.

## 5. What the data cannot show

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
