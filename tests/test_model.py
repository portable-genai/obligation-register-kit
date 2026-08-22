"""Value-object invariants: endpoint typing, dedup keys, required provenance."""

from __future__ import annotations

import pytest

from obligation_register import (
    Citation,
    Edge,
    EdgeKind,
    NodeKind,
    NodeRef,
    Obligation,
)


def _cit() -> Citation:
    return Citation(source_id="src.example", locator="s1")


def test_obligation_requires_text_and_citation() -> None:
    with pytest.raises(ValueError):
        Obligation(id="o1", title="t", text="   ", citation=_cit())


def test_obligation_derives_a_dedup_key_from_text_and_owner() -> None:
    a = Obligation(id="o1", title="t", text="Encrypt data at rest.", owner="ciso", citation=_cit())
    b = Obligation(
        id="o2", title="t", text="encrypt   data   at rest.", owner="ciso", citation=_cit()
    )
    c = Obligation(id="o3", title="t", text="Encrypt data at rest.", owner="dpo", citation=_cit())
    assert a.key == b.key  # whitespace and case normalised
    assert a.key != c.key  # a different owner is a different register identity


def test_citation_rejects_an_empty_source_id() -> None:
    with pytest.raises(ValueError):
        Citation(source_id="  ")


def test_edge_endpoints_must_match_the_relation() -> None:
    obl = NodeRef(NodeKind.OBLIGATION, "o1")
    ev = NodeRef(NodeKind.EVIDENCE, "e1")
    with pytest.raises(ValueError):
        Edge(src=obl, dst=ev, kind=EdgeKind.OBLIGATION_TO_CONTROL)


def test_edge_id_is_content_derived_and_idempotent() -> None:
    obl = NodeRef(NodeKind.OBLIGATION, "o1")
    ctrl = NodeRef(NodeKind.CONTROL, "c1")
    a = Edge(src=obl, dst=ctrl, kind=EdgeKind.OBLIGATION_TO_CONTROL)
    b = Edge(src=obl, dst=ctrl, kind=EdgeKind.OBLIGATION_TO_CONTROL, note="a later proposal")
    assert a.id == b.id  # same endpoints and relation collapse to one id


def test_counts_for_coverage_requires_accepted_and_not_stale() -> None:
    obl = NodeRef(NodeKind.OBLIGATION, "o1")
    ctrl = NodeRef(NodeKind.CONTROL, "c1")
    edge = Edge(src=obl, dst=ctrl, kind=EdgeKind.OBLIGATION_TO_CONTROL)
    assert not edge.counts_for_coverage  # proposed
    assert edge.accepted().counts_for_coverage
    assert not edge.accepted().with_stale(True).counts_for_coverage
