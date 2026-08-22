"""Deadline arithmetic: status classification and the approaching subset (no clock)."""

from __future__ import annotations

from datetime import date

from obligation_register import (
    Citation,
    Deadline,
    DeadlineStatus,
    Obligation,
    approaching,
    days_until,
    deadline_status,
    due_entries,
)


def _obl(obl_id: str, due: date | None) -> Obligation:
    deadline = Deadline(due_on=due, kind="renewal") if due is not None else None
    return Obligation(
        id=obl_id,
        title="t",
        text=f"Obligation {obl_id}.",
        citation=Citation(source_id="src.example", locator="s1"),
        deadline=deadline,
    )


def test_days_until_is_signed() -> None:
    assert days_until(date(2026, 1, 10), date(2026, 1, 1)) == 9
    assert days_until(date(2026, 1, 1), date(2026, 1, 10)) == -9


def test_status_classification_around_the_soon_window() -> None:
    as_of = date(2026, 1, 1)
    assert deadline_status(date(2025, 12, 31), as_of, 30) is DeadlineStatus.OVERDUE
    assert deadline_status(date(2026, 1, 1), as_of, 30) is DeadlineStatus.DUE_SOON  # today counts
    assert (
        deadline_status(date(2026, 1, 31), as_of, 30) is DeadlineStatus.DUE_SOON
    )  # inclusive edge
    assert deadline_status(date(2026, 2, 1), as_of, 30) is DeadlineStatus.UPCOMING


def test_due_entries_omit_undated_and_sort_by_due_date() -> None:
    obligations = [
        _obl("late", date(2026, 3, 1)),
        _obl("soon", date(2026, 1, 15)),
        _obl("none", None),
    ]
    entries = due_entries(obligations, date(2026, 1, 1), 30)
    assert [e.obligation_id for e in entries] == ["soon", "late"]


def test_approaching_keeps_only_overdue_and_due_soon() -> None:
    obligations = [
        _obl("overdue", date(2025, 12, 1)),
        _obl("soon", date(2026, 1, 10)),
        _obl("far", date(2026, 6, 1)),
    ]
    ids = [e.obligation_id for e in approaching(obligations, date(2026, 1, 1), 30)]
    assert ids == ["overdue", "soon"]
