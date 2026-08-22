"""The versioned, append-only register with effective dating (pure stdlib, no clock).

A register is a sequence of immutable snapshots. Each snapshot pins a whole
:class:`~obligation_register.graph.ObligationGraph` at a version and an effective date, so
the register answers "what did the obligation graph look like as of this date" without
mutating history: a correction is a new snapshot, never an edit to an old one. Effective
dates are monotonic non-decreasing, which is what lets :meth:`Register.as_of` do a simple
backward scan and always find the generation in force on a given day.

Admission (deduping candidate obligations by their content key) is a shared primitive so
the regulatory and contractual systems admit into a register the same way.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date

from .graph import ObligationGraph
from .model import Obligation

__all__ = ["RegisterSnapshot", "Register", "AdmissionResult", "admit"]


@dataclass(frozen=True, slots=True)
class RegisterSnapshot:
    """One immutable generation of the obligation graph, versioned and effective-dated."""

    version: int
    effective_from: date
    graph: ObligationGraph
    note: str = ""


@dataclass(frozen=True, slots=True)
class Register:
    """An append-only sequence of snapshots, newest last.

    Construct empty (``Register()``) and grow it with :meth:`append`, which enforces the
    version and effective-date monotonicity invariants and returns a new register.
    """

    snapshots: tuple[RegisterSnapshot, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.snapshots

    @property
    def latest(self) -> RegisterSnapshot | None:
        """The most recent snapshot, or ``None`` for an empty register."""
        return self.snapshots[-1] if self.snapshots else None

    @property
    def latest_version(self) -> int:
        """The highest version number, or 0 when the register is empty."""
        return self.snapshots[-1].version if self.snapshots else 0

    def append(self, graph: ObligationGraph, effective_from: date, note: str = "") -> Register:
        """Append a new snapshot, versioned one above the last.

        Refuses an effective date earlier than the current head: history is append-only
        and effective dates never go backwards, so a backdated correction is a modelling
        error the caller must resolve (for example by choosing the head's effective date).
        """
        head = self.latest
        if head is not None and effective_from < head.effective_from:
            raise ValueError(
                f"effective_from {effective_from.isoformat()} is before the current head "
                f"{head.effective_from.isoformat()}; the register is append-only"
            )
        snapshot = RegisterSnapshot(
            version=self.latest_version + 1,
            effective_from=effective_from,
            graph=graph,
            note=note,
        )
        return replace(self, snapshots=(*self.snapshots, snapshot))

    def version(self, version: int) -> RegisterSnapshot | None:
        """The snapshot with the given version number, or ``None``."""
        for snapshot in self.snapshots:
            if snapshot.version == version:
                return snapshot
        return None

    def as_of(self, on: date) -> RegisterSnapshot | None:
        """The snapshot in force on ``on``: the latest with ``effective_from <= on``.

        Returns ``None`` when ``on`` predates the first snapshot, so a caller can tell the
        difference between "no register yet on that date" and "the empty graph".
        """
        chosen: RegisterSnapshot | None = None
        for snapshot in self.snapshots:  # ascending effective order (append-only)
            if snapshot.effective_from <= on:
                chosen = snapshot
            else:
                break
        return chosen


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    """The outcome of admitting candidate obligations into a graph: the new graph and why."""

    graph: ObligationGraph
    admitted: tuple[Obligation, ...]
    duplicates: tuple[Obligation, ...]


def admit(graph: ObligationGraph, candidates: Iterable[Obligation]) -> AdmissionResult:
    """Admit candidate obligations into ``graph``, deduping by content key.

    A candidate whose content key already exists (in the graph or earlier in this batch)
    is a duplicate and is dropped rather than admitted, so the same clause decomposed
    twice collapses to one register entry. Order of admission follows the input order.
    """
    seen = {obligation.key for obligation in graph.obligations}
    admitted: list[Obligation] = []
    duplicates: list[Obligation] = []
    for candidate in candidates:
        if candidate.key in seen:
            duplicates.append(candidate)
            continue
        seen.add(candidate.key)
        admitted.append(candidate)
    return AdmissionResult(
        graph=graph.with_obligations(admitted),
        admitted=tuple(admitted),
        duplicates=tuple(duplicates),
    )
