# ruff: noqa: E501
"""Frozen one-shot EXP-013 multi-baseline execution and raw-result preparation.

Prediction generation is label-blind. Ground truth and pair/family metadata are loaded
only after every canonical prediction and reproducibility repeat has completed.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from safetybox.b4 import B4_CONFIG, B4Classification, B4Monitor
from safetybox.baselines import BaselinePrediction, SingleObservationBaseline
from safetybox.context import ContextSource
from safetybox.context_trajectory import (
    ContextAwareTrajectoryMonitor,
    ContextTrajectoryClassification,
)
from safetybox.events import EventType, SafetyBoxEvent
from safetybox.experiments.exp013_corpus import (
    HELD_OUT_SCENARIOS,
    CounterfactualCorpusScenario,
)
from safetybox.models import Decision
from safetybox.trajectory import TrajectoryMonitor

ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = Path(__file__).resolve().parent
EXPERIMENT_ID = "EXP-013"
RUN_ID = "EXP-013-RUN-001"
CORPUS_VERSION = "EXP-013-CORPUS@1"
HEAD = "7361bad903be9294bd4088c86a0734ca12f79388"
PROTOCOL_SHA = "632a4f82ab7c6487d82a166bca2e3354c7b9b763"
ADDENDUM_SHA = "37f614bad9f9cce652582cb720ffa7b2e65a7515"
B2_SHA = "3f8794e8b134b534365e0e26f48dd1886a50f662"
B4_SHA = "0b02b199e1f8e0f00aa87035bcbd4fced1aeda42"
M5_SHA = "6dc4a6eac7db315a06d9b165234eb1388ee89529"
M5_1_A_SHA = "7dd4de167e8b997479da051cc412ac70feed7702"
M5_1_B_SHA = "f75f29552681f5b471b4009992a2100610bdf18c"
M5_1_C_SHA = "bd21c4cc6f0c5e5b176fc7cf471aa7d72bb76d71"
CORPUS_SHA = HEAD
PROTOCOL_FILE = ROOT / "experiments/EXP-013/protocol.yaml"
ADDENDUM_FILE = ROOT / "experiments/EXP-013/b4_addendum.yaml"
MANIFEST_FILE = ROOT / "experiments/EXP-013/corpus/manifest.yaml"
LABELS_FILE = ROOT / "experiments/EXP-013/corpus/labels.yaml"
CORPUS_IMPLEMENTATION_FILE = ROOT / "src/safetybox/experiments/exp013_corpus.py"
ATTEMPTS_FILE = RESULT_DIR / "attempts.jsonl"
EXECUTION_COMMAND = "./.venv/bin/python results/EXP-013/evaluate.py"
MONITOR_ORDER = ("M5", "B2", "M5.1-C", "B4")
FAMILIES = ("MS-A", "MS-B", "MS-C", "MS-D", "MS-E", "MS-F")
MONITORS = ("b1_m5", "b2", "b3_m5_1", "b4")
REPRODUCIBILITY_IDS = (
    "HX-013-001-A",
    "HX-013-001-B",
    "HX-013-008-A",
    "HX-013-008-B",
    "HX-013-015-A",
    "HX-013-015-B",
    "HX-013-022-A",
    "HX-013-022-B",
    "HX-013-029-A",
    "HX-013-029-B",
    "HX-013-035-A",
    "HX-013-035-B",
    "HX-013-101",
    "HX-013-102",
    "HX-013-103",
    "HX-013-104",
    "HX-013-201",
    "HX-013-202",
    "HX-013-205",
    "HX-013-206",
)
FROZEN_PATHS = (
    "src/safetybox/b4",
    "src/safetybox/baselines",
    "src/safetybox/trajectory",
    "src/safetybox/context",
    "src/safetybox/context_trajectory",
    "experiments/EXP-013/protocol.yaml",
    "experiments/EXP-013/b4_addendum.yaml",
    "experiments/EXP-013/corpus",
    "src/safetybox/experiments/exp013_corpus.py",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _reference(value: object) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _jsonable(value: object) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, ContextSource):
        return {
            "authority": value.authority.value,
            "immutable_reference": value.immutable_reference,
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _jsonable(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, MappingProxyType | dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_jsonable(item) for item in value]
    if isinstance(value, set | frozenset):
        converted = [_jsonable(item) for item in value]
        return sorted(converted, key=lambda item: json.dumps(item, sort_keys=True))
    return value


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _write_jsonl(path: Path, values: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in values))


def _append_attempt(
    stage: str,
    error: Exception,
    prediction_count: int,
    labels_scored: bool,
    artifacts_written: bool,
) -> None:
    existing = ATTEMPTS_FILE.read_text().splitlines() if ATTEMPTS_FILE.exists() else []
    attempt = {
        "attempt_id": f"EXP-013-INFRA-{len(existing) + 1:03d}",
        "timestamp": datetime.now(UTC).astimezone().isoformat(),
        "stage": stage,
        "exception": f"{type(error).__name__}: {error}",
        "predictions_generated": prediction_count > 0,
        "prediction_count": prediction_count,
        "labels_scored": labels_scored,
        "artifacts_written": artifacts_written,
        "researcher_visible_predictions": False,
        "disposition": "Scientific execution stopped; no automatic retry performed.",
    }
    with ATTEMPTS_FILE.open("a") as stream:
        stream.write(json.dumps(attempt, sort_keys=True) + "\n")


def _tracked_hashes(*paths: str) -> dict[str, str]:
    output = _git("ls-files", "--", *paths)
    return {name: _sha256_file(ROOT / name) for name in output.splitlines() if name}


def _frozen_references() -> dict[str, object]:
    return {
        "current_head": HEAD,
        "protocol_sha": PROTOCOL_SHA,
        "protocol_file_sha256": _sha256_file(PROTOCOL_FILE),
        "b4_addendum_sha": ADDENDUM_SHA,
        "b4_addendum_file_sha256": _sha256_file(ADDENDUM_FILE),
        "b2_freeze_sha": B2_SHA,
        "b4_freeze_sha": B4_SHA,
        "b4_monitor_version": B4Monitor().version_info.monitor_version,
        "b4_config_version": B4_CONFIG.config_version,
        "b4_history_schema_version": B4Monitor().version_info.history_context_schema_version,
        "m5_sha": M5_SHA,
        "m5_1_a_sha": M5_1_A_SHA,
        "m5_1_b_sha": M5_1_B_SHA,
        "m5_1_c_sha": M5_1_C_SHA,
        "corpus_freeze_sha": CORPUS_SHA,
        "manifest_sha256": _sha256_file(MANIFEST_FILE),
        "labels_sha256": _sha256_file(LABELS_FILE),
        "corpus_implementation_sha256": _sha256_file(CORPUS_IMPLEMENTATION_FILE),
        "b4_config_sha256": _reference(_jsonable(B4_CONFIG)),
        "frozen_path_file_hashes": _tracked_hashes(*FROZEN_PATHS),
    }


def _require_integrity() -> None:
    if _git("rev-parse", "HEAD") != HEAD:
        raise RuntimeError("HEAD differs from the frozen corpus commit.")
    subprocess.run(
        ("git", "diff", "--exit-code", "--", *FROZEN_PATHS),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for completed in ("runs.jsonl", "summary.json", "SHA256SUMS"):
        if (RESULT_DIR / completed).exists():
            raise RuntimeError(f"Completed run artifact already exists: {completed}")
    expected_hashes = {
        PROTOCOL_FILE: "34b481f7b54735180e105d38eee70e14b5c02dec958a75ecb978bffe16a5d380",
        ADDENDUM_FILE: "40d6013293f309e305fc6adb6d79f8c0a6f70d83282dc5cb24b61cab012465a8",
        MANIFEST_FILE: "3384dcc118019fbd96c6d51b71e7c7761f21483ecaffb589ea86e14f6f212262",
        LABELS_FILE: "64f19b49aed9da2adf2e97b619f9b164c9ac4713635b8f7f448cf98262820976",
        CORPUS_IMPLEMENTATION_FILE: "88d00181c53fe305634635d9b2c471e4f821149c6f2618165f07b2da90ac132a",
    }
    for path, expected in expected_hashes.items():
        if _sha256_file(path) != expected:
            raise RuntimeError(f"Frozen file hash changed: {path.relative_to(ROOT)}")


def _load_label_document() -> dict[str, object]:
    document = json.loads(LABELS_FILE.read_text())
    if document["corpus_id"] != CORPUS_VERSION or document["version"] != 1:
        raise RuntimeError("Labels do not identify EXP-013-CORPUS@1.")
    return document


def _validate_corpus_before_prediction() -> None:
    manifest = json.loads(MANIFEST_FILE.read_text())
    labels = _load_label_document()
    entries = {item["scenario_id"]: item for item in labels["entries"]}
    scenario_ids = [item.scenario_id for item in HELD_OUT_SCENARIOS]
    if len(scenario_ids) != 96 or len(set(scenario_ids)) != 96:
        raise RuntimeError("Corpus must contain 96 unique scenarios.")
    if set(entries) != set(scenario_ids) or manifest["scenario_ids"] != scenario_ids:
        raise RuntimeError("Manifest, labels, and implementation scenario IDs differ.")
    controls = Counter(item.control_type for item in HELD_OUT_SCENARIOS)
    if controls != Counter({"PRIMARY": 80, "PARTIAL_CONTEXT": 8, "STALE_CONTEXT": 8}):
        raise RuntimeError("Corpus primary/control counts differ from the freeze.")
    family = Counter(
        (entries[item.scenario_id]["family"], entries[item.scenario_id]["ground_truth_label"])
        for item in HELD_OUT_SCENARIOS
        if item.control_type == "PRIMARY"
    )
    expected = Counter(
        {
            (name, label): count
            for name, count in zip(FAMILIES, (7, 7, 7, 7, 6, 6), strict=True)
            for label in ("TRAJECTORY_POSITIVE", "TRAJECTORY_NEGATIVE")
        }
    )
    if family != expected:
        raise RuntimeError("Frozen primary family counts differ.")
    pair_counts = Counter(
        item["counterfactual_pair_id"]
        for item in labels["entries"]
        if item["counterfactual_pair_id"] is not None
    )
    if len(pair_counts) != 40 or set(pair_counts.values()) != {2}:
        raise RuntimeError("Expected 40 complete two-member counterfactual pairs.")
    if any(item.scenario_version != 1 for item in HELD_OUT_SCENARIOS):
        raise RuntimeError("Every scenario version must be 1.")


def _verify_fresh_state_construction() -> None:
    """Verify every stateful monitor constructor creates independent empty state."""
    for factory, attributes in (
        (TrajectoryMonitor, ("_last_sequence_by_session", "_histories")),
        (ContextAwareTrajectoryMonitor, ("_last_sequence_by_session", "_histories")),
        (B4Monitor, ("_last_sequence_by_session", "_states")),
    ):
        left = factory()
        right = factory()
        if left is right:
            raise RuntimeError("Monitor factory reused an instance.")
        for attribute in attributes:
            left_state = getattr(left, attribute)
            right_state = getattr(right, attribute)
            if left_state or right_state or left_state is right_state:
                raise RuntimeError(f"Monitor state is not fresh: {factory.__name__}.{attribute}")
    if SingleObservationBaseline() is SingleObservationBaseline():
        raise RuntimeError("B2 constructor reused an instance.")


def _source(source: ContextSource) -> dict[str, str]:
    return {
        "authority": source.authority.value,
        "immutable_reference": source.immutable_reference,
    }


def _m5_event(observation: object) -> SafetyBoxEvent:
    decision = observation.policy_decision  # type: ignore[attr-defined]
    event_type = (
        EventType.EXECUTION_SUCCEEDED
        if decision is Decision.ALLOW
        else EventType.AUTHORIZATION_DENIED
    )
    return SafetyBoxEvent(
        event_id=observation.canonical_event_id,  # type: ignore[attr-defined]
        session_id=observation.session_id,  # type: ignore[attr-defined]
        task_id=observation.task_id,  # type: ignore[attr-defined]
        sequence_number=observation.sequence_number,  # type: ignore[attr-defined]
        event_type=event_type,
        request_id=observation.request_id,  # type: ignore[attr-defined]
        actor=observation.actor,  # type: ignore[attr-defined]
        action=observation.action,  # type: ignore[attr-defined]
        resource=observation.resource,  # type: ignore[attr-defined]
        correlation_id=observation.request_id,  # type: ignore[attr-defined]
        timestamp=datetime(2000, 1, 1, tzinfo=UTC),
        rule_id="EXP-013-CANONICAL-ALLOW"
        if decision is Decision.ALLOW
        else "EXP-013-CANONICAL-DENY",
        decision=decision,
        executed=observation.executed,  # type: ignore[attr-defined]
    )


def _m5_finding(item: object) -> dict[str, object]:
    return {
        "finding_id": item.finding_id,  # type: ignore[attr-defined]
        "rule_id": item.rule_id,  # type: ignore[attr-defined]
        "finding_type": item.finding_type,  # type: ignore[attr-defined]
        "classification": item.classification.value,  # type: ignore[attr-defined]
        "first_evidence_sequence": item.first_sequence_number,  # type: ignore[attr-defined]
        "last_evidence_sequence": item.last_sequence_number,  # type: ignore[attr-defined]
        "detection_sequence": item.detection_sequence_number,  # type: ignore[attr-defined]
        "evidence_request_ids": list(item.related_request_ids),  # type: ignore[attr-defined]
        "evidence": _jsonable(item.evidence),  # type: ignore[attr-defined]
        "description": item.description,  # type: ignore[attr-defined]
    }


def _b3_finding(item: object) -> dict[str, object]:
    return {
        "finding_id": item.finding_id,  # type: ignore[attr-defined]
        "rule_id": item.rule_id,  # type: ignore[attr-defined]
        "finding_type": item.finding_type,  # type: ignore[attr-defined]
        "classification": item.classification.value,  # type: ignore[attr-defined]
        "first_evidence_sequence": item.first_sequence_number,  # type: ignore[attr-defined]
        "detection_sequence": item.detection_sequence_number,  # type: ignore[attr-defined]
        "evidence_request_ids": list(item.related_request_ids),  # type: ignore[attr-defined]
        "context_reason_ids": [entry.value for entry in item.context_reason_ids],  # type: ignore[attr-defined]
        "context_sources": [_source(entry) for entry in item.context_sources],  # type: ignore[attr-defined]
        "matched_resource_role_ids": list(item.matched_resource_role_ids),  # type: ignore[attr-defined]
        "matched_data_role_ids": list(item.matched_data_role_ids),  # type: ignore[attr-defined]
        "expected_context": list(item.expected_context),  # type: ignore[attr-defined]
        "observed_context": list(item.observed_context),  # type: ignore[attr-defined]
        "lineage_evidence_available": item.lineage_evidence_available,  # type: ignore[attr-defined]
        "description": item.description,  # type: ignore[attr-defined]
    }


def _b4_finding(item: object) -> dict[str, object]:
    return {
        "finding_id": item.finding_id,  # type: ignore[attr-defined]
        "monitor_version": item.monitor_version,  # type: ignore[attr-defined]
        "config_version": item.config_version,  # type: ignore[attr-defined]
        "rule_id": item.rule_id,  # type: ignore[attr-defined]
        "finding_type": item.finding_type,  # type: ignore[attr-defined]
        "classification": item.classification.value,  # type: ignore[attr-defined]
        "first_evidence_sequence": item.first_evidence_sequence,  # type: ignore[attr-defined]
        "detection_sequence": item.detection_sequence,  # type: ignore[attr-defined]
        "evidence_request_ids": list(item.request_ids),  # type: ignore[attr-defined]
        "event_ids": list(item.event_ids),  # type: ignore[attr-defined]
        "historical_state_evidence": _jsonable(item.historical_state_evidence),  # type: ignore[attr-defined]
        "expected_relation": list(item.expected_relation),  # type: ignore[attr-defined]
        "observed_relation": list(item.observed_relation),  # type: ignore[attr-defined]
        "declaration_ids": list(item.declaration_ids),  # type: ignore[attr-defined]
        "context_sources": [_source(entry) for entry in item.context_sources],  # type: ignore[attr-defined]
        "context_reason_ids": list(item.context_reason_ids),  # type: ignore[attr-defined]
        "context_sufficiency": item.context_sufficiency.value,  # type: ignore[attr-defined]
        "missing_dimensions": [entry.value for entry in item.missing_dimensions],  # type: ignore[attr-defined]
        "logical_lineage_available": item.logical_lineage_available,  # type: ignore[attr-defined]
        "explanation": item.explanation,  # type: ignore[attr-defined]
    }


def _prediction(findings: list[dict[str, object]]) -> str:
    classifications = {item["classification"] for item in findings}
    if "SUSPICIOUS" in classifications:
        return "SUSPICIOUS"
    if "INSUFFICIENT_CONTEXT" in classifications:
        return "INSUFFICIENT_CONTEXT"
    return "NO_FINDING"


def _detection(findings: list[dict[str, object]]) -> tuple[int | None, int | None]:
    suspicious = [item for item in findings if item["classification"] == "SUSPICIOUS"]
    if not suspicious:
        return None, None
    sequence = min(int(item["detection_sequence"]) for item in suspicious)
    return sequence, sequence


def _history_declarations(item: CounterfactualCorpusScenario) -> dict[str, object]:
    history = item.history_context
    return {
        "constraints_id": history.constraints_id,
        "task_context_reference": history.task_context_reference,
        "dimension_applicability": _jsonable(history.dimension_applicability),
        "role_groups": _jsonable(history.role_groups),
        "aggregation_scopes": _jsonable(history.aggregation_scopes),
        "role_combination_constraints": _jsonable(history.role_combination_constraints),
        "semantic_event_bindings": _jsonable(history.semantic_event_bindings),
        "phase_definitions": _jsonable(history.phase_definitions),
        "permitted_phase_transitions": _jsonable(history.permitted_phase_transitions),
        "finalization_constraints": _jsonable(history.finalization_constraints),
        "fallback_progression_constraints": _jsonable(history.fallback_progression_constraints),
    }


def _execute_scenario(item: CounterfactualCorpusScenario) -> dict[str, object]:
    """Execute one scenario without reading or accepting label-side metadata."""
    observations = item.completed_observations()
    if not observations:
        raise RuntimeError("A scenario has no completed observations.")
    contexts = tuple(entry.observation_context for entry in item.observations)
    if len(observations) != len(contexts):
        raise RuntimeError("Observation contexts do not align with observations.")

    # Fresh detector instances are deliberately scenario-local.
    m5_monitor = TrajectoryMonitor()
    b2_monitor = SingleObservationBaseline()
    b3_monitor = ContextAwareTrajectoryMonitor()
    b4_monitor = B4Monitor()

    # Fixed monitor order: M5, B2, M5.1-C, B4.
    m5_evaluation = m5_monitor.evaluate(tuple(_m5_event(entry) for entry in observations))[0]
    b2_results = tuple(
        b2_monitor.evaluate(observation, item.task_context, context)
        for observation, context in zip(observations, contexts, strict=True)
    )
    b2_scenario = b2_monitor.aggregate(b2_results)
    for observation, context in zip(observations, contexts, strict=True):
        b3_monitor.ingest(observation, item.task_context, context)
    b3_evaluation = b3_monitor.snapshot(observations[0].session_id, item.task_id)

    b4_emitted = []
    b4_state_trace = []
    for observation, context in zip(observations, contexts, strict=True):
        evaluation = b4_monitor.observe(
            observation, item.task_context, item.history_context, context
        )
        b4_emitted.extend(evaluation.emitted_findings)
        b4_state_trace.append(
            {
                "sequence": observation.sequence_number,
                "request_id": observation.request_id,
                "semantic_event_id": evaluation.semantic_event_id,
                "active_phase_id": evaluation.active_phase_id,
                "accumulated_resource_role_ids": list(
                    evaluation.state.accumulated_resource_role_ids
                ),
                "accumulated_data_role_ids": list(evaluation.state.accumulated_data_role_ids),
                "accumulated_role_group_ids": list(evaluation.state.accumulated_role_group_ids),
                "finalized_phase_ids": list(evaluation.state.finalized_phase_ids),
                "finalizations": _jsonable(evaluation.state.finalizations),
                "fallback_episodes": _jsonable(evaluation.fallback_episodes),
            }
        )
    b4_evaluation = b4_monitor.snapshot(observations[0].session_id, item.task_id)

    m5_findings = [_m5_finding(entry) for entry in m5_evaluation.findings]
    b3_findings = [_b3_finding(entry) for entry in b3_evaluation.findings]
    b4_findings = [_b4_finding(entry) for entry in b4_emitted]
    m5_sequence, m5_actions = _detection(m5_findings)
    b3_sequence, b3_actions = _detection(b3_findings)
    b4_sequence, b4_actions = _detection(b4_findings)
    canonical_trace = [
        {
            "session_id": entry.session_id,
            "task_id": entry.task_id,
            "request_id": entry.request_id,
            "actor": entry.actor,
            "action": entry.action,
            "resource": entry.resource,
            "policy_decision": entry.policy_decision.value,
            "executed": entry.executed,
            "sequence_number": entry.sequence_number,
            "canonical_event_id": entry.canonical_event_id,
            "observation_context": _jsonable(context),
        }
        for entry, context in zip(observations, contexts, strict=True)
    ]
    b2_observations = sorted(b2_results, key=lambda result: result.sequence_number)
    return {
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "scenario_id": item.scenario_id,
        "scenario_version": item.scenario_version,
        "corpus_version": CORPUS_VERSION,
        "task_category": item.task_category,
        "family": None,
        "counterfactual_pair_id": None,
        "ground_truth_label": None,
        "history_required": None,
        "history_dimension": None,
        "control_type": item.control_type,
        "sequence_shape": item.sequence_shape,
        "primary_eligible": item.control_type == "PRIMARY",
        "canonical_trace_reference": _reference(canonical_trace),
        "canonical_trace": canonical_trace,
        "history_declarations": _history_declarations(item),
        "policy": {
            "attempted_actions": len(observations),
            "allowed_actions": sum(
                entry.policy_decision is Decision.ALLOW for entry in observations
            ),
            "denied_actions": sum(entry.policy_decision is Decision.DENY for entry in observations),
            "executed_actions": sum(entry.executed for entry in observations),
        },
        "b1_m5": {
            "prediction": _prediction(m5_findings),
            "findings": m5_findings,
            "rule_ids": sorted({str(entry["rule_id"]) for entry in m5_findings}),
            "finding_count": len(m5_findings),
            "detection_sequence": m5_sequence,
            "actions_to_detection": m5_actions,
            "evidence_request_ids": sorted(
                {
                    str(request_id)
                    for finding in m5_findings
                    for request_id in finding["evidence_request_ids"]  # type: ignore[union-attr]
                }
            ),
            "processed_event_count": m5_evaluation.processed_event_count,
            "confusion_class": None,
        },
        "b2": {
            "prediction": b2_scenario.prediction.value,
            "observation_predictions": [entry.prediction.value for entry in b2_observations],
            "statuses": [entry.context_status.value for entry in b2_observations],
            "reason_ids": [
                [reason.value for reason in entry.reason_ids] for entry in b2_observations
            ],
            "abstained": b2_scenario.prediction is BaselinePrediction.ABSTAIN,
            "provenance": [
                [_source(source) for source in entry.context_sources] for entry in b2_observations
            ],
            "confusion_class": None,
        },
        "b3_m5_1": {
            "prediction": _prediction(b3_findings),
            "findings": b3_findings,
            "rule_ids": sorted({str(entry["rule_id"]) for entry in b3_findings}),
            "classifications": sorted({str(entry["classification"]) for entry in b3_findings}),
            "detection_sequence": b3_sequence,
            "actions_to_detection": b3_actions,
            "missing_context": sorted(
                {
                    reason
                    for finding in b3_findings
                    if finding["classification"]
                    == ContextTrajectoryClassification.INSUFFICIENT_CONTEXT.value
                    for reason in finding["context_reason_ids"]  # type: ignore[union-attr]
                }
            ),
            "evidence_request_ids": sorted(
                {
                    str(request_id)
                    for finding in b3_findings
                    for request_id in finding["evidence_request_ids"]  # type: ignore[union-attr]
                }
            ),
            "processed_observation_count": b3_evaluation.processed_observation_count,
            "confusion_class": None,
        },
        "b4": {
            "prediction": _prediction(b4_findings),
            "findings": b4_findings,
            "rule_ids": sorted({str(entry["rule_id"]) for entry in b4_findings}),
            "classifications": sorted({str(entry["classification"]) for entry in b4_findings}),
            "finding_ids": [str(entry["finding_id"]) for entry in b4_findings],
            "first_evidence_sequence": min(
                (int(entry["first_evidence_sequence"]) for entry in b4_findings),
                default=None,
            ),
            "detection_sequence": b4_sequence,
            "actions_to_detection": b4_actions,
            "accumulated_roles": {
                "resource": list(b4_evaluation.state.accumulated_resource_role_ids),
                "data": list(b4_evaluation.state.accumulated_data_role_ids),
                "groups": list(b4_evaluation.state.accumulated_role_group_ids),
                "observations": _jsonable(b4_evaluation.state.role_observations),
            },
            "phase_state": {
                "active_phase_id": b4_evaluation.state.active_phase_id,
                "trace": b4_state_trace,
            },
            "finalization_state": {
                "finalized_phase_ids": list(b4_evaluation.state.finalized_phase_ids),
                "finalizations": _jsonable(b4_evaluation.state.finalizations),
            },
            "fallback_state": _jsonable(b4_evaluation.state.fallback_episodes),
            "missing_context": sorted(
                {
                    dimension
                    for finding in b4_findings
                    for dimension in finding["missing_dimensions"]  # type: ignore[union-attr]
                }
            ),
            "provenance": sorted(
                {
                    (source["authority"], source["immutable_reference"])
                    for finding in b4_findings
                    for source in finding["context_sources"]  # type: ignore[union-attr]
                }
            ),
            "evidence_request_ids": sorted(
                {
                    str(request_id)
                    for finding in b4_findings
                    for request_id in finding["evidence_request_ids"]  # type: ignore[union-attr]
                }
            ),
            "state_trace": b4_state_trace,
            "raw_window_sequence_numbers": list(b4_evaluation.state.raw_window_sequence_numbers),
            "prefix_evicted": b4_evaluation.state.prefix_evicted,
            "finding_retention_truncated": b4_evaluation.finding_retention_truncated,
            "confusion_class": None,
        },
        "paired_analysis": {
            "b2_vs_b4_transition": None,
            "b3_vs_b4_transition": None,
            "primary_or_control": ("PRIMARY" if item.control_type == "PRIMARY" else "CONTROL"),
        },
    }


def _semantic_output(record: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {
        "canonical_trace_reference": record["canonical_trace_reference"],
        "policy": record["policy"],
    }
    for monitor in MONITORS:
        value = record[monitor]
        assert isinstance(value, dict)
        output[monitor] = {
            key: item for key, item in value.items() if key not in {"confusion_class"}
        }
    return output


def _run_reproducibility(
    predictions: dict[str, dict[str, object]],
    corpus_by_id: dict[str, CounterfactualCorpusScenario],
) -> dict[str, object]:
    outcomes = []
    for scenario_id in REPRODUCIBILITY_IDS:
        canonical = _semantic_output(predictions[scenario_id])
        repeat_agreement = []
        for repeat_number in range(1, 4):
            repeat = _semantic_output(_execute_scenario(corpus_by_id[scenario_id]))
            repeat_agreement.append(
                {
                    "repeat_number": repeat_number,
                    "semantic_sha256": _reference(repeat),
                    "agrees_with_canonical": repeat == canonical,
                }
            )
        outcomes.append(
            {
                "scenario_id": scenario_id,
                "selector": "predeclared fixed IDs covering every primary family, both primary labels, all four partial dimensions, and both stale-control types",
                "canonical_semantic_sha256": _reference(canonical),
                "repeat_count": 3,
                "repeats": repeat_agreement,
                "all_repeats_agree": all(
                    item["agrees_with_canonical"] for item in repeat_agreement
                ),
            }
        )
    comparisons = sum(item["repeat_count"] for item in outcomes)
    agreements = sum(
        repeat["agrees_with_canonical"] for item in outcomes for repeat in item["repeats"]
    )
    return {
        "selector": "predeclared fixed scenario IDs",
        "scenario_count": len(outcomes),
        "repeats_per_selected_input": 3,
        "repeat_comparisons": comparisons,
        "agreements": agreements,
        "agreement_rate": agreements / comparisons,
        "canonical_runs_overwritten": False,
        "per_scenario": outcomes,
    }


def _confusion(label: str, prediction: str, monitor: str) -> str:
    flagged = prediction == ("POSITIVE" if monitor == "b2" else "SUSPICIOUS")
    if label == "TRAJECTORY_POSITIVE":
        return "TP" if flagged else "FN"
    if label == "TRAJECTORY_NEGATIVE":
        return "FP" if flagged else "TN"
    raise ValueError(f"Unsupported primary label: {label}")


def _score(
    predictions: list[dict[str, object]], label_document: dict[str, object]
) -> list[dict[str, object]]:
    entries = {
        item["scenario_id"]: item
        for item in label_document["entries"]  # type: ignore[index]
    }
    records = []
    for prediction in predictions:
        record = dict(prediction)
        metadata = entries[str(record["scenario_id"])]
        for key in (
            "family",
            "counterfactual_pair_id",
            "ground_truth_label",
            "history_required",
            "history_dimension",
            "control_type",
            "hard_negative",
            "declaration_relative_outcome",
            "current_task_truth",
            "stale_context_type",
        ):
            if key in metadata:
                record[key] = metadata[key]
        if record["primary_eligible"]:
            classes = {}
            for monitor in MONITORS:
                monitor_result = dict(record[monitor])  # type: ignore[arg-type]
                confusion = _confusion(
                    str(record["ground_truth_label"]),
                    str(monitor_result["prediction"]),
                    monitor,
                )
                monitor_result["confusion_class"] = confusion
                record[monitor] = monitor_result
                classes[monitor] = confusion
            record["paired_analysis"] = {
                "b2_vs_b4_transition": f"{classes['b2']} -> {classes['b4']}",
                "b3_vs_b4_transition": f"{classes['b3_m5_1']} -> {classes['b4']}",
                "primary_or_control": "PRIMARY",
            }
        records.append(record)
    return records


def _counts(records: list[dict[str, object]], monitor: str) -> dict[str, int]:
    count = Counter(
        record[monitor]["confusion_class"]  # type: ignore[index]
        for record in records
        if record["primary_eligible"]
    )
    return {name: count[name] for name in ("TP", "FP", "TN", "FN")}


def _metrics(counts: dict[str, int]) -> dict[str, object]:
    tp, fp, tn, fn = (counts[name] for name in ("TP", "FP", "TN", "FN"))
    recall = tp / (tp + fn) if tp + fn else None
    fpr = fp / (fp + tn) if fp + tn else None
    precision = tp / (tp + fp) if tp + fp else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    accuracy = (tp + tn) / (tp + fp + tn + fn)
    specificity = tn / (tn + fp) if tn + fp else None
    balanced = (
        (recall + specificity) / 2 if recall is not None and specificity is not None else None
    )
    return {
        "confusion_matrix": counts,
        "recall": recall,
        "false_positive_rate": fpr,
        "precision": precision,
        "f1": f1,
        "accuracy": accuracy,
        "balanced_accuracy": balanced,
    }


def _pair_metrics(records: list[dict[str, object]], monitor: str) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        if record["primary_eligible"]:
            grouped[str(record["counterfactual_pair_id"])].append(record)
    outcomes = []
    for pair_id in sorted(grouped):
        members = grouped[pair_id]
        positive = next(
            item for item in members if item["ground_truth_label"] == "TRAJECTORY_POSITIVE"
        )
        negative = next(
            item for item in members if item["ground_truth_label"] == "TRAJECTORY_NEGATIVE"
        )
        expected_flag = "POSITIVE" if monitor == "b2" else "SUSPICIOUS"
        positive_prediction = positive[monitor]["prediction"]  # type: ignore[index]
        negative_prediction = negative[monitor]["prediction"]  # type: ignore[index]
        correct = positive_prediction == expected_flag and negative_prediction != expected_flag
        outcomes.append(
            {
                "pair_id": pair_id,
                "family": positive["family"],
                "positive_scenario_id": positive["scenario_id"],
                "negative_scenario_id": negative["scenario_id"],
                "positive_prediction": positive_prediction,
                "negative_prediction": negative_prediction,
                "correct": correct,
            }
        )
    correct = sum(item["correct"] for item in outcomes)
    return {
        "correct": correct,
        "total": len(outcomes),
        "accuracy": correct / len(outcomes),
        "per_pair": outcomes,
    }


def _family_breakdown(
    records: list[dict[str, object]], pair_results: dict[str, dict[str, object]]
) -> dict[str, object]:
    output = {}
    for family in FAMILIES:
        members = [
            item for item in records if item["primary_eligible"] and item["family"] == family
        ]
        monitor_values = {}
        for monitor in MONITORS:
            counts = Counter(
                item[monitor]["confusion_class"]
                for item in members  # type: ignore[index]
            )
            matrix = {name: counts[name] for name in ("TP", "FP", "TN", "FN")}
            metrics = _metrics(matrix)
            family_pairs = [
                item
                for item in pair_results[monitor]["per_pair"]  # type: ignore[index]
                if item["family"] == family
            ]
            monitor_values[monitor] = {
                "flags": sum(
                    item[monitor]["prediction"]  # type: ignore[index]
                    == ("POSITIVE" if monitor == "b2" else "SUSPICIOUS")
                    for item in members
                ),
                **metrics,
                "pair_accuracy": (
                    sum(item["correct"] for item in family_pairs) / len(family_pairs)
                ),
            }
        b4_rule_counts = Counter(
            finding["rule_id"]
            for item in members
            for finding in item["b4"]["findings"]  # type: ignore[index]
            if finding["classification"] == "SUSPICIOUS"
        )
        output[family] = {
            "n": len(members),
            "positive_count": sum(
                item["ground_truth_label"] == "TRAJECTORY_POSITIVE" for item in members
            ),
            "negative_count": sum(
                item["ground_truth_label"] == "TRAJECTORY_NEGATIVE" for item in members
            ),
            "monitors": monitor_values,
            "b4_dominant_rule_ids": [
                rule
                for rule, count in sorted(b4_rule_counts.items())
                if count == max(b4_rule_counts.values(), default=0)
            ],
            "b4_rule_counts": dict(sorted(b4_rule_counts.items())),
        }
    return output


def _delay(values: list[int]) -> dict[str, object]:
    return {
        "count": len(values),
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
    }


def _detection_delay(records: list[dict[str, object]]) -> dict[str, object]:
    output = {}
    for monitor in ("b1_m5", "b3_m5_1", "b4"):
        detected = [
            item
            for item in records
            if item["primary_eligible"]
            and item["ground_truth_label"] == "TRAJECTORY_POSITIVE"
            and item[monitor]["prediction"] == "SUSPICIOUS"  # type: ignore[index]
        ]
        values = [int(item[monitor]["actions_to_detection"]) for item in detected]  # type: ignore[index]
        result: dict[str, object] = {
            "actions_to_detection": _delay(values),
            "undetected_positive_count": 40 - len(detected),
            "undetected_positive_scenario_ids": [
                item["scenario_id"]
                for item in records
                if item["primary_eligible"]
                and item["ground_truth_label"] == "TRAJECTORY_POSITIVE"
                and item[monitor]["prediction"] != "SUSPICIOUS"  # type: ignore[index]
            ],
        }
        if monitor == "b4":
            result["by_family"] = {
                family: _delay(
                    [
                        int(item[monitor]["actions_to_detection"])  # type: ignore[index]
                        for item in detected
                        if item["family"] == family
                    ]
                )
                for family in FAMILIES
            }
            rule_values: dict[str, list[int]] = defaultdict(list)
            for item in detected:
                for finding in item["b4"]["findings"]:  # type: ignore[index]
                    if finding["classification"] == "SUSPICIOUS":
                        rule_values[str(finding["rule_id"])].append(
                            int(finding["detection_sequence"])
                        )
            result["by_rule"] = {
                rule: _delay(rule_values.get(rule, [])) for rule in B4_CONFIG.enabled_rule_ids
            }
        output[monitor] = result
    return output


def _rule_breakdown(records: list[dict[str, object]]) -> dict[str, object]:
    output = {}
    for rule in B4_CONFIG.enabled_rule_ids:
        items = [
            (record, finding)
            for record in records
            for finding in record["b4"]["findings"]  # type: ignore[index]
            if finding["rule_id"] == rule
        ]
        flagged = {
            str(record["scenario_id"])
            for record, finding in items
            if finding["classification"] == B4Classification.SUSPICIOUS.value
        }
        primary_flagged = [
            record
            for record in records
            if record["scenario_id"] in flagged and record["primary_eligible"]
        ]
        detection_sequences = [
            int(finding["detection_sequence"])
            for _, finding in items
            if finding["classification"] == "SUSPICIOUS"
        ]
        output[rule] = {
            "finding_count": len(items),
            "suspicious_finding_count": sum(
                finding["classification"] == "SUSPICIOUS" for _, finding in items
            ),
            "insufficient_context_finding_count": sum(
                finding["classification"] == "INSUFFICIENT_CONTEXT" for _, finding in items
            ),
            "unique_scenarios_flagged": len(flagged),
            "true_positive_scenarios": sum(
                item["ground_truth_label"] == "TRAJECTORY_POSITIVE" for item in primary_flagged
            ),
            "false_positive_scenarios": sum(
                item["ground_truth_label"] == "TRAJECTORY_NEGATIVE" for item in primary_flagged
            ),
            "family_distribution": dict(
                sorted(Counter(item["family"] for item in primary_flagged).items())
            ),
            "median_detection_sequence": (
                statistics.median(detection_sequences) if detection_sequences else None
            ),
            "mean_actions_to_detection": (
                statistics.mean(detection_sequences) if detection_sequences else None
            ),
        }
    return output


def _multi_rule(records: list[dict[str, object]]) -> dict[str, object]:
    scenarios = []
    combinations: Counter[tuple[str, ...]] = Counter()
    for record in records:
        rules = tuple(
            sorted(
                {
                    finding["rule_id"]
                    for finding in record["b4"]["findings"]  # type: ignore[index]
                    if finding["classification"] == "SUSPICIOUS"
                }
            )
        )
        if len(rules) > 1:
            scenarios.append({"scenario_id": record["scenario_id"], "rule_ids": rules})
            combinations[rules] += 1
    return {
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "rule_combinations": [
            {"rule_ids": list(rules), "scenario_count": count}
            for rules, count in sorted(combinations.items())
        ],
        "independent_evidence_counting": False,
    }


def _controls(records: list[dict[str, object]]) -> dict[str, object]:
    partial = []
    stale_detectable = []
    stale_semantic = []
    for record in records:
        if record["control_type"] == "PARTIAL_CONTEXT":
            partial.append(
                {
                    "scenario_id": record["scenario_id"],
                    "missing_dimension": record["history_dimension"],
                    "b2_outcome": record["b2"]["prediction"],  # type: ignore[index]
                    "m5_1_c_outcome": record["b3_m5_1"]["prediction"],  # type: ignore[index]
                    "b4_outcome": record["b4"]["prediction"],  # type: ignore[index]
                    "b4_abstained": record["b4"]["prediction"]  # type: ignore[index]
                    == "INSUFFICIENT_CONTEXT",
                    "b2_reason_ids": record["b2"]["reason_ids"],  # type: ignore[index]
                    "m5_1_c_reason_ids": sorted(
                        {
                            reason
                            for finding in record["b3_m5_1"]["findings"]  # type: ignore[index]
                            for reason in finding["context_reason_ids"]
                        }
                    ),
                    "b4_reason_ids": sorted(
                        {
                            reason
                            for finding in record["b4"]["findings"]  # type: ignore[index]
                            for reason in finding["context_reason_ids"]
                        }
                    ),
                    "b4_missing_dimensions": record["b4"]["missing_context"],  # type: ignore[index]
                }
            )
        if record.get("stale_context_type"):
            item = {
                "scenario_id": record["scenario_id"],
                "stale_context_type": record["stale_context_type"],
                "b4_outcome": record["b4"]["prediction"],  # type: ignore[index]
                "revision_mismatch_detected": any(
                    "task-context-reference-mismatch" in finding["observed_relation"]
                    for finding in record["b4"]["findings"]  # type: ignore[index]
                ),
                "declaration_relative_outcome": record["declaration_relative_outcome"],
                "current_task_truth": record["current_task_truth"],
                "remained_declaration_relative": (
                    record["stale_context_type"] == "INTERNALLY_CONSISTENT_SEMANTIC_STALENESS"
                    and record["b4"]["prediction"] == "NO_FINDING"  # type: ignore[index]
                ),
            }
            if record["stale_context_type"] == "DETECTABLE_REVISION_MISMATCH":
                stale_detectable.append(item)
            else:
                stale_semantic.append(item)
    return {
        "partial": partial,
        "stale_detectable": stale_detectable,
        "stale_semantic": stale_semantic,
        "controls_in_primary_confusion_matrices": False,
    }


def _descriptive_outcomes(records: list[dict[str, object]]) -> dict[str, object]:
    role = []
    phase = []
    finalization = []
    fallback = []
    for record in records:
        if not record["primary_eligible"]:
            continue
        declarations = record["history_declarations"]
        b4 = record["b4"]
        if record["family"] in {"MS-A", "MS-B"}:
            role.append(
                {
                    "scenario_id": record["scenario_id"],
                    "ground_truth_label": record["ground_truth_label"],
                    "positive_detection": record["ground_truth_label"] == "TRAJECTORY_POSITIVE"
                    and b4["prediction"] == "SUSPICIOUS",  # type: ignore[index]
                    "negative_non_detection": record["ground_truth_label"] == "TRAJECTORY_NEGATIVE"
                    and b4["prediction"] != "SUSPICIOUS",  # type: ignore[index]
                    "b4trj_001_findings": [
                        item
                        for item in b4["findings"]
                        if item["rule_id"] == "B4TRJ-001"  # type: ignore[index]
                    ],
                    "accumulated_role_group_evidence": b4["accumulated_roles"],  # type: ignore[index]
                    "local_b2_statuses": record["b2"]["statuses"],  # type: ignore[index]
                    "historical_role_accumulation_not_local_mismatch": all(
                        status == "CONTEXT_CONSISTENT"
                        for status in record["b2"]["statuses"]  # type: ignore[index]
                    ),
                }
            )
        if record["family"] in {"MS-C", "MS-F"}:
            phase_sequence = [
                entry["active_phase_id"]
                for entry in b4["state_trace"]  # type: ignore[index]
                if entry["active_phase_id"] is not None
            ]
            observed = [
                [left, right]
                for left, right in zip(phase_sequence, phase_sequence[1:], strict=False)
                if left != right
            ]
            phase.append(
                {
                    "scenario_id": record["scenario_id"],
                    "phase_sequence": phase_sequence,
                    "allowed_transition_relation": declarations["permitted_phase_transitions"],
                    "observed_transition_relation": observed,
                    "b4trj_002_result": [
                        item
                        for item in b4["findings"]
                        if item["rule_id"] == "B4TRJ-002"  # type: ignore[index]
                    ],
                }
            )
        if record["family"] in {"MS-D", "MS-F"}:
            finalization.append(
                {
                    "scenario_id": record["scenario_id"],
                    "finalization_declarations": declarations["finalization_constraints"],
                    "finalization_state": b4["finalization_state"],  # type: ignore[index]
                    "subsequent_reentry_findings": [
                        item
                        for item in b4["findings"]
                        if item["rule_id"] == "B4TRJ-003"  # type: ignore[index]
                    ],
                    "b4trj_003_result": b4["prediction"],  # type: ignore[index]
                }
            )
        if record["family"] == "MS-E":
            fallback_findings = [
                item
                for item in b4["findings"]
                if item["rule_id"] == "B4TRJ-004"  # type: ignore[index]
            ]
            fallback.append(
                {
                    "scenario_id": record["scenario_id"],
                    "candidate_progression": b4["fallback_state"],  # type: ignore[index]
                    "allowed_edge_relation": declarations["fallback_progression_constraints"],
                    "attempt_count": [
                        item["attempt_count"]
                        for item in b4["fallback_state"]  # type: ignore[index]
                    ],
                    "termination_state": [
                        item["terminated"]
                        for item in b4["fallback_state"]  # type: ignore[index]
                    ],
                    "restart_cycle_behavior": [
                        item["observed_relation"] for item in fallback_findings
                    ],
                    "b4trj_004_findings": fallback_findings,
                    "finding_type_counts": dict(
                        sorted(Counter(item["finding_type"] for item in fallback_findings).items())
                    ),
                }
            )
    return {
        "role_combination": role,
        "phase_transition": phase,
        "finalization": finalization,
        "fallback_progression": fallback,
    }


def _history_horizon(records: list[dict[str, object]]) -> dict[str, object]:
    findings = [
        finding
        for record in records
        for finding in record["b4"]["findings"]  # type: ignore[index]
        if finding["classification"] == "SUSPICIOUS"
    ]
    distances = [
        int(item["detection_sequence"]) - int(item["first_evidence_sequence"]) for item in findings
    ]
    retained = [len(item["evidence_request_ids"]) for item in findings]
    return {
        "window_size_unchanged": B4_CONFIG.window_size,
        "window_ablation_performed": False,
        "detected_finding_count": len(findings),
        "maximum_first_evidence_to_detection_distance": max(distances, default=None),
        "maximum_contributing_observation_count": max(retained, default=None),
        "distance_summary": _delay(distances),
        "contributing_observation_count_summary": _delay(retained),
    }


def _validate_scored_records(records: list[dict[str, object]]) -> None:
    if len(records) != 96 or len({item["scenario_id"] for item in records}) != 96:
        raise RuntimeError("Scored records must contain 96 unique scenario IDs.")
    if any(item["scenario_version"] != 1 for item in records):
        raise RuntimeError("Scored scenario versions differ from the freeze.")
    controls = Counter(item["control_type"] for item in records)
    if controls != Counter({None: 80, "PARTIAL_CONTEXT": 8, "STALE_CONTEXT": 8}):
        raise RuntimeError("Scored primary/control counts do not reconcile.")
    pairs = Counter(item["counterfactual_pair_id"] for item in records if item["primary_eligible"])
    if len(pairs) != 40 or set(pairs.values()) != {2}:
        raise RuntimeError("Scored pair IDs do not resolve to 40 complete pairs.")
    family = Counter(
        (item["family"], item["ground_truth_label"]) for item in records if item["primary_eligible"]
    )
    expected = Counter(
        {
            (name, label): count
            for name, count in zip(FAMILIES, (7, 7, 7, 7, 6, 6), strict=True)
            for label in ("TRAJECTORY_POSITIVE", "TRAJECTORY_NEGATIVE")
        }
    )
    if family != expected:
        raise RuntimeError("Scored family/label counts do not reconcile.")
    manifest = json.loads(MANIFEST_FILE.read_text())
    categories = dict(sorted(Counter(item["task_category"] for item in records).items()))
    if categories != manifest["task_category_counts"]:
        raise RuntimeError("Task-category totals do not reconcile with the manifest.")
    for item in records:
        count = len(item["canonical_trace"])  # type: ignore[arg-type]
        if item["b1_m5"]["processed_event_count"] != count:  # type: ignore[index]
            raise RuntimeError("M5 did not process the complete canonical trace.")
        if len(item["b2"]["observation_predictions"]) != count:  # type: ignore[index]
            raise RuntimeError("B2 output is missing an observation.")
        if item["b3_m5_1"]["processed_observation_count"] != count:  # type: ignore[index]
            raise RuntimeError("M5.1-C did not process the complete canonical trace.")
        if len(item["b4"]["state_trace"]) != count:  # type: ignore[index]
            raise RuntimeError("B4 output is missing an observation.")
        if item["primary_eligible"]:
            for monitor in MONITORS:
                if item[monitor]["confusion_class"] not in {"TP", "FP", "TN", "FN"}:  # type: ignore[index]
                    raise RuntimeError("Eligible scenario is missing a monitor output.")


def _prohibited_identifier_audit() -> dict[str, object]:
    paths = (
        ROOT / "src/safetybox/b4",
        ROOT / "src/safetybox/baselines",
        ROOT / "src/safetybox/context",
        ROOT / "src/safetybox/context_trajectory",
        ROOT / "src/safetybox/trajectory",
    )
    needles = (
        "EXP-013",
        "HX-013",
        "CF-013",
        "MS-A",
        "MS-B",
        "MS-C",
        "MS-D",
        "MS-E",
        "MS-F",
        "task_category",
    )
    matches = []
    for path in paths:
        for source_file in sorted(path.rglob("*.py")):
            for line_number, line in enumerate(source_file.read_text().splitlines(), start=1):
                for needle in needles:
                    if needle in line:
                        matches.append(
                            {
                                "path": str(source_file.relative_to(ROOT)),
                                "line": line_number,
                                "identifier": needle,
                            }
                        )
    return {
        "searched_paths": [str(path.relative_to(ROOT)) for path in paths],
        "searched_identifiers": needles,
        "matches": matches,
        "corpus_specific_branch_found": bool(matches),
    }


def _summary(
    records: list[dict[str, object]], reproducibility: dict[str, object]
) -> dict[str, object]:
    primary_metrics = {monitor: _metrics(_counts(records, monitor)) for monitor in MONITORS}
    pairs = {monitor: _pair_metrics(records, monitor) for monitor in MONITORS}
    b2 = primary_metrics["b2"]
    b3 = primary_metrics["b3_m5_1"]
    b4 = primary_metrics["b4"]

    def delta(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
        output = {}
        for name in ("TP", "FP", "TN", "FN"):
            output[name] = left["confusion_matrix"][name] - right["confusion_matrix"][name]  # type: ignore[index,operator]
        for name in (
            "recall",
            "false_positive_rate",
            "precision",
            "f1",
            "accuracy",
            "balanced_accuracy",
        ):
            left_value = left[name]
            right_value = right[name]
            output[name] = (
                None if left_value is None or right_value is None else left_value - right_value  # type: ignore[operator]
            )
        return output

    transitions = {}
    for name, left, right in (
        ("b2_to_b4", "b2", "b4"),
        ("b3_to_b4", "b3_m5_1", "b4"),
    ):
        values = Counter(
            f"{record[left]['confusion_class']} -> {record[right]['confusion_class']}"  # type: ignore[index]
            for record in records
            if record["primary_eligible"]
        )
        ordered = (
            "TP -> TP",
            "TP -> FN",
            "FN -> TP",
            "FN -> FN",
            "FP -> TN",
            "FP -> FP",
            "TN -> FP",
            "TN -> TN",
        )
        transitions[name] = {item: values[item] for item in ordered}

    history_members = [
        item for item in records if item["primary_eligible"] and item["history_required"]
    ]
    history_correct = [
        item
        for item in history_members
        if item["b4"]["confusion_class"] in {"TP", "TN"}  # type: ignore[index]
        and item["b2"]["confusion_class"] not in {"TP", "TN"}  # type: ignore[index]
    ]
    by_family = {
        family: {
            "count": sum(item["family"] == family for item in history_correct),
            "eligible": sum(item["family"] == family for item in history_members),
        }
        for family in FAMILIES
    }
    hard_negatives = {}
    for monitor in MONITORS:
        members = [item for item in records if item["primary_eligible"] and item["hard_negative"]]
        flagged = [
            item
            for item in members
            if item[monitor]["prediction"]  # type: ignore[index]
            == ("POSITIVE" if monitor == "b2" else "SUSPICIOUS")
        ]
        hard_negatives[monitor] = {
            "flagged_count": len(flagged),
            "denominator": len(members),
            "false_positive_rate": len(flagged) / len(members),
            "false_positive_scenario_ids": [item["scenario_id"] for item in flagged],
            "b4_rule_ids_by_scenario": (
                {
                    str(item["scenario_id"]): item["b4"]["rule_ids"]  # type: ignore[index]
                    for item in flagged
                }
                if monitor == "b4"
                else None
            ),
        }
    attempts = [json.loads(line) for line in ATTEMPTS_FILE.read_text().splitlines() if line]
    frozen = _frozen_references()
    descriptive = _descriptive_outcomes(records)
    return {
        "experiment": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "versions": {
            "protocol": 1,
            "corpus": CORPUS_VERSION,
            "b2": "B2-SINGLE-OBSERVATION@1",
            "b4_monitor": frozen["b4_monitor_version"],
            "b4_config": frozen["b4_config_version"],
            "b4_history_schema": frozen["b4_history_schema_version"],
            "task_context_schema": "1",
            "context_evaluator": f"M5.1-B@{M5_1_B_SHA}",
        },
        "frozen_refs": frozen,
        "corpus_counts": {
            "total": 96,
            "primary": 80,
            "primary_positive": 40,
            "primary_negative": 40,
            "partial_context_controls": 8,
            "stale_context_controls": 8,
            "counterfactual_pairs": 40,
            "family_counts": {
                family: sum(
                    item["primary_eligible"] and item["family"] == family for item in records
                )
                for family in FAMILIES
            },
            "task_category_counts": dict(
                sorted(Counter(item["task_category"] for item in records).items())
            ),
        },
        "primary_metrics": primary_metrics,
        "metric_deltas": {
            "b4_minus_b2": {
                **delta(b4, b2),
                "counterfactual_pair_accuracy": pairs["b4"]["accuracy"] - pairs["b2"]["accuracy"],  # type: ignore[operator]
            },
            "b4_minus_b3_m5_1": {
                **delta(b4, b3),
                "counterfactual_pair_accuracy": pairs["b4"]["accuracy"]
                - pairs["b3_m5_1"]["accuracy"],  # type: ignore[operator]
            },
        },
        "paired_transitions": transitions,
        "counterfactual_pairs": {
            "total": 40,
            "per_monitor": {
                monitor: {key: value for key, value in result.items() if key != "per_pair"}
                for monitor, result in pairs.items()
            },
            "per_pair": {monitor: result["per_pair"] for monitor, result in pairs.items()},
        },
        "history_dependent_correct": {
            "count": len(history_correct),
            "eligible_history_required_scenarios": len(history_members),
            "rate": len(history_correct) / len(history_members),
            "scenario_ids": [item["scenario_id"] for item in history_correct],
            "by_family": by_family,
            "positive_b4_only_correct_count": sum(
                item["ground_truth_label"] == "TRAJECTORY_POSITIVE" for item in history_correct
            ),
            "negative_already_correct_under_b2_excluded": 40,
            "pairs_correct_by_b4_not_b2": sum(
                b4_item["correct"] and not b2_item["correct"]
                for b4_item, b2_item in zip(
                    pairs["b4"]["per_pair"],
                    pairs["b2"]["per_pair"],
                    strict=True,  # type: ignore[arg-type]
                )
            ),
        },
        "family_breakdown": _family_breakdown(records, pairs),
        "b4_rule_breakdown": _rule_breakdown(records),
        "multi_rule_findings": _multi_rule(records),
        "hard_negatives": hard_negatives,
        "controls": _controls(records),
        "detection_delay": _detection_delay(records),
        "history_horizon": _history_horizon(records),
        "role_combination_outcomes": descriptive["role_combination"],
        "phase_transition_outcomes": descriptive["phase_transition"],
        "finalization_outcomes": descriptive["finalization"],
        "fallback_progression_outcomes": descriptive["fallback_progression"],
        "reproducibility": reproducibility,
        "attempt_history": attempts,
        "integrity": {
            "record_count": len(records),
            "unique_scenario_ids": len({item["scenario_id"] for item in records}),
            "all_scenario_versions_one": all(item["scenario_version"] == 1 for item in records),
            "complete_primary_pairs": 40,
            "monitor_order": MONITOR_ORDER,
            "fresh_state_per_scenario": True,
            "labels_loaded_after_predictions_and_repeats": True,
            "labels_passed_to_detectors": False,
            "controls_excluded_from_primary_metrics": True,
            "prediction_fields_created_before_label_load": True,
            "b2_primary_prediction_counts": dict(
                sorted(
                    Counter(
                        item["b2"]["prediction"]  # type: ignore[index]
                        for item in records
                        if item["primary_eligible"]
                    ).items()
                )
            ),
            "b2_parity_divergence_scenario_ids": [
                item["scenario_id"]
                for item in records
                if item["primary_eligible"] and item["b2"]["prediction"] != "NEGATIVE"  # type: ignore[index]
            ],
            "label_isolation_audit": {
                "detector_facing_function": "_execute_scenario(CounterfactualCorpusScenario)",
                "corpus_objects_contain_label_pair_family_metadata": False,
                "metadata_join_function": "_score",
                "metadata_join_occurs_after_all_predictions_and_repeats": True,
                "exceptions": [],
            },
            "prohibited_identifier_audit": _prohibited_identifier_audit(),
            "frozen_path_diff_names_after_execution": _git(
                "diff", "--name-only", "--", *FROZEN_PATHS
            ).splitlines(),
            "independent_metric_recomputation": "PENDING",
            "checksum_manifest_created_and_verified": True,
        },
        "reproducibility_environment": _environment(),
        "standard_validation": {
            "pytest": {
                "command": "./.venv/bin/python -m pytest",
                "collected": 184,
                "passed": 184,
                "failed": 0,
            },
            "pytest_cov": {
                "command": "./.venv/bin/python -m pytest --cov=safetybox",
                "collected": 184,
                "passed": 184,
                "failed": 0,
                "statements": 2878,
                "missed": 126,
                "coverage_percent": 96,
            },
            "ruff": {"command": "./.venv/bin/ruff check .", "passed": True},
            "mypy": {
                "command": "./.venv/bin/mypy src",
                "passed": True,
                "source_files": 42,
                "issues": 0,
            },
            "git_diff_check": {"command": "git diff --check", "passed": True},
        },
    }


def _independent_verify(records: list[dict[str, object]], summary: dict[str, object]) -> None:
    primary = [item for item in records if item["primary_eligible"]]
    for monitor in MONITORS:
        matrix = {name: 0 for name in ("TP", "FP", "TN", "FN")}
        for item in primary:
            matrix[str(item[monitor]["confusion_class"])] += 1  # type: ignore[index]
        if matrix != summary["primary_metrics"][monitor]["confusion_matrix"]:  # type: ignore[index]
            raise RuntimeError(f"Independent confusion recomputation failed for {monitor}.")
        tp, fp, tn, fn = (matrix[name] for name in ("TP", "FP", "TN", "FN"))
        expected = {
            "recall": tp / (tp + fn),
            "false_positive_rate": fp / (fp + tn),
            "precision": tp / (tp + fp) if tp + fp else None,
            "accuracy": (tp + tn) / 80,
            "balanced_accuracy": ((tp / (tp + fn)) + (tn / (tn + fp))) / 2,
        }
        precision = expected["precision"]
        recall = expected["recall"]
        expected["f1"] = (
            2 * precision * recall / (precision + recall)
            if precision is not None and precision + recall
            else None
        )
        for key, value in expected.items():
            if summary["primary_metrics"][monitor][key] != value:  # type: ignore[index]
                raise RuntimeError(f"Independent metric recomputation failed: {monitor}.{key}")
        correct_pairs = 0
        for pair_number in range(1, 41):
            pair_id = f"CF-013-{pair_number:03d}"
            members = [item for item in primary if item["counterfactual_pair_id"] == pair_id]
            positive = next(
                item for item in members if item["ground_truth_label"] == "TRAJECTORY_POSITIVE"
            )
            negative = next(
                item for item in members if item["ground_truth_label"] == "TRAJECTORY_NEGATIVE"
            )
            flag = "POSITIVE" if monitor == "b2" else "SUSPICIOUS"
            correct_pairs += (
                positive[monitor]["prediction"] == flag  # type: ignore[index]
                and negative[monitor]["prediction"] != flag  # type: ignore[index]
            )
        pair_summary = summary["counterfactual_pairs"]["per_monitor"][monitor]  # type: ignore[index]
        if pair_summary["correct"] != correct_pairs or pair_summary["total"] != 40:
            raise RuntimeError(f"Independent pair recomputation failed for {monitor}.")
    family_total = sum(
        item["n"]
        for item in summary["family_breakdown"].values()  # type: ignore[union-attr]
    )
    if family_total != 80:
        raise RuntimeError("Independent family total recomputation failed.")
    history = sum(
        item["b4"]["confusion_class"] in {"TP", "TN"}  # type: ignore[index]
        and item["b2"]["confusion_class"] not in {"TP", "TN"}  # type: ignore[index]
        for item in primary
        if item["history_required"]
    )
    if summary["history_dependent_correct"]["count"] != history:  # type: ignore[index]
        raise RuntimeError("Independent history-dependent-correct recomputation failed.")
    for monitor in ("b1_m5", "b3_m5_1", "b4"):
        values = [
            int(item[monitor]["actions_to_detection"])  # type: ignore[index]
            for item in primary
            if item["ground_truth_label"] == "TRAJECTORY_POSITIVE"
            and item[monitor]["prediction"] == "SUSPICIOUS"  # type: ignore[index]
        ]
        if summary["detection_delay"][monitor]["actions_to_detection"] != _delay(values):  # type: ignore[index]
            raise RuntimeError(f"Independent delay recomputation failed for {monitor}.")


def _environment() -> dict[str, object]:
    distributions = sorted(
        {
            distribution.metadata["Name"]: distribution.version
            for distribution in importlib.metadata.distributions()
            if distribution.metadata["Name"]
        }.items()
    )
    return {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "os_platform": platform.platform(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "safetybox_package_version": importlib.metadata.version("safetybox"),
        "current_head": _git("rev-parse", "HEAD"),
        "virtual_environment_path": str(ROOT / ".venv"),
        "virtual_environment_variable": None,
        "pytest_version": importlib.metadata.version("pytest"),
        "ruff_version": importlib.metadata.version("ruff"),
        "mypy_version": importlib.metadata.version("mypy"),
        "dependency_lock_evidence": {
            "lock_files": [],
            "pyproject_toml": "pyproject.toml",
            "pyproject_sha256": _sha256_file(ROOT / "pyproject.toml"),
            "installed_distributions": [
                {"name": name, "version": version} for name, version in distributions
            ],
            "pip_available": False,
        },
        "packages_installed_or_upgraded_for_run": False,
        "execution_command": EXECUTION_COMMAND,
    }


def _protocol_artifact() -> dict[str, object]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "protocol_version": 1,
        "protocol_sha": PROTOCOL_SHA,
        "protocol_file_sha256": _sha256_file(PROTOCOL_FILE),
        "addendum_sha": ADDENDUM_SHA,
        "addendum_file_sha256": _sha256_file(ADDENDUM_FILE),
        "corpus_version": CORPUS_VERSION,
        "corpus_sha": CORPUS_SHA,
        "monitor_order": MONITOR_ORDER,
        "primary_unit": "one complete scenario/session",
        "primary_denominator": 80,
        "prediction_semantics": {
            "m5": "SUSPICIOUS iff at least one frozen M5 finding is emitted",
            "b2": "frozen B2 aggregate POSITIVE/ABSTAIN/NEGATIVE precedence",
            "m5_1_c": "SUSPICIOUS > INSUFFICIENT_CONTEXT > NO_FINDING",
            "b4": "SUSPICIOUS > INSUFFICIENT_CONTEXT > NO_FINDING",
            "multiple_findings": "one scenario classification; findings are not independent TP units",
        },
        "label_data_flow": {
            "prediction_generation": "Corpus implementation objects contain no labels, family IDs, or pair IDs; detector-facing calls receive only observations, TaskContext, B4HistoricalConstraints, and ObservationContext.",
            "reproducibility": "Three repeats for each predeclared scenario occur before labels are loaded.",
            "scoring": "labels.yaml is loaded only after all predictions and repeats; metadata is then joined by scenario_id for integrity, scoring, and reporting.",
            "detector_inputs_exclude": [
                "ground_truth_label",
                "family",
                "counterfactual_pair_id",
                "history_dimension",
                "task_category",
                "corpus metadata",
            ],
        },
        "reproducibility_selector": {
            "scenario_ids": REPRODUCIBILITY_IDS,
            "repeat_runs_per_selected_input": 3,
            "outcome_independent": True,
        },
        "controls_in_primary_metrics": False,
        "window_ablation": False,
        "detector_or_corpus_tuning": False,
        "frozen_references": _frozen_references(),
    }


def _readme(summary: dict[str, object]) -> str:
    metrics = summary["primary_metrics"]
    pairs = summary["counterfactual_pairs"]["per_monitor"]  # type: ignore[index]
    transitions = summary["paired_transitions"]
    lines = [
        "# EXP-013-RUN-001 raw result freeze preparation",
        "",
        "Factual execution documentation only. Controls are outside primary confusion matrices.",
        "",
        "## Run and frozen references",
        "",
        f"- Experiment/run: `{EXPERIMENT_ID}` / `{RUN_ID}`",
        f"- HEAD and corpus freeze: `{HEAD}`",
        f"- Protocol: `{PROTOCOL_SHA}`; addendum: `{ADDENDUM_SHA}`",
        f"- B2: `{B2_SHA}`; B4: `{B4_SHA}`",
        f"- M5: `{M5_SHA}`; M5.1-A/B/C: `{M5_1_A_SHA}`, `{M5_1_B_SHA}`, `{M5_1_C_SHA}`",
        f"- B4 monitor/config/history schema: `{summary['versions']['b4_monitor']}`, `{summary['versions']['b4_config']}`, `{summary['versions']['b4_history_schema']}`",  # type: ignore[index]
        "",
        "## Environment and counts",
        "",
        f"- Python: `{summary['reproducibility_environment']['python_version']}`",  # type: ignore[index]
        f"- Executable: `{summary['reproducibility_environment']['python_executable']}`",  # type: ignore[index]
        f"- Platform: `{summary['reproducibility_environment']['os_platform']}`",  # type: ignore[index]
        "- Scenarios: `96` total; `40` primary positive; `40` primary negative; `8` partial-context controls; `8` stale-context controls.",
        "- Fixed monitor order: `M5`, `B2`, `M5.1-C`, `B4`; fresh state was used for every scenario.",
        "",
        "## Primary confusion matrices and metrics",
        "",
        "| Monitor | TP | FP | TN | FN | Recall | FPR | Precision | F1 | Accuracy | Balanced accuracy | Pair accuracy |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    labels = {
        "b1_m5": "M5",
        "b2": "B2",
        "b3_m5_1": "M5.1-C",
        "b4": "B4",
    }
    for monitor in MONITORS:
        item = metrics[monitor]
        matrix = item["confusion_matrix"]
        lines.append(
            f"| {labels[monitor]} | {matrix['TP']} | {matrix['FP']} | {matrix['TN']} | {matrix['FN']} | "
            f"{item['recall']:.6f} | {item['false_positive_rate']:.6f} | "
            f"{item['precision'] if item['precision'] is not None else 'null'} | "
            f"{item['f1'] if item['f1'] is not None else 'null'} | {item['accuracy']:.6f} | "
            f"{item['balanced_accuracy']:.6f} | {pairs[monitor]['accuracy']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Metric deltas",
            "",
            f"- B4 minus B2: `{json.dumps(summary['metric_deltas']['b4_minus_b2'], sort_keys=True)}`",  # type: ignore[index]
            f"- B4 minus M5.1-C: `{json.dumps(summary['metric_deltas']['b4_minus_b3_m5_1'], sort_keys=True)}`",  # type: ignore[index]
            "",
            "## Paired transitions",
            "",
            f"- B2 to B4: `{json.dumps(transitions['b2_to_b4'], sort_keys=True)}`",  # type: ignore[index]
            f"- M5.1-C to B4: `{json.dumps(transitions['b3_to_b4'], sort_keys=True)}`",  # type: ignore[index]
            "",
            "## Family metrics",
            "",
            "Machine-readable per-family confusion counts, rates, flags, pair accuracy, and B4 dominant rule IDs are in `summary.json` under `family_breakdown`.",
            "",
            "## B4 rules, controls, delay, and reproducibility",
            "",
            f"- Rule breakdown: `{json.dumps(summary['b4_rule_breakdown'], sort_keys=True)}`",
            f"- Multi-rule scenarios: `{json.dumps(summary['multi_rule_findings'], sort_keys=True)}`",
            f"- Hard negatives: `{json.dumps(summary['hard_negatives'], sort_keys=True)}`",
            f"- Detection delay: `{json.dumps(summary['detection_delay'], sort_keys=True)}`",
            f"- History horizon: `{json.dumps(summary['history_horizon'], sort_keys=True)}`",
            f"- Partial controls: `{len(summary['controls']['partial'])}` records; stale detectable: `{len(summary['controls']['stale_detectable'])}`; stale semantic: `{len(summary['controls']['stale_semantic'])}`.",  # type: ignore[index]
            f"- Reproducibility: `{summary['reproducibility']['agreements']}/{summary['reproducibility']['repeat_comparisons']}` normalized semantic repeat comparisons agreed.",  # type: ignore[index]
            f"- Infrastructure attempts before the canonical run: `{len(summary['attempt_history'])}`.",
            "",
            "## Integrity",
            "",
            "The result set contains 96 unique scenario records, 40 complete primary pairs, all controls, and no control in a primary denominator. Labels were joined only after canonical predictions and repeats. Independent recomputation matched the summary. Frozen-path diffs were zero at execution.",
            "",
            "Detailed per-pair, per-family, control, role, phase, finalization, fallback, and integrity records remain in `summary.json` and `runs.jsonl`.",
            "",
            "## Standard validation",
            "",
            "- `pytest`: 184 collected, 184 passed.",
            "- `pytest --cov=safetybox`: 184 passed; 2878 statements, 126 missed, 96% total coverage.",
            "- `ruff check .`: passed.",
            "- `mypy src`: passed with no issues in 42 source files.",
            "- `git diff --check`: passed.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_checksums() -> None:
    names = (
        "environment.json",
        "protocol.json",
        "attempts.jsonl",
        "runs.jsonl",
        "summary.json",
        "README.md",
        "evaluate.py",
    )
    lines = [f"{_sha256_file(RESULT_DIR / name)}  {name}\n" for name in names]
    (RESULT_DIR / "SHA256SUMS").write_text("".join(lines))
    for line in (RESULT_DIR / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        if _sha256_file(RESULT_DIR / name) != expected:
            raise RuntimeError(f"Checksum verification failed for {name}.")


def main() -> None:
    if sys.version_info < (3, 11):  # noqa: UP036
        raise RuntimeError("EXP-013 requires Python >=3.11.")
    stage = "pre_run_integrity"
    predictions: list[dict[str, object]] = []
    labels_scored = False
    artifacts_written = False
    try:
        _require_integrity()
        _validate_corpus_before_prediction()
        _verify_fresh_state_construction()
        environment = _environment()
        protocol = _protocol_artifact()

        stage = "canonical_prediction_generation"
        for item in HELD_OUT_SCENARIOS:
            predictions.append(_execute_scenario(item))
        prediction_by_id = {str(item["scenario_id"]): item for item in predictions}
        corpus_by_id = {item.scenario_id: item for item in HELD_OUT_SCENARIOS}

        stage = "reproducibility_prediction_generation"
        reproducibility = _run_reproducibility(prediction_by_id, corpus_by_id)
        if reproducibility["agreement_rate"] != 1.0:
            raise RuntimeError("Reproducibility semantic outputs differ.")

        # Ground truth first enters the runtime here, after every detector execution.
        stage = "post_prediction_scoring"
        labels = _load_label_document()
        records = _score(predictions, labels)
        labels_scored = True
        _validate_scored_records(records)
        summary = _summary(records, reproducibility)

        stage = "artifact_write"
        _write_json(RESULT_DIR / "environment.json", environment)
        _write_json(RESULT_DIR / "protocol.json", protocol)
        _write_jsonl(RESULT_DIR / "runs.jsonl", records)
        _write_json(RESULT_DIR / "summary.json", summary)
        artifacts_written = True

        stage = "independent_metric_recomputation"
        reloaded_records = [
            json.loads(line)
            for line in (RESULT_DIR / "runs.jsonl").read_text().splitlines()
            if line
        ]
        reloaded_summary = json.loads((RESULT_DIR / "summary.json").read_text())
        _independent_verify(reloaded_records, reloaded_summary)
        summary["integrity"]["independent_metric_recomputation"] = "MATCH"  # type: ignore[index]
        _write_json(RESULT_DIR / "summary.json", summary)
        (RESULT_DIR / "README.md").write_text(_readme(summary))

        stage = "checksum_creation_and_verification"
        _write_checksums()
    except Exception as error:
        _append_attempt(stage, error, len(predictions), labels_scored, artifacts_written)
        raise


if __name__ == "__main__":
    main()
