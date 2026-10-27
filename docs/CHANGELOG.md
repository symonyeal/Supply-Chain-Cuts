# Changelog

## 2026-10-27: native Rust pipeline

- Add the `supply` executable: source verification, observational context, networks,
  recourse LPs on vendored HiGHS 1.12.0, lattice cut enumeration, exact cut-union
  bracket, residual Monte Carlo, explorer payload and a local static server.
- Native risk runs take an explicit frozen onset law and refuse a cut certificate from
  a different network, configuration or incomplete search.
- Python remains the default backend of `chokepoint` and the independent oracle; CI
  compares networks, LP certificates, cut lists, brackets, sampling streams and the
  rebuilt explorer payload with it.

## 2026-10-27: explorer redesign and optional Rust kernel

- Add a responsive supply-chain atlas with battery, solar and shared-network settings,
  input-stock and recovery controls, pinned comparisons, saved scenario URLs, cut-size
  and supplier filters, and CSV downloads. Keep full reference research tables accessible.
- Expose all 417 saved configurations without interpolation. Explain conditional
  probability, unsupported settings, overlapping contributions and source-basis limits.
- Add 240 USGS production records for 2024–2025 and 16 frozen IEA refining observations
  for 2025, with raw flags, source hashes, world-total denominators and downloadable data.
- Add an opt-in Rust exact-union backend, full-range binary64 comparator and measured
  batch timing. Retain the reference LP, independent enumerators and Python default.
- Add browser verification across the full saved range, downloads, URL round trips,
  invalid settings and six viewport/theme pairs. Gate Pages on the checked revision.

## v0.3.0 — 2026-10-17: chemistry choice, residual estimator and severity study

- Approved shared-capacity LFP/NCM recipes: five Chinese singletons and seven headline
  cuts, versus seven and 37 in the fixed-mix reference. All former cobalt/precursor
  cuts restated; 94 certified configurations and frozen-law residual probabilities.
- All seven incomplete MILP checks now exhaust and equal their lattice lists.
- Fresh independent raw-input reconstruction reproduces all PV and shared reference
  cut sets and L, with definition issues and independence limits disclosed.
- Freeze METI Japan charge output, selected EU Prodcom rows, keyless China tariff-line
  diagnostics and Co/Ni global end-use shares. Fourteen certified source/allocation
  variants; Japan removes one choice cut. Report baseline shortages at fixed demand.
- Recompute all 18 located-capacity denominators; zero verified numerators keep
  natural hazards as scenarios. Raw inputs with unverified terms remain local.
- Estimate annual scenario failure as exact L plus sampled residual failures, with an
  exact-binomial interval even when no residual failure is observed. IS and crude MC
  remain comparisons; original bundles are unchanged.
- Three new `*-residual-2395a5c` bundles, with legacy-result and sampling certificates.
- The site and answer use the residual estimate and show L. On the shared network at
  alpha = 10%, estimate 0.715669, L = 0.715669, interval 0.715669–0.715853.
- W2 severity design approved and S1–S3 registered before historical BACI acquisition.
- Freeze BACI 2012–2023 and UN HS concordance. The approved study yields four isolated
  events, no identified measure effect; S1/S2 untestable. Severity scenarios for all three
  networks retain the declared full-loss fallback; S3's five-point reduction is killed.
- Side-by-side scenario and export-response tables; cut-duration predecessors, shared
  PV controls, and an explanation of U = 100%.
- Preserve frozen data bytes in Git and verify committed hashes. Recover the association
  between older sorted cut lists and their unsorted witnesses; future runs align them.

## v0.2.0 — PV on the shared network

- PV chain polysilicon → wafer → cell → module (BACI HS22 2024; MIIT 2024 China
  production; 2.0 g Si/Wp), alone and on one network with Li-ion. Demand equals the
  undisrupted achievable output (PV 0.991 of retained modules).
- PV sweep with exhaustive search on the whole 15-node network as the certificate;
  joint network at h = σ = 0.
- PV rates fitted on the joint node set; only polysilicon has OECD exposure.

## v0.1.0 — Li-ion cut sets and the scenario bracket

- Recourse LP in requirement units over exact blocks of constant data (Lemma A).
- Interdiction MILP with upper-orthant exclusions and duration certificates; lattice
  search by capacity dominance (Lemma B); exhaustive search; all three agree where run.
- 111-node 2024 network: USGS MCS 2026 and MYB 2023, MIIT, Cochilco, BACI, Xu et al.
  2020; basis label on every node; 74 frozen sources in `SOURCES.lock`.
- Policy onsets derived from the OECD Inventory and national acts; empirical-Bayes
  rates with a country shock; exact L, U and importance sampling.
- Registered tests A1–E1 and the three day-1 claims evaluated (FINDINGS.md).
- Site on GitHub Pages; result bundle `results/liion-60eb399`.
