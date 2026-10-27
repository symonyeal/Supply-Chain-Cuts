# Observational context

`python analysis/build_context.py` verifies the frozen USGS CSV, its metadata XML,
and the IEA chart-options JSON against `SOURCES.lock`, then writes
`site/context.js` and `site/context.csv`. It makes no network requests. The CSV
contains both datasets with explicit dataset labels. Blank numeric cells remain
missing; zero is written as zero. Regeneration is deterministic.

`python analysis/build_context.py --fetch-iea` also reacquires the source chart
options from the IEA page. It selects the named chart, decodes its embedded options,
and writes them only if the numerical JSON still matches the frozen SHA-256.
Changed upstream data require a separate, explicit source-vintage update.
Country display names come from the hash-verified BACI country-code table.

USGS Mineral Commodity Summaries 2026 provides 240 production rows: 224 country or
other-country rows and 16 world-total rows. The eight commodity and process pairs
are lithium mine, cobalt mine, nickel mine, natural graphite mine, copper mine,
copper refinery, manganese mine and aluminum smelter. Each has 2024 and 2025 data.
Thousand metric tons are multiplied by 1,000. Manganese is manganese content,
as specified by its world-production section; its chapter-wide gross-weight note
also remains in `source_notes`. Metal contents differ between commodities, so
adding their tonnes is not a meaningful total.

Raw values, source notes and estimated flags remain alongside numeric tonnes.
The USGS metadata defines an em dash as zero and W as withheld. Withheld U.S.
lithium is null, never zero. Its published world total excludes U.S. output;
lithium shares therefore exclude that withheld output. World rows are explicitly
marked, never ranked as countries. Other countries is an aggregate, never a named
country.

Shares divide by the published rounded world total. They are not renormalized:
rounded country figures may not sum to that total. The named-country top share
and sum of three largest named-country shares describe available named records.
Where other-country or withheld production exists, a top-three sum is a lower
bound on concentration under the published denominator, subject to rounding;
it is not a complete-country concentration estimate. No HHI is calculated.

IEA's *Market size and top refining country share for select minerals, 2025*
provides 16 points in four groups. The frozen JSON preserves the chart's actual
series and coordinates: x is the leading refining country's percent share;
y is market size in billion USD. The browser export converts x to a fraction.
The chart does not identify that country, so the export assigns no country.
The source's label `Geranium` is retained and identified as a source spelling;
it is not silently relabelled. These data carry IEA attribution and CC BY 4.0.

`window.CONTEXT` contains `meta`, `production`, `refining` and `summaries`.
Production rows have commodity, stage, year, country, tonnes, raw, notes,
source_notes, estimated, aggregate, world, missing and share. Refining rows have
name, group, top_share, market_usd_bn and year. Shares are fractions, not percent.
Summaries carry world_tonnes, named_top_country, named_top_share,
named_top3_share, has_aggregate, has_missing, coverage_note and concentration_label.

This context does not update reference network capacities or reproduce a new
optimization. Production is output rather than installed capacity; market value
and refining concentration are separate indicators. The historical cut sets and
conditional probability results retain their original data and assumptions.
