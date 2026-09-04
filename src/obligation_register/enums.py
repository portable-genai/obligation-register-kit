"""The closed vocabularies of the obligation register (pure stdlib).

Every enum here is a ``StrEnum`` so a value serialises to a stable string and a persisted register
survives a round trip without a translation table. The kernel is shared by the regulatory system of
record (obligations-control-mapping) and the contractual extractor (contract-obligation-extraction),
so these vocabularies are the shared contract: adding a member is a schema change and carries a
``SCHEMA_VERSION`` bump in :mod:`obligation_register.schema`.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "NodeKind",
    "EdgeKind",
    "EdgeStatus",
    "Coverage",
    "GapKind",
    "DeadlineStatus",
]


class NodeKind(StrEnum):
    """The four vertex kinds of the obligation to policy to control to evidence graph."""

    OBLIGATION = "obligation"  # an atomic, owned obligation decomposed from a source
    POLICY = "policy"  # an internal policy or standard that answers obligations
    CONTROL = "control"  # a control that implements a policy
    EVIDENCE = "evidence"  # an evidence artefact that attests a control operates


class EdgeKind(StrEnum):
    """The typed, directed relations that form a coverage chain.

    A coverage chain runs obligation -> (policy ->)? control (-> evidence)?. Both the
    layered path (through a policy) and the direct path (obligation straight to control)
    are supported so a firm that maps obligations to controls without an intermediate
    policy layer is still first class.
    """

    OBLIGATION_TO_POLICY = "obligation_to_policy"
    OBLIGATION_TO_CONTROL = "obligation_to_control"
    POLICY_TO_CONTROL = "policy_to_control"
    CONTROL_TO_EVIDENCE = "control_to_evidence"


class EdgeStatus(StrEnum):
    """The review lifecycle of a proposed mapping edge.

    Coverage is computed from ``ACCEPTED`` edges only: a model proposal that no human
    has accepted never contributes to a coverage figure, which is what keeps coverage
    from resting on unreviewed output.
    """

    PROPOSED = "proposed"  # a candidate linkage awaiting maker-checker review
    ACCEPTED = "accepted"  # a human accepted the linkage; it counts toward coverage
    REJECTED = "rejected"  # a human rejected the linkage; it never counts


class Coverage(StrEnum):
    """How fully an obligation is answered by accepted, current mappings."""

    COVERED = "covered"  # reaches at least one control and every reached control is evidenced
    PARTIAL = "partial"  # reaches at least one control but not all reached are evidenced
    UNCOVERED = "uncovered"  # reaches no control via an accepted, non-stale edge


#: Weakest to strongest coverage. Comparisons use the index, never the string.
COVERAGE_ORDER: tuple[Coverage, ...] = (Coverage.UNCOVERED, Coverage.PARTIAL, Coverage.COVERED)


class GapKind(StrEnum):
    """The kinds of gap the pure gap engine surfaces from a graph."""

    UNCOVERED_OBLIGATION = "uncovered_obligation"  # an obligation reaching no current control
    PARTIAL_OBLIGATION = "partial_obligation"  # an obligation with unevidenced reached controls
    ORPHAN_CONTROL = "orphan_control"  # a control no obligation accepts a mapping to
    STALE_EDGE = "stale_edge"  # an accepted edge whose source moved and needs re-review


class DeadlineStatus(StrEnum):
    """The status of a deadline-bearing register entry relative to an ``as_of`` date."""

    NONE = "none"  # the entry carries no deadline
    UPCOMING = "upcoming"  # due, but further out than the configured soon window
    DUE_SOON = "due_soon"  # due within the configured soon window
    OVERDUE = "overdue"  # the due date is in the past relative to as_of
