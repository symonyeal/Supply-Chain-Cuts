# Changelog

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
