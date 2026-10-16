# Working contract

Read before changing anything. [README](README.md) states what the models are;
[Decisions](docs/DECISIONS.md) states why they are that way; [Validation](docs/VALIDATION.md)
states what must be, and has been, checked. This file states the rules a change must
not break. Codex reads the same file through [AGENTS.md](AGENTS.md).

## Always on

| Rule | Reason |
| --- | --- |
| Report no outcome that was not read back from the result that produced it. | A requested tolerance is not a result. |
| Name a failed run by its status, never by its cause until the cause is shown. | Malformed data and a genuine infeasibility end the same way. |
| Cite only what [Sources](docs/SOURCES.md) records, and add the entry in the change that uses it. | A method is validated by the source it implements, not by the code that ran it. |
| Add a dependency only after measurement. Use the system Python 3.14; no virtual environment. | numpy and scipy come first. |
| State what was measured and what was not. | "Not measured" is a finding. A projection is not a measurement. |
| The [design](docs/specs/2026-10-15-chokepoint-design.md) is canonical; change it before the code departs from it. | It records decisions agreed with the user; code that drifts silently loses them. |
| Every node capacity carries its basis: `production`, `trade` or `imputed`. | Trade-based capacity understates integrated producers; a claim must say which basis it rests on. |
| Every raw input is frozen in `data/raw/` with URL, date, SHA-256 and licence in `SOURCES.lock`; fetchers verify the hash. | Results must be reproducible from the exact bytes that produced them. |
| Do not commit raw BGS data until BGS confirms the licence. | Two BGS pages state conflicting licences ([Research](docs/RESEARCH.md) §12). |
| Commit `docs/HYPOTHESES.md` before any probability result exists. | Kill conditions written after the result are not tests. |
| Never fill a data gap from memory; label it `unverified`. | The evidence base is primary sources only. |

## The model is written once

The recourse LP φ(z) lives in `chokepoint/recourse.py`. The interdiction MILP in
`chokepoint/cuts.py` is built from the dual of the same matrices, never from a second
transcription. `chokepoint/brute.py` is the independent check: it enumerates disruptions
and calls φ directly, and shares no code with `cuts.py`. Agreement of the two cut-set
lists is the certificate; a shared helper would destroy it.

## Code

Code transcribes the mathematics: symbol names from the documents, the problem stated in
each public docstring, loops whose condition is the stopping rule, comments that cite the
source. Mathematical outcomes are return values, not exceptions.

## Agent skills

### Issue tracker

GitHub Issues on `symonyeal/Chokepoint-Lab`, via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default roles, each label equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the root, created when needed. See
`docs/agents/domain.md`.

## Before a change is finished

```text
python -m pytest -q
python -m ruff check .
python -m pip check
```

A behavioural change states its effect in numbers, with the instance and revision.
Committed result bundles carry the revision that produced them.
