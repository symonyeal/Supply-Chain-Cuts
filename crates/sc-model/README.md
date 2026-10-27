# Native recourse model

`Model::from_network(network, config)` builds the material-balance LP in
`docs/MODEL.md` from the same physical-network JSON used by the Python reference.
`Model::solve(state, dual, loss)` solves the primal and, when requested, its
separate bounded dual. It returns status, cumulative shortfall `phi`, dual
objective, primal-dual gap and maximum primal residual. The model retains its
matrices across states; each solve creates a fresh HiGHS instance, matching the
reference's cold solves.

The configuration accepts `T`, `h`, `sigma`, `L`, `durations`, `aggregate`,
`choice` and `shares`. Chemistry choice requires the original 50% reference
network plus `network.recipe_bom = [bill(0), bill(1)]`; these are the endpoint
bill-of-materials structures calculated from the frozen source by `sc-data`.
It supports full node outages and an optional vector of partial loss fractions.
Disruption durations must be zero or one of the model's block ends.

`evaluate(network, config, states)` wraps a batch, returning each state and its
certificate plus block ends, matrix dimensions, total demand and the linked
solver version. The `sc-model-check` executable reads and writes JSON lines for
the comparison harness. The production command uses the library directly.

## Solver source

The vendored solver is [HiGHS 1.12.0](https://github.com/ERGO-Code/HiGHS/tree/755a8e027a99a8d4ecf153a8dde4b2a767cdf384),
the solver version bundled by the SciPy 1.17.1 reference environment. Its source
is distributed under the [MIT licence](HiGHS/LICENSE.txt). `UPSTREAM.json`
records the exact upstream revision, selected source count and byte count, and
a SHA-256 of the selected relative paths and contents. Upstream C++/C sources
are unmodified. Disabled test/example/documentation payloads are omitted;
the CMake entry files needed for the disabled targets remain.

The `cmake` build dependency is pinned to 0.1.58. A C++ compiler and CMake are
required when building; Python is not required to build or run the executable.
Release compiler flags enable optimization, without fast-math or floating-point
contraction. Presolve is enabled and the simplex strategy is 1, matching the
explicit SciPy `linprog(method="highs")` settings. The solver's other defaults
remain at the matching version's defaults.

Keep `CARGO_TARGET_DIR` in the working folder. Deep Windows paths can exceed
MSBuild's path limit; a `subst` alias to that folder keeps generated paths short.
This changes the path used by the build while retaining files in the working
folder. Build and cache paths are runtime configuration, never source paths in
the manifest.

## Comparison

`python -m analysis.check_native_model --out <evidence-folder>` captures fresh
Python certificates. `--compare --binary <sc-model-check>` compares native
outputs with that baseline and times both implementations on the same inputs.
It retains every numeric discrepancy by configuration, complete node-duration
vector and field; it reports exact-bit counts separately from the declared
`1e-7` absolute solver tolerance. Status, dimensions, block ends, state keys and
failure classifications are checked separately. Planted wrong values and a
missing state must fail before the comparison is used.

The bounded baseline covers every saved fixed/choice configuration, including
both share bounds. It includes all saved cuts and their immediate predecessors
when `h=0`; for `h>0` it includes the baseline, the first cut and all of that
cut's immediate predecessors. Full-node 3/6/12-month probes and partial-loss
checks cover batteries, solar and their shared network. The unsampled stock
cut/predecessor combinations remain unmeasured. Exact result counts, differences
and timings are recorded in the comparison artifacts, not inferred from solver
version equality.

The 2026-10-27 comparison covered 192 cases and 5,962 states. All 23,848
numeric certificate fields (`phi`, `dual`, `gap`, `residual`) matched the
Python baseline bit for bit. Configuration/state keys, solver statuses, matrix
dimensions, block ends and failure classifications also matched, with no
exceptions. The comparator rejected both deliberately wrong values and a
missing state before checking the real output.

The initial implementation's same-input timing pass took 143.986 seconds in
Rust and 229.739 seconds in Python, including Rust JSON/process overhead. That
pass exposed 213 residual signed-zero differences, corrected by preserving
Python's first-operand zero tie. Every objective and dual already matched.
The final native-only rerun after that correction took 116.728 seconds and
returned the exact comparison above. These are single passes during concurrent
development, not a stable runtime distribution or a whole-pipeline benchmark.

The evidence folder `supply-chain-redesign-20261027/native-model` retains the
fresh baseline, inputs, both native outputs, the first timing report and final
comparison report. Python remains available for independent comparison and
for scopes not covered by this certificate, including other horizons and the
unsampled stock-cut combinations.
