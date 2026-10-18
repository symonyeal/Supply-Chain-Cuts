"""Transcribe all fourteen W5 scenario certificates, without refitting probabilities."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent / 'Chokepoint-Lab'
rows = []
for p in sorted((R/'results/supply-4ae36c1').glob('*.json')):
    x = json.loads(p.read_text())
    assert x['complete'] and not x['stamp']['dirty']
    assert all(t['certified'] for t in x['certificates'])
    rows.append(x)
assert len(rows)==14
text = '''

## W5: capacity sources and competing demand change different parts of the answer

Bundle `supply-4ae36c1`, producer `7b810a3`, clean stamps, alpha = 25%, h = sigma = 0,
24 months, duration <= 12, support <= 3. Every list is complete, with matching
primal/dual values and shorter-duration witnesses. N1/N2 were registered at
`e585992`, before any of these results. Source details and limitations are in DATA.

| Variant | Chemistry | Nodes | Baseline shortfall | Minimal cuts | Vanish / appear vs respective reference |
| --- | --- | ---: | ---: | ---: | ---: |
'''
for x in rows:
    text += (f"| {x['case']} | {'choice' if x['flexible'] else 'fixed 50/50'} | "
             f"{len(x['network']['nodes'])} | {x['baseline_share']:.6%} | "
             f"{'1 (empty)' if x['cuts']==[[]] else len(x['cuts'])} | "
             f"{len(x['vanish'])} / {len(x['appear'])} |\n")
text += '''
Japan's annual METI output at either assumed 3.2 or 3.7 V removes the trade-dependent
China cells 6-month + Poland and US cells 12-month triple from the chemistry-choice
list. Six cuts remain, including all five Chinese singletons. The newly retained
Japanese cell/CAM/AAM nodes and changed final-output normalisation explain the
fixed-mix boundary changes (36 cuts, not 37). These are source/voltage variants,
not evidence of actual plant flexibility. German Prodcom combined-purity carbonate
sold output (24,728 t; `imputed`) changes no cut at this headline. The combined
METI/Prodcom result equals the METI cut list. These variants have no probability
refit; the frozen-law W3 comparison uses the original reference capacities.

Co/Ni reservation at their published global battery shares makes the fixed-mix
baseline fail even without outages: 67.794261% shortfall. N1 survives, but its
scientific implication is incompatible allocation/throughput assumptions, not a
new observed chokepoint. The sole minimal cut is empty. Flexible recipes meet
baseline demand and retain all seven original choice cuts when Cu/Al/Mn availability
is 100% or 10%. At 1%, fixed/flexible baseline shortfalls are 75.341298% and
74.819450%; N2 survives under both recipes. No demand rescaling conceals the shortage.
All global-to-country allocations and the three Cu/Al/Mn fractions are scenarios;
these results do not identify actual competing-use behaviour during disruptions.

`inputs-7b810a3`, `japan-7b810a3` and `supplement-7b810a3` rerun the data pipeline:
111/114/115 Li-ion nodes respectively; 15 PV throughout. All 128 locked sources
verify and all 52 committed source blobs match their frozen bytes; every original
88-source hash is unchanged. The retained first reconciliation snapshot records
the diagnosed missing-parent/zero reporting error and is superseded by the corrected
snapshot; no capacity result used that missing BACI quantity.

The other acquired sources terminate with explicit scope limits. Keyless Comtrade
partner batches reproduce the preview rows but repeated dimensions and a precursor
row-sum/BACI-parent ratio 2.847 prevent a unique-flow aggregate. Four graphite lines
return no rows, not measured zero exports. No capacity basis changes from those
trade diagnostics. EU actual production is unavailable; LFP-only sales do not
replace aggregate CAM, confidential values stay missing, and zero sold LiOH does
not establish absent productive capacity. No qualifying Korean domestic physical
cell series was located; its flagged trade proxy remains. BGS statistics remain
unused pending licence clarification. These are terminal data outcomes, not claims
that all source gaps have been filled.
'''
p = R/'docs/FINDINGS.md';p.write_text(p.read_text(encoding='utf-8')+text,encoding='utf-8')
p = R/'docs/VALIDATION.md';s=p.read_text(encoding='utf-8');s+='''

## W5: source and allocation checks

Full gate: 40 tests passed, including both supply-accounting tests. METI kAh-to-GWh
conversion and imputed labels are checked at 3.2/3.7 V. A reservation toy verifies
unchanged demand and exposes a baseline shortfall instead of rescaling it away.
`data.research.supplement` regenerated all selected observations and reconciliation
bytes exactly. All nine disjoint partner batches reproduce the three nonempty
preview multisets; neither that check nor counts below 500 prove completeness.
The five Eurostat slices retain quantity flags; combined German carbonate equals
the two purity-category estimates. Missing/confidential is never converted to zero.

All 14 `supply-4ae36c1` cases have complete lists and optimal baseline certificates,
with zero dirty paths. N1 survives (67.794261% fixed-mix baseline shortage); N2
survives (75.341298% fixed / 74.819450% choice at 1% Cu/Al/Mn). METI changes choice
cuts 7 -> 6; German sold-carbonate proxy 7 -> 7. Capacity-source variants do not
reuse a newly fitted probability or claim independent recomputation of W3/W5.
''';p.write_text(s,encoding='utf-8')
p = R/'docs/DECISIONS.md';s=p.read_text(encoding='utf-8');s+='''

### 2026-10-17 — keep new source scopes and allocation failures explicit

METI charge output times assumed voltage enters an imputed supplement, not the
unchanged-reference chemistry probability comparison. Six choice cuts replace seven;
five Chinese singletons remain. German sold carbonate is a separate imputed proxy;
it changes no headline cut. LFP-only sales cannot identify aggregate CAM capacity.
Comtrade rows do not reconcile as unique complete flows, so precursor remains imputed.
No Korean physical-output source qualified. Verified Eurostat/e-Stat reuse terms
permit the selected data; raw sources with unresolved terms remain local.

The user approved fixed-demand Co/Ni reservations and assumed Cu/Al/Mn fractions.
Their fixed-mix baseline already loses 67.8%, whereas recipe choice meets demand at
10% Cu/Al/Mn availability. At 1% both fail without outages. Preserve those failures
and the empty-cut certificates; do not renormalise demand or label them forecasts.
The first reconciliation incorrectly printed zero for an unselected BACI parent;
retain it as v1 and correct that field to missing in the current snapshot, preserving
all source hashes. No model result uses that field.
''';p.write_text(s,encoding='utf-8')
p = R/'README.md';s=p.read_text(encoding='utf-8');s=s.replace('**What the data cannot show.** Outside China, cell and refined-nickel capacity rests on export\nmass; precursor capacity is imputed from cell output; upstream metals have no competing\ndemand;', '''**New capacity data matter.** The METI Japan supplement (assumed voltage, imputed)
removes the trade-dependent cell triple, leaving six choice cuts and the same five
singletons. A German sold-carbonate proxy changes no headline cut. The registered
competing-demand sensitivity exposes baseline failures under some allocations;
it is reported without reducing demand to hide them.

**What the data cannot show.** Most non-China cell and refined-nickel capacity still
rests on export mass; precursor is imputed; country-specific competing demand is unknown;''')
p.write_text(s,encoding='utf-8')
p = R/'docs/CHANGELOG.md';s=p.read_text(encoding='utf-8');s=s.replace('- Estimate annual','''- Freeze METI Japan charge output, selected EU Prodcom rows, keyless China tariff-line
  diagnostics and Co/Ni global end-use shares. Fourteen certified source/allocation
  variants; Japan removes one choice cut. Report baseline shortages at fixed demand.
- Recompute all 18 located-capacity denominators; zero verified numerators keep
  natural hazards as scenarios. Raw inputs with unverified terms remain local.
- Estimate annual''',1);p.write_text(s,encoding='utf-8')
p = R/'docs/specs/2026-10-16-chemistry-choice-design.md';s=p.read_text(encoding='utf-8');s=s.replace('Status: approved by the user, 2026-10-16, with 24-month share bounds; no chemistry-choice\nresults computed.', 'Status: approved by the user, 2026-10-16, with 24-month share bounds; implemented and\ncertified in the W3 bundles (FINDINGS, CHEMISTRY).');p.write_text(s,encoding='utf-8')
print('14 certified supply variants transcribed; N1/N2 survive; limitations retained')
