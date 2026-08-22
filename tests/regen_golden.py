"""Regenerate the committed golden coverage output.

Run from the repo root: ``python -m tests.regen_golden``. It is deliberately a separate,
explicit step so the golden never regenerates itself silently inside a test run: a change
to the serialised shape must be a reviewed diff, not an invisible update.
"""

from __future__ import annotations

from pathlib import Path

from obligation_register import canonical_json, compute_coverage

from .fixtures import showcase_graph


def main() -> None:
    golden_dir = Path(__file__).parent / "golden"
    golden_dir.mkdir(exist_ok=True)
    target = golden_dir / "showcase_coverage.json"
    target.write_text(canonical_json(compute_coverage(showcase_graph())), encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
