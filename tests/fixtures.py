"""Shared, obviously fictional fixtures for the kernel tests.

Two builders:

* :func:`showcase_graph` is the rich graph that exercises every coverage band, an orphan
  control and a stale edge at once. It backs the correctness tests and the byte-identical
  golden replay.
* :func:`covered_graph` / :func:`degrade` back the not-falsely-green falsification: a fully
  covered graph scores 1.0 on the coverage metric, and dropping one evidence edge must pull
  it below the bar, proving the metric can go red.

All identifiers are fictional (``.example`` sources, invented control slugs).
"""

from __future__ import annotations

from datetime import date

from obligation_register import (
    Citation,
    Deadline,
    Edge,
    EdgeKind,
    EdgeStatus,
    Node,
    NodeKind,
    NodeRef,
    Obligation,
    ObligationGraph,
)


def _cit(source_id: str, locator: str, title: str = "") -> Citation:
    return Citation(
        source_id=source_id,
        locator=locator,
        title=title or f"{source_id} {locator}",
        url=f"https://sources.example/{source_id}#{locator}",
    )


def _control(slug: str, title: str) -> Node:
    return Node(ref=NodeRef(NodeKind.CONTROL, slug), title=title, citations=(_cit(slug, "spec"),))


def _policy(slug: str, title: str) -> Node:
    return Node(ref=NodeRef(NodeKind.POLICY, slug), title=title)


def _evidence(slug: str, title: str) -> Node:
    return Node(ref=NodeRef(NodeKind.EVIDENCE, slug), title=title)


def _o2p(
    obl: str, pol: str, *, status: EdgeStatus = EdgeStatus.ACCEPTED, stale: bool = False
) -> Edge:
    return Edge(
        src=NodeRef(NodeKind.OBLIGATION, obl),
        dst=NodeRef(NodeKind.POLICY, pol),
        kind=EdgeKind.OBLIGATION_TO_POLICY,
        status=status,
        stale=stale,
        citations=(_cit(f"map-{obl}-{pol}", "rationale"),),
    )


def _o2c(
    obl: str, ctrl: str, *, status: EdgeStatus = EdgeStatus.ACCEPTED, stale: bool = False
) -> Edge:
    return Edge(
        src=NodeRef(NodeKind.OBLIGATION, obl),
        dst=NodeRef(NodeKind.CONTROL, ctrl),
        kind=EdgeKind.OBLIGATION_TO_CONTROL,
        status=status,
        stale=stale,
        citations=(_cit(f"map-{obl}-{ctrl}", "rationale"),),
    )


def _p2c(
    pol: str, ctrl: str, *, status: EdgeStatus = EdgeStatus.ACCEPTED, stale: bool = False
) -> Edge:
    return Edge(
        src=NodeRef(NodeKind.POLICY, pol),
        dst=NodeRef(NodeKind.CONTROL, ctrl),
        kind=EdgeKind.POLICY_TO_CONTROL,
        status=status,
        stale=stale,
    )


def _c2e(
    ctrl: str, ev: str, *, status: EdgeStatus = EdgeStatus.ACCEPTED, stale: bool = False
) -> Edge:
    return Edge(
        src=NodeRef(NodeKind.CONTROL, ctrl),
        dst=NodeRef(NodeKind.EVIDENCE, ev),
        kind=EdgeKind.CONTROL_TO_EVIDENCE,
        status=status,
        stale=stale,
    )


def _obl(
    obl_id: str,
    text: str,
    source_id: str,
    locator: str,
    owner: str,
    deadline: Deadline | None = None,
) -> Obligation:
    return Obligation(
        id=obl_id,
        title=text[:40],
        text=text,
        owner=owner,
        citation=_cit(source_id, locator),
        effective_from=date(2026, 1, 1),
        deadline=deadline,
    )


