"""Deadline arithmetic for the register (pure stdlib, no clock).

An obligation may carry a :class:`~obligation_register.model.Deadline`. Whether it is overdue or
approaching is never read from a system clock here: every question takes an explicit ``as_of`` date,
so a status is a pure function of the deadline and the reference date and replays identically.
contract-obligation-extraction layers renewal windows and notice periods on top of these primitives;
the kernel owns the primitives so both systems share one calendar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .enums import DeadlineStatus
from .model import Obligation

__all__ = [
    "DueEntry",
    "days_until",
    "deadline_status",
    "due_entries",
    "approaching",
]


@dataclass(frozen=True, slots=True)
class DueEntry:
    """An obligation's deadline resolved against an ``as_of`` date."""

    obligation_id: str
    due_on: date
    status: DeadlineStatus
    days_until: int
    kind: str = ""


def days_until(due_on: date, as_of: date) -> int:
    """Whole days from ``as_of`` to ``due_on`` (negative when the due date has passed)."""
    return (due_on - as_of).days


def deadline_status(due_on: date, as_of: date, soon_within_days: int) -> DeadlineStatus:
    """Classify a due date relative to ``as_of`` and the soon window.

    ``soon_within_days`` is the width of the DUE_SOON window in days. A due date strictly
    before ``as_of`` is OVERDUE; a due date within the window (inclusive, and including
    today) is DUE_SOON; anything further out is UPCOMING.
    """
    delta = days_until(due_on, as_of)
    if delta < 0:
        return DeadlineStatus.OVERDUE
    if delta <= max(0, soon_within_days):
        return DeadlineStatus.DUE_SOON
    return DeadlineStatus.UPCOMING


def due_entries(
    obligations: list[Obligation], as_of: date, soon_within_days: int
) -> list[DueEntry]:
    """Resolve every deadline-bearing obligation into a :class:`DueEntry`.

    Obligations with no deadline are omitted. The result is sorted by due date then id, so
    the nearest deadline leads and the order is stable across runs.
    """
    entries: list[DueEntry] = []
    for obligation in obligations:
        deadline = obligation.deadline
        if deadline is None:
            continue
        entries.append(
            DueEntry(
                obligation_id=obligation.id,
                due_on=deadline.due_on,
                status=deadline_status(deadline.due_on, as_of, soon_within_days),
                days_until=days_until(deadline.due_on, as_of),
                kind=deadline.kind,
            )
        )
    entries.sort(key=lambda e: (e.due_on, e.obligation_id))
    return entries


def approaching(
    obligations: list[Obligation], as_of: date, soon_within_days: int
) -> list[DueEntry]:
    """The deadline-bearing obligations that are overdue or due within the soon window.

    This is the actionable subset of :func:`due_entries`: it drops the UPCOMING entries so
    a caller sees only what needs attention as of the reference date.
    """
    return [
        entry
        for entry in due_entries(obligations, as_of, soon_within_days)
        if entry.status in (DeadlineStatus.OVERDUE, DeadlineStatus.DUE_SOON)
    ]
