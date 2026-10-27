# Native Rust pipeline

`supply` runs source verification, contextual data processing, network construction,
recourse LPs, cut enumeration, exact probability, residual Monte Carlo, explorer
payload generation and serving without launching Python. Python remains the
independent numerical oracle and retains the historical onset-rate calibration,
severity and importance-sampling tools. A native risk run takes an explicitly
supplied frozen onset law; it does not refit rates.

## Build and use

The pinned toolchain is Rust 1.99.1. Building the vendored HiGHS solver also requires
CMake and a C++ compiler; Windows builds use the Visual C++ toolchain.

```text
cargo build --release --locked -p supply
target/release/supply --help
target/release/supply verify
target/release/supply build
target/release/supply serve
```

Use `supply.exe` on Windows. `serve` defaults to `127.0.0.1:8000`.
Set `CARGO_TARGET_DIR` and `CARGO_HOME` to keep build and cache material in a chosen
working folder. `--root` selects the source repository; `build --out DIRECTORY`
writes `data.js`, `context.js` and `context.csv` there. The explorer build reads
the immutable published result bundles and preserves their scientific scope.

| Command | Input and output |
| --- | --- |
| `verify` | Verifies committed source hashes against `SOURCES.lock` |
| `context` | Builds the separate production/refining context and downloadable CSV |
| `network` | Builds a physical network from frozen raw inputs; accepts source options in `--config FILE` |
| `evaluate --states FILE` | Solves recourse for arrays of node-outage durations; accepts `--network FILE` and `--config FILE` |
| `cuts` | Enumerates minimal cuts through the capacity-dominance lattice; returns completeness and primal/dual/predecessor certificates |
| `risk --law FILE --cuts FILE` | Computes the cut-union bracket and residual estimator using the supplied frozen law and matching native cut certificate |
| `run --law FILE --out DIRECTORY` | Verifies inputs, builds a network, searches cuts and evaluates risk; writes results and a manifest with binary, network, law and source-lock hashes |
| `probability` | Reads JSON-lines exact-union requests on stdin and writes probabilities and binary64 encodings |
| `sample-law --law FILE` | Generates seeded duration states from the frozen law |
| `interval` | Reads binomial `[events, draws]` pairs on stdin and writes intervals |

Configuration JSON controls source options (`sector`, `ncm`, `cutoff`, `basis`,
`exclude`, `japan_voltage`, `eu_sold`), recourse (`choice`, `shares`, `T`, `h`,
`sigma`, `L`, `durations`), search (`alpha`, `k`, `time_limit`) and sampling
(`n`, `seed`). Omitted fields keep reference behavior. Save this example as
`<working-folder>/scenario.json`:

```json
{"sector":"liion","choice":true,"T":24,"alpha":0.25,"h":0,"sigma":0,"L":6,"durations":[3,6,12],"k":3,"n":4000,"seed":0,"time_limit":60}
```

```text
target/release/supply run --config <working-folder>/scenario.json --law results/liion-residual-2395a5c/risk.json --out <working-folder>/native-run
```

Search and sampling default to 60-second limits. Inspect `status`, `complete` and
the certificates before interpreting an output. An incomplete cut search cannot
certify the risk upper bound; `run` records `incomplete_cuts` instead of treating
the search as exhaustive. Risk rejects a changed network or configuration and a
partial-loss configuration paired with full-outage cuts.

HiGHS 1.12.0 is vendored at revision
`755a8e027a99a8d4ecf153a8dde4b2a767cdf384` under its retained MIT licence.
`crates/sc-model/UPSTREAM.json` records its complete source-tree digest.

## Native comparison scope

| Stage | Checked range and result |
| --- | --- |
| Raw inputs to physical networks | 62 configurations spanning sectors, chemistry endpoints, source bases, cutoffs, supplements and exclusions; no value or list-order differences |
| Observational context | Exact JSON values and byte-identical UTF-8 CSV; 64 data checks including the networks |
| Recourse LP | 192 cases and 5,962 states; all 23,848 numerical fields binary64-identical, with no missing or structural differences |
| Explorer payload | 90,912 JSON nodes, including 63,956 scalar/empty-container leaves; full-precision and rounded outputs match Python; rounded output matches committed `site/data.js` |
| Exact cut union | All 432 compared probabilities are binary64-identical |

The recourse range uses T = 24 months. It includes cut states and predecessors,
single-node probes, recipe-choice configurations and limited stock/partial-loss
cases. Other horizons are unmeasured. These comparisons do not establish new
capacity observations, actual plant switchability or predictive policy rates.
Full cut-search validation is separate from state-by-state LP parity. Whole-pipeline
performance is unmeasured; timings collected during concurrent workstation work
are not an isolated benchmark.