def showcase_graph() -> ObligationGraph:
    """A graph with a COVERED, a PARTIAL, two UNCOVERED (one stale), an orphan control."""
    obligations = [
        _obl(
            "reg-covered",
            "Maintain data residency in country for customer records.",
            "mas-trm.example",
            "s3.1",
            "cloud-controls-office",
        ),
        _obl(
            "reg-partial",
            "Encrypt customer data at rest and in transit.",
            "mas-trm.example",
            "s4.2",
            "ciso-office",
        ),
        _obl(
            "reg-uncovered",
            "Notify the regulator within one hour of a material incident.",
            "mas-trm.example",
            "s6.1",
            "operational-resilience-office",
        ),
        _obl(
            "reg-stale",
            "Retain audit logs for seven years in immutable storage.",
            "mas-trm.example",
            "s8.4",
            "ciso-office",
            deadline=Deadline(due_on=date(2026, 3, 31), kind="attestation"),
        ),
    ]
    nodes = [
        _policy("pol-cloud", "Cloud Controls Policy"),
        _control("ctrl-residency", "Resource-location org policy"),
        _control("ctrl-encryption", "CMEK on customer data stores"),
        _control("ctrl-kms", "Key management service configuration"),
        _control("ctrl-worm", "WORM log bucket with retention lock"),
        _control("ctrl-orphan", "Legacy control nobody maps to"),
        _evidence("ev-scc-residency", "Security Command Center residency finding"),
        _evidence("ev-scc-encryption", "Security Command Center CMEK finding"),
        _evidence("ev-worm-attestation", "WORM retention attestation"),
    ]
    edges = [
        # reg-covered: obligation -> policy -> control -> evidence (all accepted, current)
        _o2p("reg-covered", "pol-cloud"),
        _p2c("pol-cloud", "ctrl-residency"),
        _c2e("ctrl-residency", "ev-scc-residency"),
        # reg-partial: two direct controls, only one evidenced
        _o2c("reg-partial", "ctrl-encryption"),
        _c2e("ctrl-encryption", "ev-scc-encryption"),
        _o2c("reg-partial", "ctrl-kms"),  # ctrl-kms has no evidence edge
        # reg-uncovered: only a PROPOSED mapping (never accepted)
        _o2c("reg-uncovered", "ctrl-residency", status=EdgeStatus.PROPOSED),
        # reg-stale: accepted mapping but marked stale; the control is itself evidenced
        _o2c("reg-stale", "ctrl-worm", stale=True),
        _c2e("ctrl-worm", "ev-worm-attestation"),
        # ctrl-orphan has no incoming mapping at all
    ]
    return ObligationGraph(obligations=tuple(obligations), nodes=tuple(nodes), edges=tuple(edges))


def covered_graph(prefix: str, source_id: str) -> ObligationGraph:
    """A fully COVERED two-obligation graph for one falsification segment."""
    obligations = (
        _obl(
            f"{prefix}-a",
            "First fully covered obligation for the segment.",
            source_id,
            "c1",
            "owner-a",
        ),
        _obl(
            f"{prefix}-b",
            "Second fully covered obligation for the segment.",
            source_id,
            "c2",
            "owner-b",
        ),
    )
    nodes = (
        _policy(f"{prefix}-pol", "Segment policy"),
        _control(f"{prefix}-ctrl-1", "Segment control one"),
        _control(f"{prefix}-ctrl-2", "Segment control two"),
        _evidence(f"{prefix}-ev-1", "Segment evidence one"),
        _evidence(f"{prefix}-ev-2", "Segment evidence two"),
    )
    edges = (
        _o2c(f"{prefix}-a", f"{prefix}-ctrl-1"),
        _c2e(f"{prefix}-ctrl-1", f"{prefix}-ev-1"),
        _o2p(f"{prefix}-b", f"{prefix}-pol"),
        _p2c(f"{prefix}-pol", f"{prefix}-ctrl-2"),
        _c2e(f"{prefix}-ctrl-2", f"{prefix}-ev-2"),
    )
    return ObligationGraph(obligations=obligations, nodes=nodes, edges=edges)


def degrade(graph: ObligationGraph, prefix: str) -> ObligationGraph:
    """Reject one evidence edge so a COVERED obligation drops to PARTIAL (the red case)."""
    target = f"{prefix}-ctrl-1"

    def drop(edge: Edge) -> Edge:
        if edge.kind is EdgeKind.CONTROL_TO_EVIDENCE and edge.src.id == target:
            return edge.rejected()
        return edge

    return graph.map_edges(drop)
