"""Graph invariants: immutability, unknown-vertex refusal, staleness sweep."""

from __future__ import annotations

import pytest

from obligation_register import (
    Citation,
    Edge,
    EdgeKind,
    EdgeStatus,
    Node,
    NodeKind,
    NodeRef,
    Obligation,
    ObligationGraph,
    UnknownVertexError,
)

from .fixtures import showcase_graph


def _cit(source_id: str = "src.example") -> Citation:
    return Citation(source_id=source_id, locator="s1")


def test_add_is_append_only_and_returns_a_new_graph() -> None:
    base = ObligationGraph()
    obl = Obligation(id="o1", title="t", text="Do a thing.", citation=_cit())
    grown = base.add_obligation(obl)
    assert base.obligations == ()  # original unchanged
    assert grown.obligations == (obl,)


def test_edge_to_unknown_vertex_is_refused() -> None:
    graph = ObligationGraph(
        obligations=(Obligation(id="o1", title="t", text="Do a thing.", citation=_cit()),)
    )
    dangling = Edge(
        src=NodeRef(NodeKind.OBLIGATION, "o1"),
        dst=NodeRef(NodeKind.CONTROL, "does-not-exist"),
        kind=EdgeKind.OBLIGATION_TO_CONTROL,
    )
    with pytest.raises(UnknownVertexError):
        graph.add_edge(dangling)


def test_construction_validates_all_edges() -> None:
    with pytest.raises(UnknownVertexError):
        ObligationGraph(
            nodes=(Node(ref=NodeRef(NodeKind.CONTROL, "c1")),),
            edges=(
                Edge(
                    src=NodeRef(NodeKind.CONTROL, "c1"),
                    dst=NodeRef(NodeKind.EVIDENCE, "missing"),
                    kind=EdgeKind.CONTROL_TO_EVIDENCE,
                ),
            ),
        )


def test_canonical_ordering_makes_equal_graphs_equal() -> None:
    graph = showcase_graph()
    reversed_inputs = ObligationGraph(
        obligations=tuple(reversed(graph.obligations)),
        nodes=tuple(reversed(graph.nodes)),
        edges=tuple(reversed(graph.edges)),
    )
    assert reversed_inputs == graph  # sorted canonically on construction


def test_mark_stale_for_moved_sources_marks_only_that_obligations_edges() -> None:
    graph = showcase_graph()
    swept = graph.mark_stale_for_moved_sources({"mas-trm.example"})
    # every accepted obligation-rooted edge from a mas-trm obligation is now stale
    obligation_edges = [
        e
        for e in swept.edges
        if e.src.kind is NodeKind.OBLIGATION and e.status is EdgeStatus.ACCEPTED
    ]
    assert obligation_edges  # there is at least one
    assert all(e.stale for e in obligation_edges)
    # a shared policy-to-control edge is not touched by an obligation's source moving
    p2c = [e for e in swept.edges if e.kind is EdgeKind.POLICY_TO_CONTROL]
    assert all(not e.stale for e in p2c)
