"""Executable M5 evidence for bounded deterministic trajectory monitoring."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest

from safetybox import (
    BENIGN_001,
    BENIGN_002,
    TS_008,
    TS_009,
    SafetyBoxEvent,
    ScenarioRunner,
    ThreatScenario,
    TrajectoryMonitor,
    TrajectoryOrderingError,
)


def evaluate_scenario(scenario: ThreatScenario) -> tuple[SafetyBoxEvent, ...]:
    return ScenarioRunner().run(scenario).audit_events


def test_ts_009_emits_observational_staged_collection_to_egress_finding() -> None:
    events = evaluate_scenario(TS_009)
    evaluation = TrajectoryMonitor().evaluate(events)[0]

    assert [finding.rule_id for finding in evaluation.findings] == ["TRJ-001"]
    finding = evaluation.findings[0]
    assert finding.related_request_ids == tuple(f"TS-009:step-0{item}" for item in range(1, 5))
    assert finding.first_sequence_number == 5
    assert finding.last_sequence_number == finding.detection_sequence_number == 20
    assert finding.evidence["action_sequence"] == (
        "filesystem.read",
        "filesystem.read",
        "database.query",
        "network.send",
    )


def test_ts_008_emits_one_repeated_denied_boundary_probing_finding() -> None:
    evaluation = TrajectoryMonitor().evaluate(evaluate_scenario(TS_008))[0]

    assert [finding.rule_id for finding in evaluation.findings] == ["TRJ-002"]
    assert evaluation.findings[0].related_request_ids == (
        "TS-008:step-01",
        "TS-008:step-02",
        "TS-008:step-03",
    )


@pytest.mark.parametrize("scenario", [BENIGN_001, BENIGN_002])
def test_benign_controls_emit_no_suspicious_findings(scenario: ThreatScenario) -> None:
    evaluation = TrajectoryMonitor().evaluate(evaluate_scenario(scenario))[0]

    assert evaluation.findings == ()


def test_equivalent_semantic_trace_ignores_event_ids_timestamps_and_origin() -> None:
    events = evaluate_scenario(TS_009)
    alternate = tuple(
        replace(
            event,
            event_id=f"alternate-{event.sequence_number}",
            request_id=f"other-origin-{event.request_id.rsplit(':', maxsplit=1)[-1]}",
            correlation_id=f"alternate-{event.sequence_number}",
            timestamp=datetime(2030, 1, 1, tzinfo=UTC),
        )
        for event in events
    )
    first = TrajectoryMonitor().evaluate(events)[0].findings[0]
    second = TrajectoryMonitor().evaluate(alternate)[0].findings[0]

    assert (first.rule_id, first.finding_type, first.classification) == (
        second.rule_id,
        second.finding_type,
        second.classification,
    )
    assert first.evidence["action_sequence"] == second.evidence["action_sequence"]
    assert (first.first_sequence_number, first.last_sequence_number) == (
        second.first_sequence_number,
        second.last_sequence_number,
    )


def test_duplicate_and_decreasing_events_are_rejected_without_reordering() -> None:
    monitor = TrajectoryMonitor()
    first, second = evaluate_scenario(BENIGN_001)[:2]
    monitor.ingest(first)
    monitor.ingest(second)

    with pytest.raises(TrajectoryOrderingError):
        monitor.ingest(second)
    with pytest.raises(TrajectoryOrderingError):
        monitor.ingest(replace(second, sequence_number=1))


def test_gaps_are_accepted_and_visible_in_finding_sequence_range() -> None:
    events = evaluate_scenario(TS_009)
    gaps = tuple(replace(event, sequence_number=event.sequence_number * 2) for event in events)

    finding = TrajectoryMonitor().evaluate(gaps)[0].findings[0]

    assert (finding.first_sequence_number, finding.last_sequence_number) == (10, 40)


def test_window_can_prevent_longer_trajectory_match() -> None:
    monitor = TrajectoryMonitor(window_size=3)
    evaluation = monitor.evaluate(evaluate_scenario(TS_009))[0]

    assert evaluation.findings == ()


def test_sessions_and_tasks_do_not_combine_observations() -> None:
    events = evaluate_scenario(TS_009)
    terminal_events = [
        event
        for event in events
        if event.event_type.value in {"EXECUTION_SUCCEEDED", "AUTHORIZATION_DENIED"}
    ]
    split_sessions = tuple(
        replace(event, session_id="session-a" if index < 2 else "session-b")
        for index, event in enumerate(terminal_events)
    )
    split_tasks = tuple(
        replace(event, task_id="task-a" if index < 2 else "task-b")
        for index, event in enumerate(terminal_events)
    )

    assert all(not item.findings for item in TrajectoryMonitor().evaluate(split_sessions))
    assert TrajectoryMonitor().evaluate(split_tasks)[0].findings == ()


def test_findings_and_snapshots_are_immutable_and_explainable() -> None:
    evaluation = TrajectoryMonitor().evaluate(evaluate_scenario(TS_009))[0]
    finding = evaluation.findings[0]

    assert (
        finding.rule_id
        and finding.related_request_ids
        and finding.description
        and finding.evidence
    )
    with pytest.raises(FrozenInstanceError):
        finding.rule_id = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        finding.evidence["changed"] = True  # type: ignore[index]
    with pytest.raises(AttributeError):
        evaluation.findings.append(finding)  # type: ignore[attr-defined]


def test_clean_monitors_produce_identical_semantic_findings() -> None:
    events = evaluate_scenario(TS_008)
    first = TrajectoryMonitor().evaluate(events)[0].findings
    second = TrajectoryMonitor().evaluate(events)[0].findings

    assert first == second
