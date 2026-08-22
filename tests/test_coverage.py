"""Coverage engine correctness against the showcase graph."""

from __future__ import annotations

from obligation_register import (
    Coverage,
    GapKind,
    compute_coverage,
)

from .fixtures import showcase_graph


def _by_id(report):
    return {r.obligation_id: r for r in report.results}


def test_coverage_bands_are_computed_from_accepted_non_stale_edges() -> None:
    report = compute_coverage(showcase_graph())
    bands = {oid: r.coverage for oid, r in _by_id(report).items()}
    assert bands == {
        "reg-covered": Coverage.COVERED,
        "reg-partial": Coverage.PARTIAL,
        "reg-uncovered": Coverage.UNCOVERED,
        "reg-stale": Coverage.UNCOVERED,  # its only mapping is stale, so it counts for nothing
    }


def test_counts_are_zero_filled_and_sorted() -> None:
    report = compute_coverage(showcase_graph())
    assert dict(report.counts) == {"covered": 1, "partial": 1, "uncovered": 2}


def test_partial_obligation_reaches_but_does_not_evidence_all_controls() -> None:
    result = _by_id(compute_coverage(showcase_graph()))["reg-partial"]
    assert result.reached_controls == ("ctrl-encryption", "ctrl-kms")
    assert result.evidenced_controls == ("ctrl-encryption",)


def test_proposed_edge_never_contributes_to_coverage() -> None:
    result = _by_id(compute_coverage(showcase_graph()))["reg-uncovered"]
    assert result.reached_controls == ()
    assert result.coverage is Coverage.UNCOVERED


def test_orphan_control_is_one_reached_by_no_obligation() -> None:
    report = compute_coverage(showcase_graph())
    # ctrl-worm is reached only by a STALE edge, but staleness aside it IS mapped, so it is
    # not an orphan; only ctrl-orphan has no mapping at all.
    assert report.orphan_controls == ("ctrl-orphan",)


def test_stale_edge_is_surfaced_and_drops_its_obligation() -> None:
    report = compute_coverage(showcase_graph())
    assert len(report.stale_edges) == 1
    stale_result = _by_id(report)["reg-stale"]
    assert stale_result.stale_edge_ids == report.stale_edges
    assert stale_result.coverage is Coverage.UNCOVERED


def test_gaps_cover_every_uncovered_partial_orphan_and_stale() -> None:
    report = compute_coverage(showcase_graph())
    kinds = sorted({(g.kind, g.subject) for g in report.gaps})
    assert (GapKind.UNCOVERED_OBLIGATION, "reg-uncovered") in kinds
    assert (GapKind.UNCOVERED_OBLIGATION, "reg-stale") in kinds
    assert (GapKind.PARTIAL_OBLIGATION, "reg-partial") in kinds
    assert (GapKind.ORPHAN_CONTROL, "ctrl-orphan") in kinds
    assert any(g.kind is GapKind.STALE_EDGE for g in report.gaps)


def test_every_finding_carries_at_least_one_citation() -> None:
    report = compute_coverage(showcase_graph())
    for result in report.results:
        assert result.citations, f"{result.obligation_id} has no citation"
    for gap in report.gaps:
        if gap.kind in (GapKind.UNCOVERED_OBLIGATION, GapKind.PARTIAL_OBLIGATION):
            assert gap.citations, f"gap {gap.subject} has no citation"


def test_covered_obligation_cites_its_source_and_edge_path() -> None:
    result = _by_id(compute_coverage(showcase_graph()))["reg-covered"]
    source_ids = {c.source_id for c in result.citations}
    # the obligation's own source plus the accepted mapping edge's rationale citation
    assert "mas-trm.example" in source_ids
    assert "map-reg-covered-pol-cloud" in source_ids
