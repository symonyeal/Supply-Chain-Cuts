# Decisions

Each entry: the decision, the alternatives measured, the measurement, the date.

Decisions taken with the user during design (2026-10-15) are recorded in the
[design](specs/2026-10-15-chokepoint-design.md): country × product nodes over firms;
Li-ion first, then PV; capacity network with recourse; exact interdiction checked by brute
force; hybrid probability (bounds, then importance sampling); policy and natural hazards,
with natural hazards matched to production sites.

## Open

- Natural-hazard site data: coverage threshold 70% per layer, else the sensitivity
  fallback (design §5). To be measured at the start of phase P.

## Tested and refused

- GDELT as an event source: no product field ([Research](RESEARCH.md) §7).
- ACLED, Global Trade Alert: licence terms restrict publication ([Research](RESEARCH.md) §4, §6).
- WTO QR notifications: no filings from the producer countries that matter ([Research](RESEARCH.md) §12).
