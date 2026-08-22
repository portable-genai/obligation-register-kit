"""Canonical serialisation: determinism, enum/date encoding, versioned envelope."""

from __future__ import annotations

from datetime import date

from obligation_register import (
    SCHEMA_VERSION,
    Citation,
    Coverage,
    NodeKind,
    NodeRef,
    canonical_json,
    compute_coverage,
    digest,
    envelope,
    to_jsonable,
)

from .fixtures import showcase_graph


def test_enums_encode_as_their_values() -> None:
    assert to_jsonable(Coverage.PARTIAL) == "partial"
    assert to_jsonable(NodeKind.CONTROL) == "control"


def test_dates_encode_as_iso_strings() -> None:
    assert to_jsonable(date(2026, 3, 31)) == "2026-03-31"


def test_noderef_encodes_as_kind_and_id() -> None:
    assert to_jsonable(NodeRef(NodeKind.CONTROL, "c1")) == {"kind": "control", "id": "c1"}


def test_canonical_json_is_stable_across_calls() -> None:
    report = compute_coverage(showcase_graph())
    assert canonical_json(report) == canonical_json(report)


def test_digest_changes_when_content_changes() -> None:
    base = compute_coverage(showcase_graph())
    a = Citation(source_id="a.example", locator="s1")
    b = Citation(source_id="b.example", locator="s1")
    assert digest(a) != digest(b)
    assert digest(base) == digest(compute_coverage(showcase_graph()))


def test_envelope_carries_the_schema_version() -> None:
    env = envelope("coverage_report", compute_coverage(showcase_graph()))
    assert env["schema_version"] == SCHEMA_VERSION
    assert env["kind"] == "coverage_report"
    assert "payload" in env
