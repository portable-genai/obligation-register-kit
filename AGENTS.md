# obligation-register-kit

The shared working agreement is [`.github/AGENTS.md`](https://github.com/portable-genai/.github/blob/main/AGENTS.md).
It carries the architecture rules, the gate contract, the fleet invariants, the
falsification discipline, versions and house style, and it holds in every repository
here. Read it first. This file carries only what is specific to this one.

## What this is

`obligation-register-kit` is the shared **obligation-register kernel** for the catalog's GRC
systems, packaged once: an atomic, owned, citation-bearing obligation model; a typed, reviewed
obligation to policy to control to evidence mapping graph; versioned, effective-dated register
snapshots; deadline arithmetic; and a pure coverage/gap engine. It is born in Rgc7
(`obligations-control-mapping`, the system of record) and pinned by tag from Rgc12
(`contract-obligation-extraction`), which applies the same engine to a contractual corpus.

## Commands

A venv exists at `.venv`. The core has no runtime dependencies. The only non-PyPI piece is the
test-only `agent-eval-kit`, used by the coverage falsification proof.

Clean-clone networked setup (resolves the git-pinned test dep from GitHub):

```sh
pip install -e ".[dev]"
```

Offline setup (the real gate; no GitHub credential), installing the commons from the LOCAL
SIBLING checkout exactly as the service repos do:

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv -e ../agent-eval-kit
uv pip install --python .venv 'ruff==0.15.18' 'mypy>=1.10' 'pytest>=8.2'
uv pip install --python .venv -e . --no-deps
```

The full gate, in order (all four must pass, offline):

```sh
ruff check src tests
ruff format --check src tests   # ruff pinned EXACTLY so formatting never drifts
mypy src                        # strict; src only
pytest                          # -q, testpaths=tests
```

The `agent-eval-kit` pin records both its tag and the commit that tag resolves to; a consumer
that pins THIS kit records its own tag and commit the same way.

## Hard constraints

- **The kernel is pure stdlib, zero runtime dependencies.** `dependencies = []` in pyproject is
  deliberate. No module under `src/obligation_register/` imports a framework, a cloud SDK, an
  HTTP client, or reads a clock (`datetime` is used as a VALUE type only; every deadline question
  takes an explicit `as_of`). A consuming service inherits no transitive runtime deps.
- **Consequential math is pure and deterministic.** Coverage, gaps, orphans, stale edges and
  deadline status are total functions of their inputs. The same graph always produces the same
  output, byte for byte (proven by `tests/test_golden_replay.py`).
- **Coverage counts ACCEPTED, NON-STALE edges only.** Never let a proposed or stale edge
  contribute to a coverage figure. This is the property that keeps coverage off unreviewed model
  output, and it is load-bearing for both consuming systems.
- **The register is append-only.** A correction is a new snapshot with a later effective date,
  never an edit to an old one. Effective dates are monotonic non-decreasing.
- **Python >=3.12**, mypy `strict = true`, ruff line-length 100 with `E,F,I,UP,B,SIM`.

## Architecture

Modules in `src/obligation_register/`, re-exported flat from `__init__.py` (submodules are also
exposed by name):

- **enums.py** - the closed vocabularies (`NodeKind`, `EdgeKind`, `EdgeStatus`, `Coverage`,
  `GapKind`, `DeadlineStatus`). Adding a member is a schema change.
- **provenance.py** - `Citation`, the pointer carried by every obligation and edge.
- **keys.py** - deterministic content-derived keys (`dedup_key`, `edge_id`, `normalise_text`).
- **model.py** - the value objects (`NodeRef`, `Node`, `Obligation`, `Deadline`, `Edge`) and
  the edge-endpoint table. Endpoints are validated at construction.
- **graph.py** - `ObligationGraph`: immutable, append-only, endpoint-validated, with the
  staleness sweep `mark_stale_for_moved_sources`.
- **register.py** - `Register` / `RegisterSnapshot` (versioned, effective-dated) and `admit`
  (content-key dedup).
- **coverage.py** - the pure coverage/gap engine (`compute_coverage` and friends).
- **deadlines.py** - deadline arithmetic, every call taking an explicit `as_of`.
- **schema.py** - canonical serialisation (`canonical_json`, `digest`, `envelope`) and
  `SCHEMA_VERSION`.

## Invariants

Keep behaviour identical when editing existing code; put a redesign in a separate change. The
zero-runtime-dependency core, the accepted-non-stale coverage rule, and the append-only register
are the three properties never to weaken. When the serialised shape legitimately changes, bump
`SCHEMA_VERSION`, regenerate the golden with `python -m tests.regen_golden`, and review the diff.
