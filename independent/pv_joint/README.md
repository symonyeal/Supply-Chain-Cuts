These independent scripts reproduce the original fixed 50% LFP/50% NCM622 PV and joint calculation from the frozen input tree. They import no project modules and read no production code, tests, analysis or project results. The named cut lists are bundled comparison inputs; exhaustive enumeration constructs its own states.

Use system Python 3.14 with numpy, scipy, openpyxl and pypdf installed. Run these PowerShell commands from this directory. Set `--root` to the frozen input tree and `--out` to a separate output directory; the cut paths are explicit. These are the commands tested in this workspace:

```powershell
$inputRoot = '..\..'    # the repository root
$outputDir = '..\portable-test'
py -3.14 .\recompute.py --root $inputRoot --out $outputDir --pv-cuts '.\inputs\pv-cuts.json' --joint-cuts '.\inputs\joint-cuts.json'
py -3.14 .\trace_sources.py --root $inputRoot --out $outputDir
```

The input tree must retain its permitted `data/raw`, `data/events`, `SOURCES.lock`, `CLAUDE.md` and four referenced documentation files. Raw source files are not bundled here. The programs write only beneath `--out`; neither requires the original scratch directory. Both expose `--help`.

The fresh-directory test reproduced 22 PV cuts and 180 joint cuts through support three. PV L is `0.2444939846405121`; joint L is `0.20382804118895667`. All sector certificates, rates, events and source-audit outputs exactly match the accepted audit. All 1521 coverage rows match the independently extracted frozen PDF. The preserved HHI reporting correction uses all origins; capacity and headline outputs are unchanged. This correction predates the portability patch.

`results.json` contains numerical outcomes, certificates and input hashes. `source_trace.json` contains document excerpts, source hashes and coverage comparisons. `coverage_from_pdf.csv` is the independent exposure transcription. The output also includes the network, reconstructed events, node-years and exhaustive enumeration summary. This package runs the existing calculations; it adds no scientific analysis.

| Code | Original SHA-256 | Portable SHA-256 |
| --- | --- | --- |
| recompute.py | `29092b322abc6ed6a83f29791941c8affad0f1955821aa9fd82de6efe2998083` | `1dabd1a6e44dc7904229a77b302e8adb833c97abc63612e1183ef9173dd7ca42` |
| trace_sources.py | `1c92ee50e897556a93b79114b7da48c3e7ea7ed7838af24e9a687d749fc9b456` | `114b8440f3db57970c0a7dbd410eef530ffb28e574ca6d46f3b3b0b31f3128b6` |

`package-manifest.json` records code/input hashes, dependency versions, reproduction comparisons and the immutable accepted-artifact hashes. `portability.patch` shows the complete changes: explicit path arguments, output-directory creation and cut-path selection. The two original scripts, accepted `results.json` and original audit report remain byte-identical.

The independence limits remain: the scripts share the written mathematical specification and curated product/act annotations; MIIT and Fraunhofer numerical CSVs were not re-transcribed from original publications. Raw OECD events and coverage were independently checked. National-act dates and legal scope were checked against frozen documents; legal completeness, product mapping, censoring and whole-node outage severity remain assumptions. Enumeration is through support three at tolerance 1e-9 for the stated fixed-mix instance. L is a model-conditional cut-union probability, not an estimate of the total real-world failure probability.

Repository integration applies only line wrapping and formatting; AST equality with both portable originals was checked. Repository hashes are recorded separately in package-manifest.json; the original audit and portable hashes remain preserved. Source-excerpt outputs with unverified reuse terms must remain local.
