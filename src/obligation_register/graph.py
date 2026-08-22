"""The obligation graph: an immutable, append-only, deterministic vertex/edge store.

The graph is the shape the coverage engine reasons over. It is immutable by construction:
every mutator returns a NEW graph with the change applied and the contents re-sorted into
a canonical order, so two graphs built from the same facts are equal and serialise
byte-for-byte the same. It validates as it builds: an edge to a vertex the graph does not
contain is refused, which is how "a write-back naming an unknown control id is rejected"
is enforced at the kernel rather than in each caller.

Pure stdlib, no clock, no I/O.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from functools import cached_property

from .enums import NodeKind
from .model import Edge, Node, NodeRef, Obligation

__all__ = ["ObligationGraph", "UnknownVertexError", "DuplicateVertexError"]


class UnknownVertexError(ValueError):
    """Raised when an edge names a vertex the graph does not contain."""


class DuplicateVertexError(ValueError):
    """Raised when an obligation id or node ref is added twice with different content."""


@dataclass(frozen=True)
class ObligationGraph:
    """An immutable obligation to policy to control to evidence graph.

    Construct empty and build up with the ``add_*`` / ``with_*`` mutators, each of which
    returns a new graph. Endpoints are validated on every edge, and contents are held in
    a canonical sort order so equality and serialisation are stable.
    """

    obligations: tuple[Obligation, ...] = ()
    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()

    def __post_init__(self) -> None:
        obligations = tuple(sorted(self.obligations, key=lambda o: o.id))
        nodes = tuple(sorted(self.nodes, key=lambda n: n.ref))
        edges = tuple(sorted(self.edges, key=lambda e: e.id))
        object.__setattr__(self, "obligations", obligations)
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        self._validate()

    # ------------------------------------------------------------------ #
    # Lookups (cached; the graph is immutable so caching is safe)
    # ------------------------------------------------------------------ #
    @cached_property
    def obligation_by_id(self) -> dict[str, Obligation]:
        return {o.id: o for o in self.obligations}

    @cached_property
    def node_by_ref(self) -> dict[NodeRef, Node]:
        return {n.ref: n for n in self.nodes}

    @cached_property
    def refs(self) -> frozenset[NodeRef]:
        """Every vertex identity the graph contains (obligations and nodes)."""
        return frozenset({o.ref for o in self.obligations} | {n.ref for n in self.nodes})

    @cached_property
    def edge_by_id(self) -> dict[str, Edge]:
        return {e.id: e for e in self.edges}

    @cached_property
    def outgoing(self) -> dict[NodeRef, tuple[Edge, ...]]:
        """Edges grouped by source vertex, in canonical edge-id order per source."""
        table: dict[NodeRef, list[Edge]] = {}
        for edge in self.edges:
            table.setdefault(edge.src, []).append(edge)
        return {ref: tuple(edges) for ref, edges in table.items()}

    def has_vertex(self, ref: NodeRef) -> bool:
        return ref in self.refs

    def controls(self) -> tuple[Node, ...]:
        return tuple(n for n in self.nodes if n.ref.kind is NodeKind.CONTROL)

    def policies(self) -> tuple[Node, ...]:
        return tuple(n for n in self.nodes if n.ref.kind is NodeKind.POLICY)

    def evidence(self) -> tuple[Node, ...]:
        return tuple(n for n in self.nodes if n.ref.kind is NodeKind.EVIDENCE)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def _validate(self) -> None:
        if len({o.id for o in self.obligations}) != len(self.obligations):
            raise DuplicateVertexError("duplicate obligation id in graph")
        if len({n.ref for n in self.nodes}) != len(self.nodes):
            raise DuplicateVertexError("duplicate node ref in graph")
        if len({o.ref for o in self.obligations} & {n.ref for n in self.nodes}):
            raise DuplicateVertexError("a ref is both an obligation and a node")
        known = self.refs
        for edge in self.edges:
            if edge.src not in known:
                raise UnknownVertexError(f"edge {edge.id} names unknown source {edge.src}")
            if edge.dst not in known:
                raise UnknownVertexError(f"edge {edge.id} names unknown target {edge.dst}")

    # ------------------------------------------------------------------ #
    # Append-only mutators (each returns a new graph)
    # ------------------------------------------------------------------ #
    def add_obligation(self, obligation: Obligation) -> ObligationGraph:
        existing = self.obligation_by_id.get(obligation.id)
        if existing is not None and existing != obligation:
            raise DuplicateVertexError(
                f"obligation {obligation.id} already present with other content"
            )
        if existing is not None:
            return self
        return replace(self, obligations=(*self.obligations, obligation))

    def add_node(self, node: Node) -> ObligationGraph:
        existing = self.node_by_ref.get(node.ref)
        if existing is not None and existing != node:
            raise DuplicateVertexError(f"node {node.ref} already present with other content")
        if existing is not None:
            return self
        return replace(self, nodes=(*self.nodes, node))

    def add_edge(self, edge: Edge) -> ObligationGraph:
        """Add an edge, refusing endpoints the graph does not contain.

        Re-adding an identical edge id is idempotent; re-adding the same id with different
        content replaces it (an acceptance or a staleness flip on the same linkage).
        """
        for ref, role in ((edge.src, "source"), (edge.dst, "target")):
            if ref not in self.refs:
                raise UnknownVertexError(f"edge {edge.id} names unknown {role} {ref}")
        kept = tuple(e for e in self.edges if e.id != edge.id)
        return replace(self, edges=(*kept, edge))

    def with_obligations(self, obligations: Iterable[Obligation]) -> ObligationGraph:
        graph = self
        for obligation in obligations:
            graph = graph.add_obligation(obligation)
        return graph

    def with_nodes(self, nodes: Iterable[Node]) -> ObligationGraph:
        graph = self
        for node in nodes:
            graph = graph.add_node(node)
        return graph

    def with_edges(self, edges: Iterable[Edge]) -> ObligationGraph:
        graph = self
        for edge in edges:
            graph = graph.add_edge(edge)
        return graph

    def map_edges(self, fn: Callable[[Edge], Edge]) -> ObligationGraph:
        """Apply ``fn`` to every edge, returning a new graph (acceptance / staleness sweep)."""
        return replace(self, edges=tuple(fn(e) for e in self.edges))

    def mark_stale_for_moved_sources(self, moved_source_ids: Iterable[str]) -> ObligationGraph:
        """Mark stale every edge that originates from an obligation whose source moved.

        This is the deterministic half of horizon-driven staleness: a change item touches
        a set of source ids, and every obligation admitted from one of those sources has
        its outgoing mapping edges marked stale, which drops them from coverage until a
        reviewer re-accepts. Downstream policy-to-control edges are shared and are left
        untouched, because one obligation's source moving does not invalidate them.
        """
        moved = set(moved_source_ids)
        stale_obl_ids = {o.id for o in self.obligations if o.citation.source_id in moved}

        def sweep(edge: Edge) -> Edge:
            if edge.src.kind is NodeKind.OBLIGATION and edge.src.id in stale_obl_ids:
                return edge.with_stale(True)
            return edge

        return self.map_edges(sweep)
