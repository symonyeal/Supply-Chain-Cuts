# Optional Rust probability backend

The Rust executable evaluates the exact probability that at least one supplied
duration cut occurs. It implements the memoised decision recursion in
`chokepoint.risk.exact_union`, with the same country grouping, common-shock law,
duration accumulation, cut ordering and floating-point operation order.
The Python implementation remains the default and the comparison oracle.
The recourse LP, cut enumeration, rate fitting and sampling remain in Python/SciPy.

## Build and call

Build with the pinned Rust 1.99.1 toolchain:

```powershell
$env:CARGO_TARGET_DIR = '<working folder>/rust-target'
cargo build --release --locked --manifest-path crates/cut-risk/Cargo.toml
$env:CUT_RISK_BIN = '<working folder>/rust-target/release/cut-risk.exe'
```

On Linux/macOS the executable is named `cut-risk`. Build and cache directories
can be set with Cargo's `CARGO_TARGET_DIR` and `CARGO_HOME` environment variables.

The Python wrapper accepts the same six arguments as the original function:

```python
from chokepoint.risk import exact_union

L = exact_union(V, p, rho, durations, weights, cuts, backend="rust")
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
The executable boundary/protocol tests returned `2 passed`; scoped Ruff and
Rust Clippy checks passed. The rest of the model is outside this port's scope.

## Measured time

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
