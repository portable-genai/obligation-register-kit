# obligation-register-kit

The shared **obligation-register kernel** for the catalog's governance, risk and compliance
systems. It is the engine that decomposes a source into atomic, owned obligations, maps each
across a typed obligation to policy to control to evidence graph, versions the register over
time, and computes coverage and gaps deterministically. It is born in the obligations system
of record (Rgc7) and pinned by tag from the contractual obligation extractor (Rgc12), so both
systems reason over one register model rather than two that drift.

The kernel is **pure standard library**: no clock, no I/O, no framework, no cloud SDK. Every
consequential number (coverage bands, orphan controls, stale edges, deadline status) is a
total, deterministic function of its inputs, so a result replays byte for byte and a consuming
service inherits zero transitive runtime dependencies.

## Why a kit and not a copy

Two systems admit obligations from different corpora, the regulatory corpus and the contractual
corpus, into the same shape of register. Building the engine once and pinning it by version is
what lets the catalog claim the obligation register is one engine applied twice, not two engines
that happen to agree today. Coverage and gap logic in particular must be identical: a coverage
figure computed one way for regulations and another way for contracts would be indefensible in
front of an auditor.

## What it provides

| Area | Types and functions |
|---|---|
| Provenance | `Citation` on every obligation and every edge |
| Obligation model | `Obligation` (atomic, owned, effective-dated, deadline-bearing, content-keyed), `Node`, `NodeRef`, `Edge`, `Deadline` |
| Vocabulary | `NodeKind`, `EdgeKind`, `EdgeStatus`, `Coverage`, `GapKind`, `DeadlineStatus` |
| Graph | `ObligationGraph`: immutable, append-only, endpoint-validated |
| Register | `Register` / `RegisterSnapshot`: versioned, effective-dated snapshots; `admit` for content-key dedup |
| Coverage engine | `compute_coverage`, `coverage_for_obligation`, `orphan_controls`, `stale_edges` |
| Deadlines | `deadline_status`, `days_until`, `due_entries`, `approaching` (every call takes an explicit `as_of`) |
| Serialisation | `canonical_json`, `digest`, `envelope`, `to_jsonable`, `SCHEMA_VERSION` |

## The rules the kernel enforces

- **Coverage rests on accepted, current mappings only.** An edge contributes to a coverage
  figure only when it is `ACCEPTED` and not `stale`. A model proposal nobody reviewed, or a
  mapping whose source has since moved, counts for nothing until a human accepts or re-accepts
  it. This is what keeps coverage from resting on unreviewed output.
- **Nothing consequential exists without a source.** An `Obligation` requires a `Citation`;
  an accepted `Edge` carries its own citations; every coverage and gap finding quotes the
  citations behind it, so any figure traces back to a clause without rerunning the engine.
- **History is append-only.** A `Register` corrects itself by appending a new snapshot with a
  later effective date, never by editing an old one, so `as_of(date)` always answers with the
  generation that was in force.
- **The kernel never reads a clock.** Deadline questions take an explicit `as_of`, so a status
  is a pure function of the deadline and the reference date and replays identically.

## Coverage, precisely

An obligation *reaches* a control when an accepted, non-stale path runs from it to the control,
either directly or through a policy. A control is *evidenced* when it has an accepted, non-stale
control-to-evidence edge. Then:

- `COVERED`: reaches at least one control and every reached control is evidenced.
- `PARTIAL`: reaches a control but not all reached controls are evidenced.
- `UNCOVERED`: reaches no control via an accepted, non-stale edge.

An *orphan control* is a control no obligation reaches by any accepted edge (staleness aside): a
control nobody ever justified. A *stale edge* is an accepted edge flagged stale: a real mapping
whose source moved, held out of coverage until it is re-reviewed.

## Install

```sh
pip install -e ".[dev]"   # core + ruff (pinned) + mypy + pytest + the falsification harness
```

The core has no runtime dependencies. The `dev` extra pins `agent-eval-kit` (test only) by tag
for the not-falsely-green coverage proof. The offline gate installs that from a local sibling
checkout rather than GitHub; see `AGENTS.md`.

## Gate

```sh
ruff check src tests
ruff format --check src tests
mypy src
pytest
```

The suite carries its own proofs: a byte-identical golden replay of the coverage output
(`tests/test_golden_replay.py`) and a per-segment falsification that the coverage metric can go
red (`tests/test_coverage_falsification.py`).

## Versioning

Semantic version in `pyproject.toml` and `obligation_register.__version__`; the serialised wire
shape carries its own `SCHEMA_VERSION`. Consumers pin this kit by tag in `pyproject.toml` and by
commit in their lockfiles. All example identifiers in this repository are obviously fictional.
