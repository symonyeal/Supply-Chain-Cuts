# Changelog

## Unreleased — residual estimator and severity study

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
