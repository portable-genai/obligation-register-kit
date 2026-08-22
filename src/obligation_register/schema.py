"""Canonical, versioned serialisation for the register (pure stdlib).

Two properties this module exists to guarantee:

* **Byte-identical replay.** :func:`canonical_json` encodes any kernel value into a
  deterministic JSON string (sorted keys, no incidental whitespace, dates as ISO strings,
  enums as their values). The same graph, register or coverage report always produces the
  same bytes, which is what the golden-replay proof rests on.
* **A versioned wire shape.** :data:`SCHEMA_VERSION` stamps every :func:`envelope`, so the
  contractual register that feeds a downstream system in a later wave carries an explicit
  schema version from day one. Any change to a field name or an enum member bumps it.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date
from enum import StrEnum
from typing import Any

__all__ = ["SCHEMA_VERSION", "to_jsonable", "canonical_json", "digest", "envelope"]

#: The schema version of the serialised register/coverage documents. Bump on any change to
#: a serialised field name, a dropped field, or an enum member: downstream consumers pin it.
SCHEMA_VERSION = "1.0"


def to_jsonable(obj: Any) -> Any:
    """Recursively convert a kernel value into JSON-safe primitives, deterministically.

    Order of checks matters: ``StrEnum`` is a ``str`` subclass and ``bool`` is an ``int``
    subclass, so each is matched before its supertype. Dataclasses serialise in declared
    field order; tuples and lists preserve order (the kernel already holds them sorted).
    """
    if obj is None or isinstance(obj, bool):
        return obj
    if isinstance(obj, StrEnum):
        return obj.value
    if isinstance(obj, (str, int, float)):
        return obj
    if isinstance(obj, date):
        return obj.isoformat()
    if is_dataclass(obj) and not isinstance(obj, type):
        return {field.name: to_jsonable(getattr(obj, field.name)) for field in fields(obj)}
    if isinstance(obj, Mapping):
        return {str(key): to_jsonable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(item) for item in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(canonical_json(item) for item in obj)
    raise TypeError(f"cannot serialise {type(obj).__name__} into the register schema")


def canonical_json(obj: Any) -> str:
    """Encode ``obj`` into a canonical JSON string: sorted keys, minimal separators."""
    return json.dumps(to_jsonable(obj), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(obj: Any) -> str:
    """A stable SHA-256 hex digest of the canonical JSON of ``obj`` (replay fingerprint)."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def envelope(kind: str, payload: Any) -> dict[str, Any]:
    """Wrap a serialised payload with the schema version and a kind tag (the wire shape)."""
    return {"schema_version": SCHEMA_VERSION, "kind": kind, "payload": to_jsonable(payload)}
