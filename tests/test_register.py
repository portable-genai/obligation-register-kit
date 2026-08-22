"""Register invariants: versioning, effective dating, append-only, admission dedup."""

from __future__ import annotations

from datetime import date

import pytest

from obligation_register import (
    Citation,
    Obligation,
    ObligationGraph,
    Register,
    admit,
)


def _obl(obl_id: str, text: str, owner: str = "owner") -> Obligation:
    return Obligation(
        id=obl_id,
        title="t",
        text=text,
        owner=owner,
        citation=Citation(source_id="src.example", locator="s1"),
    )


def test_append_increments_version_and_is_append_only() -> None:
    reg = Register()
    assert reg.is_empty and reg.latest_version == 0
    reg2 = reg.append(ObligationGraph(), date(2026, 1, 1), note="v1")
    reg3 = reg2.append(ObligationGraph(), date(2026, 4, 1), note="v2")
    assert [s.version for s in reg3.snapshots] == [1, 2]
    assert reg.is_empty  # the original register is untouched


def test_effective_dates_may_not_go_backwards() -> None:
    reg = Register().append(ObligationGraph(), date(2026, 6, 1))
    with pytest.raises(ValueError):
        reg.append(ObligationGraph(), date(2026, 1, 1))


def test_as_of_returns_the_generation_in_force() -> None:
    g1 = ObligationGraph(obligations=(_obl("o1", "First."),))
    g2 = ObligationGraph(obligations=(_obl("o1", "First."), _obl("o2", "Second.")))
    reg = Register().append(g1, date(2026, 1, 1)).append(g2, date(2026, 4, 1))

    assert reg.as_of(date(2025, 12, 31)) is None  # before the first snapshot
    assert reg.as_of(date(2026, 3, 1)).version == 1
    assert reg.as_of(date(2026, 4, 1)).version == 2
    assert reg.as_of(date(2027, 1, 1)).version == 2  # latest still in force


def test_admit_dedupes_by_content_key() -> None:
    graph = ObligationGraph()
    candidates = [
        _obl("o1", "Encrypt data at rest.", owner="ciso"),
        _obl("o2", "encrypt   data at rest.", owner="ciso"),  # same key as o1 after normalising
        _obl("o3", "Retain logs for seven years.", owner="ciso"),
    ]
    result = admit(graph, candidates)
    assert [o.id for o in result.admitted] == ["o1", "o3"]
    assert [o.id for o in result.duplicates] == ["o2"]
    assert len(result.graph.obligations) == 2
