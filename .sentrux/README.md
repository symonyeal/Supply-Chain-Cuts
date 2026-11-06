# Advisory Rust structure checks

Sentrux 0.5.7 scans only the first-party Rust sources and Cargo manifests selected by `scope.json`.
The recourse and probability kernels may not depend on the pipeline or site assembly.
Python remains an independent oracle and is outside this Rust baseline.

Run the shared `Claude Func Folder/sentrux/scan.py` helper:

```text
python "<shared runner>" "<repository>" "<new run label>"
```

It copies tracked source with its current working-tree bytes into an indexed scan directory,
checks the rules and compares `baseline.json`. Stage new source files first. Vendor code,
generated sites, data, archives, integration tests and build output are excluded; inline Rust tests
remain. Logs and source hashes stay under the shared runner's `evidence/` directory. Append
`--baseline` only after reviewing a proposed replacement baseline.

Known limitation, reproduced on 2026-11-06: the checker rejects a planted `use sc_site;` from
`sc-model`, but misses the qualified form `use sc_site::build;`. Passing rules therefore cannot
certify workspace boundaries. The shared runner now first checks Cargo's declared normal/build
workspace dependencies against these layers, regardless of import spelling. That check fails on
forbidden dependencies or unassigned crates; it includes target-specific declarations and excludes
dev dependencies. All five crates are assigned to library or pipeline layers. Sentrux's metrics and
within-crate graph remain advisory; no CI gate is added. Direct whole-repository
scans include tracked HiGHS and generated material and produce incomparable scores.

The local runtime has analytics disabled. Another machine needs Sentrux 0.5.7, its grammars and
the shared helper. Existing Rust/Python numerical and parity checks remain acceptance.
