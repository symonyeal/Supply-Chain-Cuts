# Registered hypotheses

Registered before any probability computation. The question is whether network recourse
changes which country–product losses merit diversification, relative to concentration alone.
The design dated 2026-10-15 is the source of these tests; rejection is an admissible result.

The day-1 answer was: at alpha = 0.25, durations of at least six months, h = sigma = 0,
China graphite is a singleton cut; Chinese midstream cuts carry at least 80% of L; annual
failure probability lies between 1% and 10%. These are three separate hypotheses.

| Leaf | Test | Kill condition |
| --- | --- | --- |
| A1 | Spearman rank correlation of product cut attribution and concentration | >= 0.9: concentration suffices on this instance |
| B1 | Remove trade nodes whose exports exceed observed production; enumerate again | Withdraw every cut that disappears as a re-export artefact |
| B2 | Replace China trade midstream capacities with MIIT production | Report changed cuts as capacity-basis dependent |
| C1 | Sweep NCM622 fraction from zero to one, including the LFP endpoint | Withdraw unconditional claims about Co/Ni cuts that disappear |
| D1 | Fit 2012–2019; score each year of 2020–2024 before updating, against a pooled constant | No log-loss improvement: report rates only as scenarios |
| E1 | Sweep alpha, duration, inventory, spare capacity and lead time | Rank sensitivity; no rejection threshold |

Premortem: trade is not production, a licence is not a complete production outage, and
national hazard occurrence is not a located factory loss. Missing exposure is not a zero.
The weakest assumption is the conversion from observed policy onsets into full-node
outages. Without independently observed loss fractions, probabilities are conditional
scenarios even if the onset-rate predictor improves.

Steelman: a largest-share table explains the findings as well as the network. The A1 test
must be reported, including undefined correlation when attribution is constant.

Certificates: independently enumerated cuts, LP primal–dual equality, immediate duration
predecessors, exact small-state risk, planted rate recovery, and independent reproduction
of the published bundle. Natural hazards enter the headline only if located capacity
coverage reaches 70% in every layer before matching.

The horizon is 24 months and failure is strict. A six-month outage cannot cause more than
25% cumulative loss when every other period can satisfy flat demand and there is no
baseline shortage. Thus equality at 25% rejects the six-month singleton assertion; it
must not be changed into a non-strict test after seeing results.

## W1: residual probability estimator (2026-10-16)

Registered before new probability computations. The original joint alpha = 10% IS point
is below its exact lower bound; the original crude estimate is the comparison, not a new
test result. Let C be the event of containing an enumerated failing cut, F failure, and
L = P(C). The proposed answer is P_hat = L + mean(1_F - 1_C), with draws from the original
scenario law. Since C is contained in F, the residual is Bernoulli and P_hat >= L for
every sample. No empirical improvement of the onset model or outage severities is claimed.

| Leaf | Expected result | Kill condition |
| --- | --- | --- |
| R1 | Recover the exact probability on a hand-enumerated categorical toy, including a failure outside the cut union | Exact probability outside the 95% binomial interval at the fixed test seed |
| R2 | Agree with crude MC on a randomly generated capacity network | Difference exceeds four combined standard errors at the fixed test seed |
| R3 | The shared alpha = 10% estimate is >= L and agrees with crude MC | Below L, or difference exceeds four combined standard errors |
| R4 | Sampling uncertainty is smaller than crude MC on the three alpha = 25% headlines | Residual standard error exceeds crude standard error on any headline |

Premortem: a supplied cut is not failing for the sampled model, or its durations or node
order differ. The algebra then fails; certificates and node-order checks are prerequisites.
Steelman: crude MC already agrees with the bracket; residual sampling earns its use only
by recovering known probabilities and reducing measured error on these instances. Variance
reduction is not asserted for every network. Zero observed residuals are not proof of zero
residual probability; use an exact binomial interval, not a collapsed normal interval.

## W2: export severity and partial losses (2026-10-16)

Registered before historical acquisition or severity computation. The user approved
`specs/2026-10-16-policy-severity-design.md` on this date. The primary outcome is export
volume in the first full calendar year after onset, relative to the previous calendar
year and untreated, surveyed exporters of the same concorded HS6. Annual data cannot
identify a response within exactly twelve months. Exports are not production.

| Leaf | Falsifiable answer | Kill condition |
| --- | --- | --- |
| S1 | Quotas/prohibitions reduce export volume by >= 50%; separate and combined estimates | Upper 95% loss limit < 50% kills; lower >= 50% supports; otherwise inconclusive |
| S2 | Export taxes reduce volume by < 20% | Lower 95% loss limit >= 20% kills; upper < 20% supports; otherwise inconclusive |
| S3 | Assigned partial losses lower failure by >= 5 percentage points in each sector at alpha = 25% | Upper 95% paired-difference limit < 5 points kills; lower >= 5 supports; otherwise inconclusive |

Estimate a stacked event study with exporter-within-event and year-within-event effects,
relative years -2, 0, +1 and omitted -1; normalized volume Q/Q_(t0-1); equal event and
within-event control weights. Use BACI HS12 2012–2023, onset years 2014–2022, isolated
measure types and verified concordances. Missing quantity is not zero. Controls require
survey coverage and no active restriction or onset in the event window. Country-cluster
bootstrap: 2,000 draws, seed 6. Fewer than five isolated events leaves a claim untestable;
fewer than ten treated countries makes inference weak. A pretrend interval excluding
zero leaves the response descriptive and the causal claim untestable.

Premortem: pretrends, simultaneous measures, untreated-control contamination, trade
diversion, incomplete quantities or a concordance change explain the observed response.
Record each exclusion and identification check. Steelman: a legal onset removes little
export volume, and any export response need not be a capacity loss. Thus f_m = clip(-beta,
0,1) is an explicit scenario assumption, with interval-endpoint sensitivities. Unknown
measure effects retain full loss; pooled measure mixes for unexposed nodes are labelled.
Use 20,000 paired draws per sector, seed 7, at alpha = 25%, h = sigma = 0; samplewise
partial shortfall <= full shortfall is a mandatory certificate independent of S3.
