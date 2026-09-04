"""obligation-register-kit: the shared obligation-register kernel for GRC systems.

One versioned source of truth for the obligation to policy to control to evidence graph that the
regulatory system of record (obligations-control-mapping) and the contractual obligation extractor
(contract-obligation-extraction) both build on. Everything here is pure standard library: no clock,
no I/O, no framework, no cloud SDK, so it installs and runs on an air-gapped host and a consuming
service inherits zero transitive runtime dependencies.

The kernel in one paragraph: an :class:`Obligation` is an atomic, owned statement
decomposed from a source and carrying its :class:`Citation`; :class:`Node` values are the
policy, control and evidence vertices it maps to; a typed, reviewed :class:`Edge` connects
two vertices and carries its own citations; an :class:`ObligationGraph` holds them
immutably; a :class:`Register` pins versioned, effective-dated snapshots of that graph; and
the pure :mod:`obligation_register.coverage` engine turns a graph into coverage bands,
orphan controls, stale edges and gaps, computed from ACCEPTED, NON-STALE edges only.

Consequential math lives in code (coverage, gaps, deadlines); a consuming service lets its
model narrate the result and never produce a number or a verdict.
"""

from __future__ import annotations

from . import coverage, deadlines, graph, keys, model, provenance, register, schema
from .coverage import (
    CoverageReport,
    GapFinding,
    ObligationCoverage,
    compute_coverage,
    coverage_for_obligation,
    orphan_controls,
    stale_edges,
)
from .deadlines import (
    DueEntry,
    approaching,
    days_until,
    deadline_status,
    due_entries,
)
from .enums import (
    Coverage,
    DeadlineStatus,
    EdgeKind,
    EdgeStatus,
    GapKind,
    NodeKind,
)
from .graph import (
    DuplicateVertexError,
    ObligationGraph,
    UnknownVertexError,
)
from .keys import dedup_key, edge_id, normalise_text
from .model import (
    EDGE_ENDPOINTS,
    Deadline,
    Edge,
    Node,
    NodeRef,
    Obligation,
)
from .provenance import Citation
from .register import (
    AdmissionResult,
    Register,
    RegisterSnapshot,
    admit,
)
from .schema import (
    SCHEMA_VERSION,
    canonical_json,
    digest,
    envelope,
    to_jsonable,
)

__version__ = "0.0.1"

__all__ = [
    # Version
    "__version__",
    "SCHEMA_VERSION",
    # Submodules
    "coverage",
    "deadlines",
    "graph",
    "keys",
    "model",
    "provenance",
    "register",
    "schema",
    # Enums
    "Coverage",
    "DeadlineStatus",
    "EdgeKind",
    "EdgeStatus",
    "GapKind",
    "NodeKind",
    # Provenance and model
    "Citation",
    "Deadline",
    "Edge",
    "EDGE_ENDPOINTS",
    "Node",
    "NodeRef",
    "Obligation",
    # Keys
    "dedup_key",
    "edge_id",
    "normalise_text",
    # Graph
    "DuplicateVertexError",
    "ObligationGraph",
    "UnknownVertexError",
    # Register
    "AdmissionResult",
    "Register",
    "RegisterSnapshot",
    "admit",
    # Coverage
    "CoverageReport",
    "GapFinding",
    "ObligationCoverage",
    "compute_coverage",
    "coverage_for_obligation",
    "orphan_controls",
    "stale_edges",
    # Deadlines
    "DueEntry",
    "approaching",
    "days_until",
    "deadline_status",
    "due_entries",
    # Schema
    "canonical_json",
    "digest",
    "envelope",
    "to_jsonable",
]
