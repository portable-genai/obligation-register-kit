"""Provenance: the citation carried by every obligation and every edge (pure stdlib).

The kernel's rule is that nothing consequential exists without a source. An obligation
carries the citation of the clause it was decomposed from; an accepted mapping edge
carries the citation(s) that justify the linkage. A coverage or gap finding then quotes
those citations, so a reviewer can trace any figure back to a published instrument or an
executed clause without rerunning the engine.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Citation"]


@dataclass(frozen=True, slots=True, order=True)
class Citation:
    """A single, verifiable pointer into a source document.

    ``source_id`` and ``locator`` are the load-bearing pair: the stable id of the source
    (a regulation, a policy, an executed contract) and the position within it (a clause
    anchor, a section number, a page). The remaining fields are human-facing context. The
    type is ordered so citation tuples sort deterministically for byte-identical output.
    """

    source_id: str
    locator: str = ""
    title: str = ""
    url: str = ""
    version: str = ""
    snippet: str = ""

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("Citation.source_id must be a non-empty source identifier")