Tests that need a native executable find it in `$CARGO_TARGET_DIR/release`
(default `target/release`) and skip until `cargo build --workspace --release --locked`
has produced it. The comparison commands are `analysis/check_native_data.py`,
`analysis/check_native_model.py`, `analysis/check_native_site.py` and
`analysis/check_native_pipeline.py`; their `--help` output describes artifact paths
and executable arguments. Python comparison paths explicitly select the Python
oracle. Keep the captured baseline and both directions of every diff.

## Probability compatibility interface

The `cut-risk` executable retains its JSON-lines interface. Build it with
`cargo build --release --locked -p cut-risk`, then set `CUT_RISK_BIN` to its path.
It uses the memoised decision recursion in `chokepoint.risk.exact_union`, preserving
country grouping, the common-shock law, duration accumulation, cut ordering and
floating-point operation order.
The Python wrapper accepts the original six arguments. Its default backend is the
Python oracle, so Python reference scripts never depend on the native build; select
the native kernel explicitly for a comparison:

```python
from chokepoint.risk import exact_union

L = exact_union(V, p, rho, durations, weights, cuts, backend="rust")
# Oracle (default): exact_union(V, p, rho, durations, weights, cuts)
```

`cuts` contains dense node-duration vectors. Set `CUT_RISK_BIN`, or use the
lower-level `chokepoint.rust.exact_union(..., binary=...)` wrapper.
A missing executable raises an error. Installation and
compilation never happen during imports. For many scenarios, use
`chokepoint.rust.batch(inputs)`, where each input is a dictionary with the keys
`V`, `p`, `rho`, `durations`, `weights`, and `cuts`.

The executable reads one JSON object per line and writes one result per line.
Each result contains `L` and `bits`, the hexadecimal IEEE-754 binary64 encoding
of `L`. Invalid requests return an `error` field, which the wrapper raises as a
`ValueError`. The batch wrapper preserves row order and checks response counts.
`serde` and `serde_json` handle the protocol; `float_roundtrip` preserves the
incoming probability values. The committed Cargo lock fixes their versions.

## Exact comparison on 2026-10-27

Run the complete saved-configuration comparison from the repository root:

```powershell
python -m analysis.check_rust --binary $env:CUT_RISK_BIN --out '<working evidence folder>'
python -m pytest -q tests/test_rust.py --basetemp '<working evidence folder>/pytest-rust'
```

The comparison rebuilds inputs from the full-precision committed result bundles,
without reading the rounded explorer data. It calculates both outputs afresh,
compares their binary64 encodings by configuration key in both directions, and
compares fresh Python results with the saved values. A deliberately wrong value
and missing-key pair must fail the comparator first.

| Range | Configurations |
| --- | ---: |
| Fixed battery, `liion-60eb399` | 135 |
| Solar, `pv-ba89465` | 135 |
| Fixed shared network, `joint-ba89465` | 6 |
| Battery recipe choice, `chemistry-risk-d18c743` | 135 |
| Shared recipe choice, `chemistry-risk-d18c743` | 6 |
| Boundary cases | 15 |
| Total per backend | 432 |

All 432 probabilities were bit-identical. Both missing-key lists and the
different-value list were empty. All 417 fresh saved-configuration results
also matched their committed `L` values exactly. Choice results cover the saved
free-choice law; the approved bounded-share configurations reuse that same law
and cut list, as recorded in their existing result bundles.

The boundary cases include no cuts, an empty cut, no nodes, probabilities zero
and one, common-shock share zero and one, mixed endpoint probabilities,
duplicate durations, duplicate/redundant cuts, duration zero and zero weights.
The initial executable boundary/protocol tests returned `2 passed`; scoped Ruff
and Rust Clippy checks passed. Those earlier tests cover the compatibility protocol;
the native pipeline comparisons are listed above.

## Historical kernel timings

On the Windows work laptop, the same 432 inputs took 35.832943 seconds in
Python and 5.311771 seconds through one Rust batch: 6.746 times faster for this
batch. The Rust measurement includes JSON serialization and process startup.
Each backend was timed once; this is a batch measurement, not a repeated-run
distribution or a whole-pipeline speedup. A single call through the wrapper
starts a process and has different overhead. Browser performance was not
measured by this benchmark.

A second independent execution of the same comparison returned the same 432
identical results, taking 30.216494 seconds in Python and 5.043552 seconds in
Rust (5.991 times faster). These two measurements illustrate runtime variation;
neither measures the complete optimisation pipeline.

The baseline was captured before writing the Rust implementation. Evidence is
retained in the working folder `supply-chain-redesign-20261027`:
`rust-python-baseline.json`, `rust-oracle.json`, `rust-output.json` and
`rust-parity.json`. No outage probabilities, duration weights or business
thresholds were changed or introduced by this port.
