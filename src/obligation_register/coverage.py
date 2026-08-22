"""The pure coverage and gap engine (the consequential heart of the kernel).

Every number a caller shows a regulator comes from here, and nothing here reads a model,
a clock or a network. Coverage is computed from ACCEPTED, NON-STALE edges only, so a
figure never rests on a proposal no human accepted, nor on a mapping whose source has
since moved. The functions are total and deterministic: the same graph always yields the
same report, byte for byte.

Definitions, stated once so callers do not each invent their own:

* An obligation *reaches* a control when an accepted, non-stale edge path runs from the
  obligation to the control, either directly (obligation to control) or through a policy
  (obligation to policy to control).
* A control is *evidenced* when it has an accepted, non-stale control-to-evidence edge.
* Coverage of an obligation is COVERED when it reaches at least one control and every
  reached control is evidenced; PARTIAL when it reaches a control but not all reached are
  evidenced; UNCOVERED when it reaches none.
* An *orphan control* is a control that no obligation reaches by any accepted edge
  (staleness aside): nobody ever accepted a mapping to it.
* A *stale edge* is an accepted edge flagged stale: it was a real mapping, but its source
  moved and it must be re-reviewed before it counts again.
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import Coverage, EdgeKind, EdgeStatus, GapKind, NodeKind
from .graph import ObligationGraph
from .model import Edge, NodeRef, Obligation
from .provenance import Citation

__all__ = [
    "ObligationCoverage",
    "GapFinding",
    "CoverageReport",
    "coverage_for_obligation",
    "orphan_controls",
    "stale_edges",
    "compute_coverage",
]


@dataclass(frozen=True, slots=True)
class ObligationCoverage:
    """The coverage verdict for one obligation, with the graph facts behind it."""

    obligation_id: str
    coverage: Coverage
    reached_controls: tuple[str, ...]
    evidenced_controls: tuple[str, ...]
    stale_edge_ids: tuple[str, ...]
    citations: tuple[Citation, ...]


@dataclass(frozen=True, slots=True)
class GapFinding:
    """One gap surfaced from the graph, each citing the path that produced it."""

    kind: GapKind
    subject: str  # the obligation id, control id or edge id the gap is about
    detail: str
    coverage: Coverage | None = None
    citations: tuple[Citation, ...] = ()


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """The whole-graph coverage picture: per-obligation verdicts, counts and gaps."""

    results: tuple[ObligationCoverage, ...]
    counts: tuple[tuple[str, int], ...]  # (coverage value, count), sorted for stable output
    orphan_controls: tuple[str, ...]
    stale_edges: tuple[str, ...]
    gaps: tuple[GapFinding, ...]


def _counts(edge: Edge, *, include_stale: bool) -> bool:
    """Whether an edge participates in reachability for the given staleness policy."""
    if edge.status is not EdgeStatus.ACCEPTED:
        return False
    return include_stale or not edge.stale


def _reach(
    graph: ObligationGraph, obligation_id: str, *, include_stale: bool
) -> tuple[set[str], list[Edge]]:
    """Return the control ids an obligation reaches and the edges traversed to reach them."""
    start = NodeRef(NodeKind.OBLIGATION, obligation_id)
    reached: set[str] = set()
    traversed: list[Edge] = []
    for edge in graph.outgoing.get(start, ()):  # obligation-rooted edges, in edge-id order
        if not _counts(edge, include_stale=include_stale):
            continue
        if edge.kind is EdgeKind.OBLIGATION_TO_CONTROL:
            reached.add(edge.dst.id)
            traversed.append(edge)
        elif edge.kind is EdgeKind.OBLIGATION_TO_POLICY:
            traversed.append(edge)
            for onward in graph.outgoing.get(edge.dst, ()):
                if onward.kind is EdgeKind.POLICY_TO_CONTROL and _counts(
                    onward, include_stale=include_stale
                ):
                    reached.add(onward.dst.id)
                    traversed.append(onward)
    return reached, traversed


def _is_evidenced(graph: ObligationGraph, control_id: str) -> bool:
    control = NodeRef(NodeKind.CONTROL, control_id)
    return any(
        edge.kind is EdgeKind.CONTROL_TO_EVIDENCE and _counts(edge, include_stale=False)
        for edge in graph.outgoing.get(control, ())
    )


def _stale_from_obligation(graph: ObligationGraph, obligation_id: str) -> tuple[str, ...]:
    start = NodeRef(NodeKind.OBLIGATION, obligation_id)
    return tuple(
        sorted(
            edge.id
            for edge in graph.outgoing.get(start, ())
            if edge.status is EdgeStatus.ACCEPTED and edge.stale
        )
    )


def coverage_for_obligation(graph: ObligationGraph, obligation: Obligation) -> ObligationCoverage:
    """Compute the coverage verdict for a single obligation (pure)."""
    reached, traversed = _reach(graph, obligation.id, include_stale=False)
    evidenced = {cid for cid in reached if _is_evidenced(graph, cid)}

    if not reached:
        coverage = Coverage.UNCOVERED
    elif evidenced == reached:
        coverage = Coverage.COVERED
    else:
        coverage = Coverage.PARTIAL

    citations: list[Citation] = [obligation.citation]
    for edge in traversed:
        citations.extend(edge.citations)

    return ObligationCoverage(
        obligation_id=obligation.id,
        coverage=coverage,
        reached_controls=tuple(sorted(reached)),
        evidenced_controls=tuple(sorted(evidenced)),
        stale_edge_ids=_stale_from_obligation(graph, obligation.id),
        citations=_dedupe_citations(citations),
    )


def orphan_controls(graph: ObligationGraph) -> tuple[str, ...]:
    """Return the control ids no obligation reaches by any accepted edge (staleness aside)."""
    reached_any: set[str] = set()
    for obligation in graph.obligations:
        reached, _ = _reach(graph, obligation.id, include_stale=True)
        reached_any |= reached
    all_controls = {node.ref.id for node in graph.controls()}
    return tuple(sorted(all_controls - reached_any))


def stale_edges(graph: ObligationGraph) -> tuple[str, ...]:
    """Return the ids of accepted edges flagged stale, in canonical order."""
    return tuple(
        sorted(edge.id for edge in graph.edges if edge.status is EdgeStatus.ACCEPTED and edge.stale)
    )


def compute_coverage(graph: ObligationGraph) -> CoverageReport:
    """Compute the whole-graph coverage report: verdicts, counts, orphans, stale, gaps."""
    results = tuple(coverage_for_obligation(graph, obligation) for obligation in graph.obligations)

    tally: dict[str, int] = {c.value: 0 for c in Coverage}
    for result in results:
        tally[result.coverage.value] += 1
    counts = tuple(sorted(tally.items()))

    orphans = orphan_controls(graph)
    stale = stale_edges(graph)
    gaps = _gaps(graph, results, orphans, stale)

    return CoverageReport(
        results=results,
        counts=counts,
        orphan_controls=orphans,
        stale_edges=stale,
        gaps=gaps,
    )


def _gaps(
    graph: ObligationGraph,
    results: tuple[ObligationCoverage, ...],
    orphans: tuple[str, ...],
    stale: tuple[str, ...],
) -> tuple[GapFinding, ...]:
    findings: list[GapFinding] = []
    for result in results:
        if result.coverage is Coverage.UNCOVERED:
            findings.append(
                GapFinding(
                    kind=GapKind.UNCOVERED_OBLIGATION,
                    subject=result.obligation_id,
                    detail="obligation reaches no accepted, current control mapping",
                    coverage=result.coverage,
                    citations=result.citations,
                )
            )
        elif result.coverage is Coverage.PARTIAL:
            missing = tuple(
                c for c in result.reached_controls if c not in result.evidenced_controls
            )
            findings.append(
                GapFinding(
                    kind=GapKind.PARTIAL_OBLIGATION,
                    subject=result.obligation_id,
                    detail=f"reached controls without evidence: {', '.join(missing) or 'none'}",
                    coverage=result.coverage,
                    citations=result.citations,
                )
            )
    for control_id in orphans:
        findings.append(
            GapFinding(
                kind=GapKind.ORPHAN_CONTROL,
                subject=control_id,
                detail="control has no accepted mapping from any obligation",
                citations=_control_citations(graph, control_id),
            )
        )
    for edge_id in stale:
        edge = graph.edge_by_id[edge_id]
        findings.append(
            GapFinding(
                kind=GapKind.STALE_EDGE,
                subject=edge_id,
                detail=f"accepted {edge.kind.value} edge is stale and must be re-reviewed",
                citations=edge.citations,
            )
        )
    return tuple(findings)


def _control_citations(graph: ObligationGraph, control_id: str) -> tuple[Citation, ...]:
    node = graph.node_by_ref.get(NodeRef(NodeKind.CONTROL, control_id))
    return node.citations if node is not None else ()


def _dedupe_citations(citations: list[Citation]) -> tuple[Citation, ...]:
    """De-duplicate while preserving deterministic order (sorted)."""
    return tuple(sorted(set(citations)))
