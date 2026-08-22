"""Deterministic, content-derived keys (pure stdlib, no clock, no randomness).

Two systems admit obligations from different corpora into one shared register, so the
keys that dedupe obligations and identify edges must be a pure function of content: the
same clause admitted twice must collapse to one register entry, and a re-run over the
same graph must produce the same edge ids. Everything here is ``hashlib`` over normalised
text, so it is stable across processes, machines and Python runs.
"""

from __future__ import annotations

import hashlib
import re

from .enums import EdgeKind

__all__ = ["normalise_text", "dedup_key", "edge_id"]

#: How many hex characters of a digest go into a key: long enough to avoid collision on
#: any realistic register, short enough to stay readable in an audit line.
_KEY_LEN = 16

_WHITESPACE = re.compile(r"\s+")


def normalise_text(text: str) -> str:
    """Collapse whitespace and case so trivially different renderings dedupe together.

    Deliberately conservative: it lowercases and normalises whitespace but does not stem
    or drop punctuation, because two obligations that differ only in a numeric threshold
    must NOT collapse into one. The point is to catch re-formatting, not to paraphrase.
    """
    return _WHITESPACE.sub(" ", text).strip().lower()


def dedup_key(text: str, owner: str = "") -> str:
    """A stable dedup key for an atomic obligation, derived from its normalised text.

    ``owner`` is folded in so the same wording assigned to two different accountable
    owners stays two register entries: ownership is part of the obligation's identity in
    a register that assigns accountability, not merely metadata about it.
    """
    payload = f"{normalise_text(text)}\x1f{owner.strip().lower()}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"obl-{digest[:_KEY_LEN]}"


def edge_id(src_kind: str, src_id: str, dst_kind: str, dst_id: str, kind: EdgeKind) -> str:
    """A stable id for a directed, typed edge, idempotent across re-proposals.

    Two proposals of the same linkage (same endpoints, same relation) collapse to one
    edge id, so re-running the mapper over an unchanged graph never duplicates edges.
    """
    payload = f"{src_kind}:{src_id}\x1f{dst_kind}:{dst_id}\x1f{kind.value}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"edge-{digest[:_KEY_LEN]}"
