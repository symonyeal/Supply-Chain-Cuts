"""Transcribe the completed W3 bundles into publication tables."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent / 'Chokepoint-Lab'
C = R / 'results/chemistry-896581f/cuts'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
x = read(C / 'liion_free_a0.25_h0_s0_L6.json')
y = read(C / 'liion_bounded_a0.25_h0_s0_L6.json')
assert x['cuts'] == y['cuts']
for p in C.glob('*.json'):
    z = read(p)
    assert z['complete'] and not z['stamp']['dirty']
    assert all(t['certified'] for t in z['certificates'])
assert len(list(C.glob('*.json'))) == 94
rows = x['legacy_comparison']['metals_restated']
assert len(rows) == 29 and all(z['shortfall'] == 0 and not z['fails'] for z in rows)
text = '''# Every former cobalt or precursor cut survives with chemistry choice

The headline uses alpha = 25%, h = sigma = 0, a 24-month horizon and outages up to
12 months. Capacities stay at the reference 50/50 blend. The two approved aggregate
NCM-share ranges [0,1] and [0.25,0.75] give identical failure events (MODEL, restored
second-year argument). This is hypothetical recipe flexibility, not measured plant
switchability. No nickel-containing minimal cut existed at this reference headline.

Sources: `results/chemistry-896581f/cuts/liion_{free,bounded}_a0.25_h0_s0_L6.json`,
producer `d18c743`; both clean. Each row below restates one former minimal cut; zero
means no unmet cell demand, not merely a shortfall below the failure threshold.

| Former cut (country, product, months) | Shortfall, free choice | Shortfall, bounded choice | Still a cut? |
| --- | ---: | ---: | --- |
'''
for a, b in zip(rows, y['legacy_comparison']['metals_restated'], strict=True):
    assert a == b
    name = ' + '.join(f'{c} {p} {d}' for c, p, d in a['losses'])
    text += f'| {name} | 0% | 0% | no |\n'
(R / 'docs/CHEMISTRY.md').write_text(text, encoding='utf-8')
summary = '''## Current answer: chemistry choice (v0.3.0)

With hypothetical LFP/NCM recipe flexibility and unchanged reference capacities, there
are **seven** minimal Li-ion cuts at alpha = 25%, h = sigma = 0. **Five** are Chinese
singletons lasting 12 months: AAM (46.795% shortfall), CAM (45.334%), cells (45.658%),
graphite (39.090%) and lithium carbonate (26.875%). The other two are China cells for
six months with Poland and US cells for twelve (25.031%, still trade-dependent), and
Australia, Chile and China lithium mines for twelve (31.006%). The reference fixed
50/50 model below has 37 cuts and seven singletons. Of those, 31 vanish and one new
lithium-mining triple appears. All 29 former cobalt or precursor cuts have **zero**
shortfall under either approved share interval; every one is restated in
[CHEMISTRY](CHEMISTRY.md). C2a and C2b both survive their registered kill conditions.

The 94 certified cases comprise 45 Li-ion configurations for each share interval and
two shared-network thresholds for each. The free and bounded lists agree in every
case. The share sensitivity is mathematically nonbinding here: outages end by month
12, a feasible 50/50 reference mix can serve the restored second year, and the
aggregate 24-month share is then between 25% and 75%. This does not test actual
manufacturing switchability or a monthly chemistry quota. At alpha = 10%, the Li-ion
list shrinks from 135 to 31; at 50% it remains empty. The shared lists shrink from
244 to 133 at 10% and from 180 to 100 at 25%.

| Network | Threshold | Exact L | L plus residual (95% sampling interval) | Residual failures / draws |
| --- | ---: | ---: | --- | ---: |
'''
for sector in ('liion', 'joint'):
    r = read(R / f'results/chemistry-risk-d18c743/{sector}.json')
    assert not r['stamp']['dirty'] and r['rates_unchanged'] and r['network_unchanged']
    for a in ('0.1', '0.25'):
        e = r['residual'][a]
        summary += (f"| {sector} | {float(a):.0%} | {e['L']:.9f} | {e['estimate']:.9f} "
                    f"[{e['ci95'][0]:.9f}, {e['ci95'][1]:.9f}] | "
                    f"{e['residual_events']} / {e['n']} |\n")
summary += '''
Cut bundle `chemistry-896581f` was produced at `d18c743`; risk bundle
`chemistry-risk-d18c743` at `980b2a7`. All stamps are clean. The cut worktree lacked
unused local-only event files, listed in its stamp; the locked capacity inputs were
present. Risk reused the frozen node order, rates and duration law exactly. Intervals
are Clopper–Pearson residual intervals conditional on this scenario, with seed 8 and
20,000 draws; they exclude model and source uncertainty. A zero residual count does
not prove exact equality to L. The approved severity study still cannot identify
capacity-loss fractions (W2 below), so these probabilities remain scenarios.

'''
p = R / 'docs/FINDINGS.md'
s = p.read_text(encoding='utf-8')
s = s.replace('## 1. Answer (Li-ion, v0.1.0)', summary + '## 1. Fixed-mix reference (Li-ion, v0.1.0)', 1)
p.write_text(s, encoding='utf-8')
p = R / 'README.md';s = p.read_text(encoding='utf-8')
i, j = s.index('**Seven single losses'), s.index('**What the data cannot show.**')
s = s[:i] + '''**Five Chinese single losses remain when the model may choose LFP or NCM recipes:**
cells, cathode material, anode material, graphite and lithium carbonate, each out for a
year. There are seven minimal cuts of at most three losses at a 25% shortfall threshold
over 24 months. China’s precursor and refined-cobalt singletons disappear; all 29 former
cobalt or precursor cuts have zero shortfall. This assumes recipe flexibility at fixed
reference capacities; actual plant switchability is unmeasured. The fixed 50/50
reference retains its original 37 cuts and seven singletons for comparison.

**Probability remains a scenario.** Under the same full-outage onset law, chemistry
choice gives Li-ion L = 0.288286 and lower bound plus residual 0.288286 (95% sampling
interval 0.288286–0.288471), versus 0.485681 for the fixed mix. The approved export
severity study yields only four isolated events and no identified measure effect;
its declared full-loss fallback therefore leaves the reference scenario unchanged.
Recorded onsets fail the predictive test. These are conditional probabilities, not forecasts.

**Solar has four Chinese singleton cuts and 22 cuts in all.** With chemistry choice,
the shared network has 100 cuts and no singletons at 25%, L = 0.105885 and estimate
0.106885 (95% sampling interval 0.106496–0.107429). A fresh independent reconstruction
reproduces all 22 solar and 180 fixed-mix shared cuts from raw inputs.

''' + s[j:]
s = s.replace('python run_severity.py RUN', 'python run_chemistry.py RUN 7                     # recipe-choice cut sweep\npython run_chemistry_risk.py CUT_RUN OUT_RUN       # frozen-law recipe-choice risk\npython run_severity.py RUN')
p.write_text(s, encoding='utf-8')

p = R / 'docs/VALIDATION.md';s = p.read_text(encoding='utf-8')
s += '''
## W3: alternative recipes

`tests/test_recipes.py` checks the hand-derived LFP route, bounded-share duals,
monthly/block equivalence, capacity dominance, random exhaustive/lattice/MILP equality,
baseline-failure empty cuts, and the restored-second-year share equivalence on 40
random states. The single LP matrix construction supplies the primal and MILP dual.
All 94 saved cut configurations are complete with certified primal/dual values and
immediate duration predecessors. Both registered singleton claims survive; every
former Co/Ni/pCAM headline cut is explicitly restated in CHEMISTRY. Risk checks the
unchanged network, rate law and feasible monthly 50/50 reference before reusing the
same failure event for the bounded interval. These are model certificates, not
evidence that actual plants can change chemistry.

## W6: fresh independent PV/shared reconstruction

Fresh agent, no production code, tests, analysis or result access. Portable programs
and named comparison inputs: `independent/pv_joint`; immutable report and numerical
artifacts: `results/independent-pv-joint`. The agent separately parsed BACI, USGS,
OECD SDMX, all 1,521 exposure rows from the methodology PDF, and selected primary
workbook/SI cells. All checked frozen hashes match. No coverage-row discrepancy.

Independent enumeration gives exactly 22 PV cuts (4/5/13 by support) and 180 fixed-mix
joint cuts (0/61/119). It visits 13,275 PV states and 2,802,195 mixed joint states;
no supplied cut is missing and no additional cut appears. Separate monthly LPs check
all 202 cuts and 532 predecessors; the greatest difference from the independent
cumulative-output recurrence is 2.998e-15. Independent L values are
0.2444939846405121 (PV) and 0.20382804118895667 (joint), versus production
0.2444939846075459 and 0.2038280411830003: numerical rate-fit differences below
3.3e-11. Counts (4,3,169), rho = 0.6557026896815004 and the roster agree.

Two diagnosed definition issues are retained in the report. Linked OECD/national
records count separately in duration weighting but once in node-year onset counts;
deduplicating durations would give (2,3,167). The preserved independent HHI output
initially omitted excluded origins from its numerator, changing cobalt/CAM rounding;
the portable script uses all origins. Neither issue changes the accepted cut/L
comparison. MIIT/Fraunhofer transcriptions, product mapping, legal completeness,
censoring and whole-node outage severity remain shared assumptions. W6 validates
the fixed-mix PV/shared headlines, not the later chemistry-choice scenario or the
predictive validity of rates. Raw excerpts with unverified reuse terms remain local.
'''
p.write_text(s, encoding='utf-8')
p = R / 'docs/DECISIONS.md'
with p.open('a', encoding='utf-8') as f:
    f.write('''
### 2026-10-16 — keep chemistry flexibility distinct from measured production

Use the approved shared-capacity recipes and 24-month delivered-output share bounds.
Measured outcome: five rather than seven singleton cuts, seven rather than 37 cuts;
all 29 former cobalt/precursor cuts have zero shortfall. Actual line switchability
is unknown. The [25%,75%] bound is nonbinding by the restored-second-year argument,
so identical results are not evidence of robustness to binding chemistry quotas.
The site defaults to choice, offers the fixed-mix reference in the same cut controls,
and explicitly retains fixed-mix labels on the severity study and E1 exhibit.
''')
p = R / 'docs/CHANGELOG.md';s = p.read_text(encoding='utf-8')
s = s.replace('## Unreleased — residual estimator and severity study', '## Unreleased — chemistry choice, residual estimator and severity study')
s = s.replace('- Estimate annual', '''- Approved shared-capacity LFP/NCM recipes: five Chinese singletons and seven headline
  cuts, versus seven and 37 in the fixed-mix reference. All former cobalt/precursor
  cuts restated; 94 certified configurations and frozen-law residual probabilities.
- All seven incomplete MILP checks now exhaust and equal their lattice lists.
- Fresh independent raw-input reconstruction reproduces all PV and shared reference
  cut sets and L, with definition issues and independence limits disclosed.
- Estimate annual''',1)
p.write_text(s, encoding='utf-8')
print('94 cut certificates audited; 29 former metal cuts restated; docs transcribed')
