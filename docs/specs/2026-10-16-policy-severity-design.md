# Policy severity: proposed research design

Status: awaiting review. Implements NEXT.md W2; no new severity results have been computed.

## Question and proposed answer

How much does export volume change after each kind of restriction, and how does a stated
conversion of those changes to capacity losses alter the three failure scenarios?

The falsifiable answer is that quotas and prohibitions remove at least half the affected
export volume, while export taxes remove less than one fifth. Licensing and other measure
types are estimated without a directional claim. Exports measure shipments leaving a
country, not its production or capacity. A measured export response can inform a capacity
scenario; it cannot by itself validate that conversion.

## Frozen observations and event definitions

Freeze the existing selected HS6 set from BACI HS12 V202601 for 2012–2023, one selected CSV
per year. Extend the existing byte-range extractor without overwriting the 2024 snapshots.
Store archive-member and selected-file SHA-256 digests, acquisition date, URL and Etalab
2.0 licence in the manifest and SOURCES.lock. Source: CEPII BACI, recorded in RESEARCH §1.

Aggregate quantity q in tonnes by exporter, HS6 and year. An absent bilateral row is zero
trade, since BACI records positive flows; an existing row without q makes that exporter–HS6
year incomplete, so exclude that observation. Exclude controls and treated units lacking
a complete, positive baseline quantity; retain complete zero exports after treatment.
Do not replace missing quantities with zeros or infer policy-free years from missing OECD
coverage.

Use the restrictive introduction/increase records behind `events.node_years`, retaining
their original OECD measure type and HS2007 product mapping. Include national acts only
where their affected HS6 and prohibition/licensing type have a verified concordance.
Check each HS2007 code against HS2012; identical digits alone are not evidence of an
unchanged definition. Report unmapped or unsupported onsets as exclusions.

Deduplicate onset records at exporter × HS6 × measure × onset year, retaining source ids.
The main estimate uses isolated measures: exclude another measure type on the same
exporter–HS6 in the event window. Report the simultaneous-measure group separately.

## Estimator and timing

Annual data cannot identify a loss within exactly twelve months. The primary outcome is
the first full calendar year after the effective onset year t0, relative to t0−1. The
onset year is a secondary outcome because it mixes pre- and post-measure months.

For each onset, use a window t0−2,...,t0+1 (onsets 2014–2022). Controls are other exporters
of the same HS6, with observed OECD coverage and no active restriction or restrictive
onset during that window. Where this leaves no qualifying controls, the onset is not
identified and is reported as such. Do not assume unsurveyed exporters are untreated.

Let Q_i,t be complete export volume and y_i,t = Q_i,t/Q_i,t0−1. Fit the stacked event
study with exporter-within-event and year-within-event effects, plus a treated exporter
indicator interacted with relative year and measure type. Omit relative year −1.
Each event has equal total weight; controls within an event have equal weight. Thus a
coefficient is a change in baseline-volume units relative to the controls. Exporter and
year effects identify differences in changes, not level differences. Report relative
years −2, 0 and +1, event counts, unique exporters, HS6 counts and uncertainty.

Use a country-cluster bootstrap (2,000 draws, seed 6), keeping every repeated onset and
HS6 of a sampled country together. Report percentile 95% intervals. With fewer than ten
treated countries, mark inference weak; fewer than five isolated events makes the
measure-type claim untestable. Diagnose a pretrend when the relative-year −2 interval
excludes zero; such a response is descriptive and cannot support a causal severity claim.

Parallel trends, no unrecorded overlapping measures, no trade diversion into the controls,
and correct concordance are identification assumptions. All are plausible failure modes,
not established facts. Report the pretrend and simultaneous-measure exclusions alongside
each main estimate; report quotas and prohibitions separately and jointly.

## Registered claims and kill conditions

Before fetching or estimating, append these claims to HYPOTHESES and commit:

- S1: the first-full-year export loss for quotas/prohibitions is at least 50%; killed if
  the upper 95% loss limit is below 50%, supported if its lower limit is at least 50%,
  otherwise inconclusive. Report the combined group and each code separately.
- S2: the loss for export taxes is below 20%; killed if the lower limit is at least 20%,
  supported if its upper limit is below 20%, otherwise inconclusive.
- S3: partial losses lower failure probability by at least five percentage points in
  each sector at alpha = 25%; killed if the upper 95% paired difference limit is below
  five points, supported if its lower limit is at least five, otherwise inconclusive.

A pretrend or insufficient isolated observations leaves S1/S2 untestable rather than
silently classifying an uncertain estimate as surviving. Register these verdict rules
before any severity computation.

## Conversion to a capacity scenario

For measure m set f_m = min(1,max(0,−beta_m,+1)). This clipping is an explicit scenario
conversion; keep the unclipped export estimate and interval in the severity table. Run
the interval endpoints as sensitivities. A positive export response maps to zero loss.
For unidentified measure types, retain full loss as the conservative fallback and report
the share of sampled onsets to which it applies. No measured severity is assigned to
unexposed midstream/cell products: their pooled measure mix remains a scenario assumption.

Retain the existing onset rates, country-shock law and legal-measure durations. Conditional
on a node onset, draw its measure type from the observed product-specific mix, falling back
to the observed all-product mix when necessary. Mark those fallbacks. Duration and measure
type are independent in this scenario; do not imply that this dependence was estimated.

Use 20,000 paired draws (seed 7) for each sector at alpha = 25%, h = sigma = 0. Solve the
same state with f = 1 and with the assigned f_m. Every partial shortfall must be no larger
than its full-loss shortfall within the LP tolerance. Full-loss cuts provide no lower
bound for partial losses. Estimate partial failure directly by MC with a binomial 95%
interval and compare paired full-loss MC with the W1 residual estimate. Report the three
scenario types side by side, with their registration and identification limitations.
The paired difference indicator is full-loss failure with partial-loss survival; its
binomial interval supplies the S3 check. Monotonicity is a required mathematical
certificate, separate from the empirical claim of at least five points' reduction.

## Definition of done

Every registered claim has a verdict and its numbers, or a named identification failure.
DATA records export responses, intervals, counts, exclusions and the f_m conversion.
Li-ion, PV and joint bundles contain partial-loss estimates and paired monotonicity checks.
The site labels each scenario and the assumptions that connect trade to capacity. The
gate, frozen hashes, builder certificates and mobile/desktop render pass. Unidentified
effects remain an explicit scientific gap.
