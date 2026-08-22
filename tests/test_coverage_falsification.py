"""The not-falsely-green proof: the coverage metric can go red, per segment.

A coverage figure that cannot fall when coverage genuinely worsens proves nothing. This
wires ``agent_eval_kit.assert_each_can_go_red`` over the coverage metric: for each segment
(a regulatory register and a contractual one), a fully covered graph must score at the bar
and a graph with one evidence edge withdrawn must score below it. If the degraded case
still passed, the metric would be falsely green and this test would fail with that message.
"""

from __future__ import annotations

from agent_eval_kit import assert_each_can_go_red

from obligation_register import Coverage, ObligationGraph, compute_coverage

from .fixtures import covered_graph, degrade

_SEGMENTS = {
    "regulatory": "mas-trm.example",
    "contractual": "outsourcing-msa.example",
}


def coverage_ratio(graph: ObligationGraph) -> float:
    """Fraction of obligations that are fully COVERED (the metric under test)."""
    report = compute_coverage(graph)
    total = len(report.results)
    if total == 0:
        return 1.0
    covered = sum(1 for result in report.results if result.coverage is Coverage.COVERED)
    return covered / total


def test_coverage_metric_can_go_red_per_segment() -> None:
    cases: dict[str, tuple[ObligationGraph, ObligationGraph]] = {}
    for segment, source in _SEGMENTS.items():
        green = covered_graph(segment, source)
        red = degrade(green, segment)
        cases[segment] = (green, red)
    assert_each_can_go_red(coverage_ratio, cases, threshold=1.0, metric="coverage_ratio")


def test_the_green_cases_really_are_fully_covered() -> None:
    for segment, source in _SEGMENTS.items():
        assert coverage_ratio(covered_graph(segment, source)) == 1.0
