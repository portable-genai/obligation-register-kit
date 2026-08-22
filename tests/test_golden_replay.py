"""The byte-identical golden replay: the determinism proof for the coverage output.

Two assertions. The first proves the output is stable ACROSS RUNS in one process. The
second proves it is stable across the build/commit boundary by comparing against a golden
committed to the tree. If a change legitimately alters the serialised shape, regenerate the
golden with ``python -m tests.regen_golden`` and review the diff.
"""

from __future__ import annotations

from pathlib import Path

from obligation_register import canonical_json, compute_coverage

from .fixtures import showcase_graph

_GOLDEN = Path(__file__).parent / "golden" / "showcase_coverage.json"


def test_replay_is_byte_identical_across_runs() -> None:
    first = canonical_json(compute_coverage(showcase_graph()))
    second = canonical_json(compute_coverage(showcase_graph()))
    assert first == second


def test_output_matches_the_committed_golden() -> None:
    produced = canonical_json(compute_coverage(showcase_graph()))
    assert _GOLDEN.exists(), "golden missing; run: python -m tests.regen_golden"
    assert produced == _GOLDEN.read_text(encoding="utf-8")
