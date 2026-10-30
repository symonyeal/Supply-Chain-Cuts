# Module ownership and redundancy review

The 2026-10-30 review covered the complete tracked tree at `4ac63a1`: 1,175 files.
Every handwritten source file was reviewed, including callers, tests and command
entry points. Frozen material was classified by its provenance and hashed. No
first-party source file was left outside the review.

| Baseline category | Files | Disposition |
| --- | ---: | --- |
| Live handwritten Python, Rust and browser code | 89 | Reviewed; repeated decisions consolidated below |
| Vendored HiGHS | 527 | Preserved; count, bytes and complete tree digest match `UPSTREAM.json` |
| Frozen inputs, transcriptions and source metadata | 70 | Preserved byte for byte |
| Result bundles, independent comparison inputs and project history | 439 | Preserved byte for byte; historical scripts retain their original dependencies |
| Generated site payloads and context CSV | 3 | Preserved byte for byte; verified through their builders |
| Documentation, manifests, workflows, attribution and assets | 47 | Reviewed or classified by role; distinct responsibilities retained |

The working evidence contains a path-by-path CSV with before/after SHA-256 values,
the independent tracked-file inventory, source-review records, duplicate-block
search results and verification logs. It is not a second source of project code.

## Owners

| Decision hidden by the module | Owner | Callers |
| --- | --- | --- |
| Country ordering, probability validation, common-shock rates and conditional node rates | Private `cut-risk::law::Law` | Exact union, count bracket and seeded sampling |
| Manifest snapshot, source hash verification, CSV decoding | Private `sc-data::Sources` | Network/BOM construction, context construction and source verification |
| Historical cut-to-certificate coordinate join | Private `sc-site::CutBundle` | Reference and chemistry payload builders; each task is read/joined once |
| Sweep grid, sparse state representation and primal/dual/predecessor certification | `chokepoint.sweep` | Cut, chemistry, capacity and risk runners; comparison tools |
| Seeded latent-state draw order | Private `chokepoint.risk._sample_states` | Residual, partial-loss and importance sampling |
| Theme preference and storage fallback | `site/theme.js` | Overview and explorer, through their script declarations |
| Display names and capacity-scenario labels | `site/names.js` | Overview, explorer and research tables |

Sampling no longer calculates an exact cut union merely to validate a law. Bracket
attribution reuses the prepared law instead of cloning and preparing every input.
Native source readers parse one manifest per operation. Network construction uses
one rule for the CAM/AAM production-or-BOM choice, and context export uses one CSV
writer loop. The Python runners share one enumerate/convert/certify operation and
no longer import implementation helpers from other runner scripts. The unused
browser `notice` state and `.delta` selector were removed.

The native recourse model, lattice search and static server already hide their
respective mathematics and protocol decisions behind small interfaces; review
did not justify splitting them into additional modules. No dependency was added.

## Repetition retained for a reason

- Python and Rust remain independent transcriptions. MILP, lattice and exhaustive
  algorithms retain their independent acceptance roles. Sharing their mathematical
  implementation would weaken the certificates described in [MODEL](MODEL.md).
- Historical run bundles contain copies of their inputs and predecessor results.
  They are immutable evidence, not competing live implementations. Removing their
  repeated bytes would break the published reproduction paths and provenance.
- The solver is a pinned upstream source tree. Its implementation is not rewritten
  as part of application cleanup; its recorded tree hash remains unchanged.
- Comparison tools retain different contracts: exact source values, typed JSON
  structure and float bits, keyed probabilities, or LP tolerance and status checks.
  A shared configurable comparator would conceal those differences.
- Small command boundaries retain their local protocol/error handling; they do
  not warrant a new shared I/O crate. Page-specific percentage formats retain
  their different missing-value and precision meanings.

## Verification

The verification commands are defined once in [the work contract](../CLAUDE.md).
The review additionally runs the complete native data, model, site, probability
and pipeline comparisons, seeded Python before/after checks, full sweep-grid
comparison, and browser checks. Numerical equivalence remains scoped to the
inputs actually compared, as described in [VALIDATION](VALIDATION.md).
