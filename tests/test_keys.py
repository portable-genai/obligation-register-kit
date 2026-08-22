"""Deterministic key derivation."""

from __future__ import annotations

from obligation_register import EdgeKind, dedup_key, edge_id, normalise_text


def test_normalise_collapses_whitespace_and_case() -> None:
    assert normalise_text("  Encrypt   DATA\tat rest ") == "encrypt data at rest"


def test_dedup_key_is_stable_and_content_derived() -> None:
    a = dedup_key("Encrypt data at rest.", "ciso")
    b = dedup_key("encrypt   data at rest.", "ciso")
    assert a == b
    assert a.startswith("obl-")


def test_dedup_key_separates_owners_and_thresholds() -> None:
    assert dedup_key("Retain logs 7 years.", "ciso") != dedup_key("Retain logs 7 years.", "dpo")
    assert dedup_key("Retain logs 7 years.") != dedup_key("Retain logs 5 years.")


def test_edge_id_is_stable() -> None:
    a = edge_id("obligation", "o1", "control", "c1", EdgeKind.OBLIGATION_TO_CONTROL)
    b = edge_id("obligation", "o1", "control", "c1", EdgeKind.OBLIGATION_TO_CONTROL)
    assert a == b and a.startswith("edge-")
