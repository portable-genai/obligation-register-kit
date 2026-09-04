"""The value objects of the register: refs, nodes, obligations, deadlines, edges.

All frozen, all slotted, all pure stdlib. These are the shared types obligations-control-mapping
(regulatory) and contract-obligation-extraction (contractual) both speak: an obligation decomposed
from a source, the policy / control / evidence nodes it maps to, the typed edges that connect them,
and the deadline an obligation may carry. Consequential structure lives here; consequential
DECISIONS live in :mod:`obligation_register.coverage`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

from .enums import EdgeKind, EdgeStatus, NodeKind
from .keys import dedup_key as _dedup_key
from .keys import edge_id as _edge_id
from .provenance import Citation

__all__ = [
    "NodeRef",
    "Node",
    "Deadline",
    "Obligation",
    "Edge",
    "EDGE_ENDPOINTS",
]

#: The obligatory endpoint kinds for each edge relation. An edge whose endpoints do not
#: match is a modelling error and is refused at construction, so a malformed graph cannot
#: be built in the first place.
EDGE_ENDPOINTS: dict[EdgeKind, tuple[NodeKind, NodeKind]] = {
    EdgeKind.OBLIGATION_TO_POLICY: (NodeKind.OBLIGATION, NodeKind.POLICY),
    EdgeKind.OBLIGATION_TO_CONTROL: (NodeKind.OBLIGATION, NodeKind.CONTROL),
    EdgeKind.POLICY_TO_CONTROL: (NodeKind.POLICY, NodeKind.CONTROL),
    EdgeKind.CONTROL_TO_EVIDENCE: (NodeKind.CONTROL, NodeKind.EVIDENCE),
}


@dataclass(frozen=True, slots=True, order=True)
class NodeRef:
    """The identity of a graph vertex: its kind and its stable id.

    Ordered, so any collection of refs sorts deterministically for stable output.
    """

    kind: NodeKind
    id: str

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("NodeRef.id must be a non-empty identifier")

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.id}"


@dataclass(frozen=True, slots=True)
class Node:
    """A policy, control or evidence vertex. Obligations use :class:`Obligation`.

    Kept deliberately thin: the coverage engine reasons over graph shape, not node body,
    so a node is an id, a title and its provenance. Obligation nodes are the rich type
    because they carry ownership, effective dating and deadlines.
    """

    ref: NodeRef
    title: str = ""
    citations: tuple[Citation, ...] = ()

    def __post_init__(self) -> None:
        if self.ref.kind is NodeKind.OBLIGATION:
            raise ValueError("an OBLIGATION vertex must be an Obligation, not a Node")


@dataclass(frozen=True, slots=True)
class Deadline:
    """A date an obligation must be met by, with its kind and a note.

    ``due_on`` is a plain :class:`datetime.date`: the kernel never reads a clock, so the
    date is supplied by the caller and every status question takes an explicit ``as_of``.
    """

    due_on: date
    kind: str = ""
    note: str = ""


@dataclass(frozen=True, slots=True)
class Obligation:
    """One atomic, owned obligation decomposed from a source clause.

    ``citation`` is required: an obligation with no source is not admissible. ``key`` is
    the content-derived dedup key; leaving it blank lets the register derive it from the
    text and owner, so two admissions of the same clause collapse to one entry.
    """

    id: str
    title: str
    text: str
    citation: Citation
    owner: str = ""
    key: str = ""
    effective_from: date | None = None
    deadline: Deadline | None = None
    attributes: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Obligation.id must be a non-empty identifier")
        if not self.text.strip():
            raise ValueError("Obligation.text must be a non-empty statement")
        if not self.key:
            object.__setattr__(self, "key", _dedup_key(self.text, self.owner))

    @property
    def ref(self) -> NodeRef:
        """This obligation's vertex identity in the graph."""
        return NodeRef(NodeKind.OBLIGATION, self.id)


@dataclass(frozen=True, slots=True)
class Edge:
    """A typed, directed, reviewed linkage between two vertices.

    Coverage counts an edge only when it is ``ACCEPTED`` and not ``stale``. ``id`` is
    content-derived from the endpoints and relation when left blank, so re-proposing the
    same linkage is idempotent rather than duplicating the edge.
    """

    src: NodeRef
    dst: NodeRef
    kind: EdgeKind
    status: EdgeStatus = EdgeStatus.PROPOSED
    stale: bool = False
    citations: tuple[Citation, ...] = ()
    note: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        want = EDGE_ENDPOINTS[self.kind]
        got = (self.src.kind, self.dst.kind)
        if got != want:
            raise ValueError(
                f"{self.kind.value} must connect {want[0].value} to {want[1].value}, "
                f"got {got[0].value} to {got[1].value}"
            )
        if not self.id:
            derived = _edge_id(self.src.kind, self.src.id, self.dst.kind, self.dst.id, self.kind)
            object.__setattr__(self, "id", derived)

    @property
    def counts_for_coverage(self) -> bool:
        """True when this edge is accepted and current, so it may contribute to coverage."""
        return self.status is EdgeStatus.ACCEPTED and not self.stale

    def accepted(self) -> Edge:
        """Return this edge marked ACCEPTED (a maker-checker acceptance)."""
        return replace(self, status=EdgeStatus.ACCEPTED)

    def rejected(self) -> Edge:
        """Return this edge marked REJECTED."""
        return replace(self, status=EdgeStatus.REJECTED)

    def with_stale(self, stale: bool = True) -> Edge:
        """Return this edge with its staleness flag set (deterministic staleness sweep)."""
        return replace(self, stale=stale)
