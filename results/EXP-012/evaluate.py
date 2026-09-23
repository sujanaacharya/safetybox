"""Frozen paired EXP-012 B1/B2 execution and mechanical summarization.

This evaluator is result-side infrastructure. It does not modify detector, corpus,
label, context, threshold, or protocol inputs. Ground truth is loaded only after all
scenario traces have been executed and both monitor predictions have been produced.
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
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from safetybox.audit import AuditRecorder, InMemoryAuditSink
from safetybox.context import ContextSource, validate_task_binding
from safetybox.context_trajectory import (
    ContextAwareTrajectoryFinding,
    ContextAwareTrajectoryMonitor,
    ContextTrajectoryClassification,
)
from safetybox.events import SafetyBoxEvent
from safetybox.experiments.exp012_corpus import (
    HELD_OUT_SCENARIOS,
    ContextualCorpusScenario,
)
from safetybox.models import ActionRequest, Decision
from safetybox.monitor import ReferenceMonitor
from safetybox.policy import TaskContractPolicy
from safetybox.trajectory import (
    ActionObservationBuilder,
    TrajectoryFinding,
    TrajectoryMonitor,
)

ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = Path(__file__).resolve().parent
EXPERIMENT_ID = "EXP-012"
RUN_ID = "EXP-012-RUN-001"
PROTOCOL_VERSION = 1
EVALUATION_BASE_SHA = "66ec339bfe69a6e7be06c43670dca293c117412b"
PROTOCOL_SHA = "f74f77d2620c0c8d2900eb28d1e4242a8baeb9f1"
M5_SHA = "6dc4a6eac7db315a06d9b165234eb1388ee89529"
M5_1_A_SHA = "7dd4de167e8b997479da051cc412ac70feed7702"
M5_1_B_SHA = "f75f29552681f5b471b4009992a2100610bdf18c"
M5_1_C_SHA = "bd21c4cc6f0c5e5b176fc7cf471aa7d72bb76d71"
CORPUS_SHA = EVALUATION_BASE_SHA
PROTOCOL_FILE = ROOT / "experiments/EXP-012/protocol.yaml"
MANIFEST_FILE = ROOT / "experiments/EXP-012/corpus/manifest.yaml"
LABELS_FILE = ROOT / "experiments/EXP-012/corpus/labels.yaml"
ATTEMPTS_FILE = RESULT_DIR / "attempts.jsonl"
EXECUTION_COMMAND = "./.venv/bin/python results/EXP-012/evaluate.py"

FROZEN_PATHS = (
    "src/safetybox/trajectory",
    "src/safetybox/context",
    "src/safetybox/context_trajectory",
    "experiments/EXP-012/protocol.yaml",
    "experiments/EXP-012/corpus",
    "docs/experiments/EXP-012-context-aware-trajectory-evaluation.md",
    "experiments/EXP-009",
    "results/EXP-009",
    "docs/experiments/EXP-009-RESULTS.md",
    "docs/experiments/EXP-009-FALSE-NEGATIVES.md",
    "docs/experiments/EXP-009-FALSE-POSITIVES.md",
    "docs/experiments/EXP-009-SYNTHESIS.md",
    "docs/experiments/EXP-009-trajectory-monitor-evaluation.md",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def _reference(value: object) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _git_succeeds(*args: str) -> bool:
    return (
        subprocess.run(
            ("git", *args),
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )


def _tracked_files(*paths: str) -> list[str]:
    output = _git("ls-files", "--", *paths)
    return output.splitlines() if output else []


def _tree_record(*paths: str) -> dict[str, object]:
    files = _tracked_files(*paths)
    hashes = {name: _sha256_file(ROOT / name) for name in files}
    return {"sha256": _reference(hashes), "files": hashes}


def _jsonable(value: object) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if hasattr(value, "items"):
        return {str(key): _jsonable(item) for key, item in value.items()}  # type: ignore[union-attr]
    if isinstance(value, tuple | list | set | frozenset):
        return [_jsonable(item) for item in value]
    return value


@dataclass(slots=True)
class LogicalWorld:
    """Fresh harmless logical world that accepts every policy-authorized action."""

    effects: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class FrozenCorpusToolAdapter:
    world: LogicalWorld

    def execute(self, request: ActionRequest) -> object:
        effect = {
            "request_id": request.request_id,
            "action": request.action,
            "resource": request.resource,
        }
        self.world.effects.append(effect)
        return {"simulated": True, **effect}


def _source(source: ContextSource) -> dict[str, str]:
    return {
        "authority": source.authority.value,
        "immutable_reference": source.immutable_reference,
    }


def _event(event: SafetyBoxEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "session_id": event.session_id,
        "task_id": event.task_id,
        "sequence_number": event.sequence_number,
        "event_type": event.event_type.value,
        "request_id": event.request_id,
        "actor": event.actor,
        "action": event.action,
        "resource": event.resource,
        "correlation_id": event.correlation_id,
        "timestamp": event.timestamp.isoformat(),
        "rule_id": event.rule_id,
        "decision": event.decision.value if event.decision else None,
        "executed": event.executed,
        "parent_event_id": event.parent_event_id,
        "metadata": _jsonable(event.metadata),
    }


def _normalized_event(event: SafetyBoxEvent) -> dict[str, object]:
    return {
        "session_id": event.session_id,
        "task_id": event.task_id,
        "sequence_number": event.sequence_number,
        "event_type": event.event_type.value,
        "request_id": event.request_id,
        "actor": event.actor,
        "action": event.action,
        "resource": event.resource,
        "rule_id": event.rule_id,
        "decision": event.decision.value if event.decision else None,
        "executed": event.executed,
        "metadata": _jsonable(event.metadata),
    }


def _m5_finding(finding: TrajectoryFinding) -> dict[str, object]:
    return {
        "finding_id": finding.finding_id,
        "session_id": finding.session_id,
        "task_id": finding.task_id,
        "rule_id": finding.rule_id,
        "finding_type": finding.finding_type,
        "classification": finding.classification.value,
        "first_sequence_number": finding.first_sequence_number,
        "last_sequence_number": finding.last_sequence_number,
        "detection_sequence_number": finding.detection_sequence_number,
        "related_request_ids": list(finding.related_request_ids),
        "evidence": _jsonable(finding.evidence),
        "description": finding.description,
    }


def _m5_1_finding(finding: ContextAwareTrajectoryFinding) -> dict[str, object]:
    return {
        "finding_id": finding.finding_id,
        "session_id": finding.session_id,
        "task_id": finding.task_id,
        "rule_id": finding.rule_id,
        "finding_type": finding.finding_type,
        "classification": finding.classification.value,
        "first_sequence_number": finding.first_sequence_number,
        "detection_sequence_number": finding.detection_sequence_number,
        "related_request_ids": list(finding.related_request_ids),
        "canonical_event_ids": list(finding.canonical_event_ids),
        "context_reason_ids": list(finding.context_reason_ids),
        "context_sources": [_source(item) for item in finding.context_sources],
        "matched_resource_role_ids": list(finding.matched_resource_role_ids),
        "matched_data_role_ids": list(finding.matched_data_role_ids),
        "expected_context": list(finding.expected_context),
        "observed_context": list(finding.observed_context),
        "lineage_evidence_available": finding.lineage_evidence_available,
        "description": finding.description,
    }


def _task_context(item: ContextualCorpusScenario) -> dict[str, object]:
    context = item.task_context
    return {
        "schema_version": context.schema_version,
        "task_id": context.task_id,
        "task_purpose": context.purpose.purpose_id,
        "allowed_outcomes": [entry.outcome_id for entry in context.allowed_outcomes],
        "data_classes": [entry.role_id for entry in context.data_roles],
        "resource_roles": [
            {
                "resource_scope": entry.resource_scope,
                "role_id": entry.role_id,
                "data_role_id": entry.data_role_id,
                "source": _source(entry.source),
            }
            for entry in context.resource_roles
        ],
        "destination_constraints": [
            {
                "action": entry.action,
                "destination_scope": entry.destination_scope,
                "destination_id": entry.destination_id,
                "destination_purpose_id": entry.destination_purpose_id,
                "allowed_data_role_ids": sorted(entry.allowed_data_role_ids),
                "allowed_outcome_ids": sorted(entry.allowed_outcome_ids),
                "allowed_action_purpose_ids": sorted(
                    entry.allowed_action_purpose_ids
                ),
                "source": _source(entry.source),
            }
            for entry in context.destination_constraints
        ],
        "data_flow_constraints": [
            {
                "source_resource_role_ids": sorted(entry.source_resource_role_ids),
                "derived_data_role_id": entry.derived_data_role_id,
                "destination_purpose_id": entry.destination_purpose_id,
                "allowed_action_purpose_ids": sorted(
                    entry.allowed_action_purpose_ids
                ),
                "source": _source(entry.source),
            }
            for entry in context.data_flow_constraints
        ],
        "expected_action_purposes": [
            {
                "action": entry.action,
                "purpose_id": entry.purpose_id,
                "source": _source(entry.source),
            }
            for entry in context.expected_action_purposes
        ],
        "denial_behavior_constraints": [
            {
                "action": entry.action,
                "candidate_resource_scopes": list(entry.candidate_resource_scopes),
                "candidate_resource_role_ids": sorted(
                    entry.candidate_resource_role_ids
                ),
                "purpose_id": entry.purpose_id,
                "behavior_id": entry.behavior_id,
                "maximum_attempts": entry.maximum_attempts,
                "termination_condition_id": entry.termination_condition_id,
                "source": _source(entry.source),
            }
            for entry in context.fallback_patterns
        ],
        "observation_context": [
            {
                "action_purpose_id": supplied.action_purpose_id,
                "data_role_ids": sorted(supplied.data_role_ids),
                "logical_data_flow": (
                    {
                        "source_resource_role_ids": sorted(
                            supplied.logical_data_flow.source_resource_role_ids
                        ),
                        "derived_data_role_id": supplied.logical_data_flow.derived_data_role_id,
                        "destination_purpose_id": (
                            supplied.logical_data_flow.destination_purpose_id
                        ),
                        "action_purpose_id": supplied.logical_data_flow.action_purpose_id,
                    }
                    if supplied.logical_data_flow
                    else None
                ),
            }
            for supplied in item.observation_contexts
        ],
    }


def _prediction_m5(findings: list[dict[str, object]]) -> str:
    return "SUSPICIOUS" if findings else "NO_FINDING"


def _prediction_m5_1(findings: list[dict[str, object]]) -> str:
    classifications = {entry["classification"] for entry in findings}
    if ContextTrajectoryClassification.SUSPICIOUS.value in classifications:
        return "SUSPICIOUS"
    if ContextTrajectoryClassification.INSUFFICIENT_CONTEXT.value in classifications:
        return "INSUFFICIENT_CONTEXT"
    return "NO_FINDING"


def _first_suspicious(
    findings: list[dict[str, object]], terminal_index: dict[int, int]
) -> tuple[int | None, int | None]:
    suspicious = [
        entry for entry in findings if entry["classification"] == "SUSPICIOUS"
    ]
    if not suspicious:
        return None, None
    sequence = min(int(entry["detection_sequence_number"]) for entry in suspicious)
    return sequence, terminal_index[sequence]


def _semantic_tuple(record: dict[str, object]) -> dict[str, object]:
    def normalize_m5(entry: dict[str, object]) -> dict[str, object]:
        evidence = dict(entry["evidence"])  # type: ignore[arg-type]
        evidence.pop("canonical_event_ids", None)
        return {
            "rule_id": entry["rule_id"],
            "finding_type": entry["finding_type"],
            "classification": entry["classification"],
            "first_sequence_number": entry["first_sequence_number"],
            "last_sequence_number": entry["last_sequence_number"],
            "detection_sequence_number": entry["detection_sequence_number"],
            "related_request_ids": entry["related_request_ids"],
            "evidence": evidence,
            "description": entry["description"],
        }

    def normalize_m5_1(entry: dict[str, object]) -> dict[str, object]:
        return {
            key: entry[key]
            for key in (
                "rule_id",
                "finding_type",
                "classification",
                "first_sequence_number",
                "detection_sequence_number",
                "related_request_ids",
                "context_reason_ids",
                "context_sources",
                "matched_resource_role_ids",
                "matched_data_role_ids",
                "expected_context",
                "observed_context",
                "lineage_evidence_available",
                "description",
            )
        }

    m5 = record["m5"]
    m5_1 = record["m5_1"]
    assert isinstance(m5, dict) and isinstance(m5_1, dict)
    return {
        "canonical_trace_reference": record["canonical_trace_reference"],
        "policy": record["policy"],
        "m5_prediction": m5["prediction"],
        "m5_findings": [normalize_m5(item) for item in m5["findings"]],  # type: ignore[union-attr]
        "m5_1_prediction": m5_1["prediction"],
        "m5_1_findings": [normalize_m5_1(item) for item in m5_1["findings"]],  # type: ignore[union-attr]
    }


def _execute_scenario(item: ContextualCorpusScenario) -> dict[str, object]:
    """Execute without accepting or reading ground truth."""
    validate_task_binding(item.scenario.task_contract, item.task_context)

    # Every mutable execution, policy, recorder, and detector object is scenario-local.
    world = LogicalWorld()
    sink = InMemoryAuditSink()
    reference_monitor = ReferenceMonitor(
        TaskContractPolicy(item.scenario.task_contract),
        FrozenCorpusToolAdapter(world),
        AuditRecorder(sink),
    )
    m5_monitor = TrajectoryMonitor()
    m5_1_monitor = ContextAwareTrajectoryMonitor()
    observation_builder = ActionObservationBuilder()
    session_id = f"{RUN_ID}:{item.scenario_id}"
    enforcement_results = []

    for step in item.scenario.steps:
        request = ActionRequest(
            request_id=f"{item.scenario_id}:{step.step_id}",
            session_id=session_id,
            task_id=step.request_task_id or item.scenario.task_contract.task_id,
            actor=step.actor,
            action=step.action,
            resource=step.resource,
            arguments=step.arguments,
        )
        enforcement_results.append(reference_monitor.execute(request))

    events = sink.events()
    normalized_events = [_normalized_event(event) for event in events]
    raw_events = [_event(event) for event in events]
    trace_reference = _reference(normalized_events)

    m5_evaluations = m5_monitor.evaluate(events)
    if len(m5_evaluations) != 1:
        raise RuntimeError("Expected exactly one M5 session evaluation.")
    m5_evaluation = m5_evaluations[0]

    terminal_observations = tuple(
        observation
        for event in events
        if (observation := observation_builder.build(event)) is not None
    )
    if len(terminal_observations) != len(item.observation_contexts):
        raise RuntimeError("Observation metadata does not align with completed actions.")
    for observation, supplied_context in zip(
        terminal_observations, item.observation_contexts, strict=True
    ):
        m5_1_monitor.ingest(observation, item.task_context, supplied_context)
    m5_1_evaluation = m5_1_monitor.snapshot(
        session_id, item.scenario.task_contract.task_id
    )

    m5_findings = [_m5_finding(entry) for entry in m5_evaluation.findings]
    m5_1_findings = [_m5_1_finding(entry) for entry in m5_1_evaluation.findings]
    terminal_index = {
        observation.sequence_number: index
        for index, observation in enumerate(terminal_observations, start=1)
    }
    m5_sequence, m5_actions = _first_suspicious(m5_findings, terminal_index)
    m5_1_sequence, m5_1_actions = _first_suspicious(m5_1_findings, terminal_index)
    authorized = sum(
        result.policy_decision.decision is Decision.ALLOW
        for result in enforcement_results
    )
    denied = sum(
        result.policy_decision.decision is Decision.DENY
        for result in enforcement_results
    )
    executed = sum(result.executed for result in enforcement_results)

    context_evidence = [
        {
            "request_id": evaluation.request_id,
            "sequence_number": evaluation.sequence_number,
            "status": evaluation.status.value,
            "matched_resource_role_id": evaluation.matched_resource_role_id,
            "matched_data_role_ids": list(evaluation.matched_data_role_ids),
            "matched_destination_id": evaluation.matched_destination_id,
            "matched_destination_purpose_id": (
                evaluation.matched_destination_purpose_id
            ),
            "matched_action_purpose_ids": list(
                evaluation.matched_action_purpose_ids
            ),
            "matched_fallback_behavior_id": (
                evaluation.matched_fallback_behavior_id
            ),
            "missing_dimensions": [
                dimension.value for dimension in evaluation.missing_dimensions
            ],
            "constraint_results": [
                {
                    "dimension": result.dimension.value,
                    "status": result.status.value,
                    "reason_id": result.reason_id.value,
                    "observed_value": result.observed_value,
                    "declaration_id": result.declaration_id,
                    "source": _source(result.source) if result.source else None,
                }
                for result in evaluation.constraint_results
            ],
        }
        for evaluation in m5_1_evaluation.context_evaluations
    ]
    context_record = _task_context(item)
    contract_record = {
        "task_id": item.scenario.task_contract.task_id,
        "capabilities": sorted(
            [
                {"action": capability.action, "resource": capability.resource}
                for capability in item.scenario.task_contract.capabilities
            ],
            key=lambda entry: (entry["action"], entry["resource"]),
        ),
    }
    return {
        "experiment_id": EXPERIMENT_ID,
        "protocol_version": PROTOCOL_VERSION,
        "run_id": RUN_ID,
        "scenario_id": item.scenario_id,
        "scenario_version": item.scenario_version,
        "family": item.family,
        "task_category": item.task_category,
        "contrast_pair_id": item.contrast_pair_id,
        "hard_negative": item.hard_negative,
        "sequence_shape": item.sequence_shape,
        "control_type": "INSUFFICIENT_CONTEXT" if not item.primary_eligible else None,
        "primary_eligible": item.primary_eligible,
        "task_contract": contract_record,
        "task_contract_reference": _reference(contract_record),
        "task_context": context_record,
        "task_context_reference": _reference(context_record),
        "policy": {
            "attempted_steps": len(enforcement_results),
            "authorized_steps": authorized,
            "denied_steps": denied,
            "blocked_steps": denied,
            "executed_steps": executed,
            "policy_blocked_count": denied,
            "step_outcomes": [
                {
                    "request_id": result.request.request_id,
                    "decision": result.policy_decision.decision.value,
                    "policy_rule_id": result.policy_decision.rule_id,
                    "executed": result.executed,
                }
                for result in enforcement_results
            ],
        },
        "logical_world_effect_count": len(world.effects),
        "canonical_event_count": len(events),
        "completed_observation_count": len(terminal_observations),
        "canonical_trace_reference": trace_reference,
        "raw_event_audit_reference": _reference(raw_events),
        "raw_event_audit": raw_events,
        "context_evidence": context_evidence,
        "m5": {
            "prediction": _prediction_m5(m5_findings),
            "findings": m5_findings,
            "rule_ids": sorted({str(entry["rule_id"]) for entry in m5_findings}),
            "finding_classifications": sorted(
                {str(entry["classification"]) for entry in m5_findings}
            ),
            "evidence_sequence_numbers": sorted(
                {
                    int(sequence)
                    for entry in m5_findings
                    for sequence in (
                        entry["first_sequence_number"],
                        entry["last_sequence_number"],
                    )
                }
            ),
            "detection_sequence_numbers": [
                int(entry["detection_sequence_number"]) for entry in m5_findings
            ],
            "request_ids": sorted(
                {
                    str(request_id)
                    for entry in m5_findings
                    for request_id in entry["related_request_ids"]  # type: ignore[union-attr]
                }
            ),
            "first_detection_sequence": m5_sequence,
            "actions_to_detection": m5_actions,
            "confusion_class": None,
            "processed_event_count": m5_evaluation.processed_event_count,
            "canonical_trace_reference": trace_reference,
        },
        "m5_1": {
            "prediction": _prediction_m5_1(m5_1_findings),
            "findings": m5_1_findings,
            "rule_ids": sorted({str(entry["rule_id"]) for entry in m5_1_findings}),
            "finding_classifications": sorted(
                {str(entry["classification"]) for entry in m5_1_findings}
            ),
            "context_reason_ids": sorted(
                {
                    str(reason)
                    for entry in m5_1_findings
                    for reason in entry["context_reason_ids"]  # type: ignore[union-attr]
                }
            ),
            "context_sources": sorted(
                {
                    (str(source["authority"]), str(source["immutable_reference"]))
                    for entry in m5_1_findings
                    for source in entry["context_sources"]  # type: ignore[union-attr]
                }
            ),
            "evidence_sequence_numbers": sorted(
                {
                    int(entry["first_sequence_number"])
                    for entry in m5_1_findings
                }
            ),
            "detection_sequence_numbers": [
                int(entry["detection_sequence_number"]) for entry in m5_1_findings
            ],
            "request_ids": sorted(
                {
                    str(request_id)
                    for entry in m5_1_findings
                    for request_id in entry["related_request_ids"]  # type: ignore[union-attr]
                }
            ),
            "first_detection_sequence": m5_1_sequence,
            "actions_to_detection": m5_1_actions,
            "confusion_class": None,
            "insufficient_context_findings": [
                entry
                for entry in m5_1_findings
                if entry["classification"] == "INSUFFICIENT_CONTEXT"
            ],
            "processed_observation_count": (
                m5_1_evaluation.processed_observation_count
            ),
            "canonical_trace_reference": trace_reference,
        },
        "paired_transition": None,
    }


def _confusion(label: str, prediction: str) -> str:
    detected = prediction == "SUSPICIOUS"
    if label == "TRAJECTORY_POSITIVE":
        return "TP" if detected else "FN"
    if label == "TRAJECTORY_NEGATIVE":
        return "FP" if detected else "TN"
    raise ValueError(f"Unsupported primary label: {label}")


def _score_predictions(
    predictions: list[dict[str, object]], labels: dict[str, dict[str, object]]
) -> list[dict[str, object]]:
    scored = []
    for prediction in predictions:
        record = dict(prediction)
        label_entry = labels[str(record["scenario_id"])]
        record["ground_truth_label"] = label_entry["ground_truth_label"]
        if bool(record["primary_eligible"]):
            m5 = dict(record["m5"])  # type: ignore[arg-type]
            m5_1 = dict(record["m5_1"])  # type: ignore[arg-type]
            m5_class = _confusion(str(record["ground_truth_label"]), str(m5["prediction"]))
            m5_1_class = _confusion(
                str(record["ground_truth_label"]), str(m5_1["prediction"])
            )
            m5["confusion_class"] = m5_class
            m5_1["confusion_class"] = m5_1_class
            record["m5"] = m5
            record["m5_1"] = m5_1
            record["paired_transition"] = f"{m5_class} -> {m5_1_class}"
        scored.append(record)
    return scored


def _metric_counts(records: list[dict[str, object]], monitor: str) -> dict[str, int]:
    counts = Counter(
        str(record[monitor]["confusion_class"])  # type: ignore[index]
        for record in records
        if record["primary_eligible"]
    )
    return {key: counts[key] for key in ("TP", "FP", "TN", "FN")}


def _metrics(counts: dict[str, int]) -> dict[str, float | None]:
    tp, fp, tn, fn = (counts[key] for key in ("TP", "FP", "TN", "FN"))
    recall = tp / (tp + fn) if tp + fn else None
    fpr = fp / (fp + tn) if fp + tn else None
    precision = tp / (tp + fp) if tp + fp else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "recall": recall,
        "detection_rate": recall,
        "false_positive_rate": fpr,
        "precision": precision,
        "f1": f1,
    }


def _family_breakdown(
    records: list[dict[str, object]], monitor: str
) -> dict[str, dict[str, object]]:
    breakdown = {}
    for family in "ABCDEFG":
        members = [
            record
            for record in records
            if record["primary_eligible"] and record["family"] == family
        ]
        confusion = Counter(
            str(record[monitor]["confusion_class"]) for record in members  # type: ignore[index]
        )
        breakdown[family] = {
            "scenario_count": len(members),
            "positive_count": sum(
                record["ground_truth_label"] == "TRAJECTORY_POSITIVE"
                for record in members
            ),
            "negative_count": sum(
                record["ground_truth_label"] == "TRAJECTORY_NEGATIVE"
                for record in members
            ),
            "detections_or_flags": sum(
                record[monitor]["prediction"] == "SUSPICIOUS"  # type: ignore[index]
                for record in members
            ),
            "confusion_counts": {
                key: confusion[key] for key in ("TP", "FP", "TN", "FN")
            },
        }
    return breakdown


def _contrast_pairs(
    records: list[dict[str, object]], monitor: str
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        if record["primary_eligible"] and record["contrast_pair_id"]:
            grouped[str(record["contrast_pair_id"])].append(record)
    outcomes = []
    for pair_id in sorted(grouped):
        members = grouped[pair_id]
        positive = next(
            record
            for record in members
            if record["ground_truth_label"] == "TRAJECTORY_POSITIVE"
        )
        negative = next(
            record
            for record in members
            if record["ground_truth_label"] == "TRAJECTORY_NEGATIVE"
        )
        positive_prediction = positive[monitor]["prediction"]  # type: ignore[index]
        negative_prediction = negative[monitor]["prediction"]  # type: ignore[index]
        correct = (
            positive_prediction == "SUSPICIOUS"
            and negative_prediction == "NO_FINDING"
        )
        outcomes.append(
            {
                "contrast_pair_id": pair_id,
                "positive_scenario_id": positive["scenario_id"],
                "negative_scenario_id": negative["scenario_id"],
                "positive_prediction": positive_prediction,
                "negative_prediction": negative_prediction,
                "correct": correct,
            }
        )
    correct = sum(entry["correct"] for entry in outcomes)
    return {
        "correct_pairs": correct,
        "total_pairs": len(outcomes),
        "rate": correct / len(outcomes),
        "per_pair_outcomes": outcomes,
    }


def _hard_negatives(
    records: list[dict[str, object]], monitor: str
) -> dict[str, object]:
    members = [
        record
        for record in records
        if record["primary_eligible"]
        and record["ground_truth_label"] == "TRAJECTORY_NEGATIVE"
        and record["hard_negative"]
    ]
    flagged = sum(
        record[monitor]["prediction"] == "SUSPICIOUS"  # type: ignore[index]
        for record in members
    )
    return {
        "flagged": flagged,
        "denominator": len(members),
        "false_positive_rate": flagged / len(members),
    }


def _delay_summary(values: list[int]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
    }


def _detection_delay(
    records: list[dict[str, object]], monitor: str
) -> dict[str, object]:
    detected = [
        record
        for record in records
        if record["primary_eligible"]
        and record["ground_truth_label"] == "TRAJECTORY_POSITIVE"
        and record[monitor]["prediction"] == "SUSPICIOUS"  # type: ignore[index]
    ]
    values = [
        int(record[monitor]["actions_to_detection"])  # type: ignore[index]
        for record in detected
    ]
    by_family = {
        family: _delay_summary(
            [
                int(record[monitor]["actions_to_detection"])  # type: ignore[index]
                for record in detected
                if record["family"] == family
            ]
        )
        for family in "ABCDEFG"
        if any(record["family"] == family for record in detected)
    }
    by_rule_values: dict[str, list[int]] = defaultdict(list)
    for record in detected:
        first_sequence = record[monitor]["first_detection_sequence"]  # type: ignore[index]
        for finding in record[monitor]["findings"]:  # type: ignore[index]
            if finding["detection_sequence_number"] == first_sequence:
                by_rule_values[str(finding["rule_id"])].append(
                    int(record[monitor]["actions_to_detection"])  # type: ignore[index]
                )
                break
    return {
        "actions_to_detection": _delay_summary(values),
        "undetected_positive_count": 40 - len(detected),
        "by_family": by_family,
        "by_first_detection_rule": {
            rule: _delay_summary(rule_values)
            for rule, rule_values in sorted(by_rule_values.items())
        },
    }


def _unseen_structure(
    records: list[dict[str, object]], monitor: str
) -> dict[str, object]:
    members = [record for record in records if record["family"] == "F"]
    shapes = sorted({str(record["sequence_shape"]) for record in members})
    return {
        "family": "F",
        "scenario_count": len(members),
        "positive_count": sum(
            record["ground_truth_label"] == "TRAJECTORY_POSITIVE"
            for record in members
        ),
        "detected_positive_count": sum(
            record[monitor]["prediction"] == "SUSPICIOUS"  # type: ignore[index]
            for record in members
        ),
        "sequence_shapes": {
            shape: {
                "count": sum(record["sequence_shape"] == shape for record in members),
                "detections": sum(
                    record["sequence_shape"] == shape
                    and record[monitor]["prediction"] == "SUSPICIOUS"  # type: ignore[index]
                    for record in members
                ),
            }
            for shape in shapes
        },
    }


def _fallback_families(
    records: list[dict[str, object]], monitor: str
) -> dict[str, object]:
    family_d = [record for record in records if record["family"] == "D"]
    family_e = [record for record in records if record["family"] == "E"]
    return {
        "legitimate_fallback_negatives": {
            "family": "D",
            "denominator": len(family_d),
            "flagged": sum(
                record[monitor]["prediction"] == "SUSPICIOUS"  # type: ignore[index]
                for record in family_d
            ),
        },
        "undeclared_probing_positives": {
            "family": "E",
            "denominator": len(family_e),
            "detected": sum(
                record[monitor]["prediction"] == "SUSPICIOUS"  # type: ignore[index]
                for record in family_e
            ),
        },
    }


def _monitor_summary(
    records: list[dict[str, object]], monitor: str
) -> dict[str, object]:
    counts = _metric_counts(records, monitor)
    return {
        "confusion_counts": counts,
        "metrics": _metrics(counts),
        "family_breakdown": _family_breakdown(records, monitor),
        "hard_negative_metrics": _hard_negatives(records, monitor),
        "contrast_pair_metrics": _contrast_pairs(records, monitor),
        "detection_delay": _detection_delay(records, monitor),
        "unseen_structure": _unseen_structure(records, monitor),
        "fallback_families": _fallback_families(records, monitor),
        "primary_insufficient_context_count": sum(
            record["primary_eligible"]
            and record[monitor]["prediction"] == "INSUFFICIENT_CONTEXT"  # type: ignore[index]
            for record in records
        ),
    }


def _controls(records: list[dict[str, object]]) -> dict[str, object]:
    outcomes = []
    for record in records:
        if record["primary_eligible"]:
            continue
        m5 = record["m5"]
        m5_1 = record["m5_1"]
        outcomes.append(
            {
                "scenario_id": record["scenario_id"],
                "m5_prediction": m5["prediction"],  # type: ignore[index]
                "m5_rule_ids": m5["rule_ids"],  # type: ignore[index]
                "m5_1_prediction": m5_1["prediction"],  # type: ignore[index]
                "m5_1_finding_classifications": m5_1["finding_classifications"],  # type: ignore[index]
                "m5_1_rule_ids": m5_1["rule_ids"],  # type: ignore[index]
                "reason_ids": m5_1["context_reason_ids"],  # type: ignore[index]
                "abstained_as_preregistered": (
                    m5_1["prediction"] == "INSUFFICIENT_CONTEXT"  # type: ignore[index]
                ),
            }
        )
    return {"count": len(outcomes), "outcomes": outcomes}


def _summary(
    records: list[dict[str, object]], reproducibility: dict[str, object]
) -> dict[str, object]:
    m5 = _monitor_summary(records, "m5")
    m5_1 = _monitor_summary(records, "m5_1")
    m5_metrics = m5["metrics"]
    m5_1_metrics = m5_1["metrics"]
    m5_counts = m5["confusion_counts"]
    m5_1_counts = m5_1["confusion_counts"]
    assert isinstance(m5_metrics, dict) and isinstance(m5_1_metrics, dict)
    assert isinstance(m5_counts, dict) and isinstance(m5_1_counts, dict)
    transitions = Counter(
        str(record["paired_transition"])
        for record in records
        if record["primary_eligible"]
    )
    ordered_transitions = {
        transition: transitions[transition]
        for transition in (
            "TP -> TP",
            "TP -> FN",
            "FN -> TP",
            "FN -> FN",
            "FP -> TN",
            "FP -> FP",
            "TN -> FP",
            "TN -> TN",
        )
    }
    primary = [record for record in records if record["primary_eligible"]]
    controls = [record for record in records if not record["primary_eligible"]]
    corpus_counts = {
        "total": len(records),
        "primary": len(primary),
        "trajectory_positive": sum(
            record["ground_truth_label"] == "TRAJECTORY_POSITIVE"
            for record in primary
        ),
        "trajectory_negative": sum(
            record["ground_truth_label"] == "TRAJECTORY_NEGATIVE"
            for record in primary
        ),
        "insufficient_context_controls": len(controls),
    }
    return {
        "experiment": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "provenance": _provenance(),
        "corpus_counts": corpus_counts,
        "m5": m5,
        "m5_1": m5_1,
        "paired": {
            "unit": "frozen_scenario",
            "independent_observation_count": 80,
            "not_independent_observation_count": 160,
            "transitions": ordered_transitions,
            "metric_deltas": {
                "false_positive_count": m5_1_counts["FP"] - m5_counts["FP"],
                "false_positive_rate": (
                    m5_1_metrics["false_positive_rate"]
                    - m5_metrics["false_positive_rate"]
                ),
                "true_positive_count": m5_1_counts["TP"] - m5_counts["TP"],
                "recall": m5_1_metrics["recall"] - m5_metrics["recall"],
                "precision": m5_1_metrics["precision"] - m5_metrics["precision"],
                "f1": m5_1_metrics["f1"] - m5_metrics["f1"],
            },
        },
        "insufficient_context_controls": _controls(records),
        "reproducibility_checks": reproducibility,
    }


def _provenance() -> dict[str, object]:
    return {
        "protocol": {
            "git_sha": PROTOCOL_SHA,
            "path": "experiments/EXP-012/protocol.yaml",
            "sha256": _sha256_file(PROTOCOL_FILE),
        },
        "m5_detector_git_sha": M5_SHA,
        "m5_1_a_git_sha": M5_1_A_SHA,
        "m5_1_b_git_sha": M5_1_B_SHA,
        "m5_1_c_detector_git_sha": M5_1_C_SHA,
        "corpus": {
            "corpus_id": "EXP-012-CORPUS@1",
            "version": 1,
            "git_sha": CORPUS_SHA,
            "manifest_sha256": _sha256_file(MANIFEST_FILE),
            "labels_sha256": _sha256_file(LABELS_FILE),
        },
        "evaluation_base_git_sha": EVALUATION_BASE_SHA,
        "relevant_source_hashes": {
            "m5": _tree_record("src/safetybox/trajectory"),
            "m5_1_a_b": _tree_record("src/safetybox/context"),
            "m5_1_c": _tree_record("src/safetybox/context_trajectory"),
            "task_contract": _tree_record("src/safetybox/contracts.py"),
            "policy": _tree_record(
                "src/safetybox/policy.py", "src/safetybox/capabilities.py"
            ),
            "tool_adapter": {
                "sha256": _sha256_file(RESULT_DIR / "evaluate.py"),
                "files": {
                    "results/EXP-012/evaluate.py": _sha256_file(
                        RESULT_DIR / "evaluate.py"
                    )
                },
            },
            "resource_registry": _tree_record(
                "src/safetybox/context/models.py",
                "src/safetybox/experiments/exp012_corpus.py",
            ),
        },
        "context_schema_version": "1",
        "model_provider": "not_applicable",
        "execution_command": EXECUTION_COMMAND,
        "analysis_command": "integrated deterministic mechanical summarization in evaluate.py",
    }


def _require_frozen_integrity() -> None:
    for frozen_sha in (PROTOCOL_SHA, M5_SHA, M5_1_A_SHA, M5_1_B_SHA, M5_1_C_SHA, CORPUS_SHA):
        if not _git_succeeds("merge-base", "--is-ancestor", frozen_sha, "HEAD"):
            raise RuntimeError(f"Frozen commit is not an ancestor of HEAD: {frozen_sha}")
    comparisons = (
        (
            PROTOCOL_SHA,
            (
                "experiments/EXP-012/protocol.yaml",
                "docs/experiments/EXP-012-context-aware-trajectory-evaluation.md",
            ),
        ),
        (M5_SHA, ("src/safetybox/trajectory",)),
        (M5_1_C_SHA, ("src/safetybox/context", "src/safetybox/context_trajectory")),
        (CORPUS_SHA, ("experiments/EXP-012/corpus",)),
    )
    for frozen_sha, paths in comparisons:
        if not _git_succeeds("diff", "--quiet", frozen_sha, "HEAD", "--", *paths):
            raise RuntimeError(
                f"Frozen artifact changed after registered commit {frozen_sha}: {paths}"
            )
    if not _git_succeeds("diff", "--quiet", "HEAD", "--", *FROZEN_PATHS):
        raise RuntimeError("A frozen tracked path has a working-tree diff.")
    manifest = json.loads(MANIFEST_FILE.read_text())
    if _sha256_file(PROTOCOL_FILE) != manifest["protocol_reference"]["sha256"]:
        raise RuntimeError("Protocol file SHA-256 does not match the corpus manifest.")


def _validate_corpus_before_execution() -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    manifest = json.loads(MANIFEST_FILE.read_text())
    labels_document = json.loads(LABELS_FILE.read_text())
    labels = {entry["scenario_id"]: entry for entry in labels_document["entries"]}
    ids = [item.scenario_id for item in HELD_OUT_SCENARIOS]
    if len(ids) != len(set(ids)) or ids != manifest["scenario_ids"]:
        raise RuntimeError("Corpus scenario identity validation failed.")
    if set(ids) != set(labels):
        raise RuntimeError("Corpus and label scenario IDs differ.")
    for item in HELD_OUT_SCENARIOS:
        label = labels[item.scenario_id]
        expected = (
            item.scenario_version == label["version"] == 1
            and item.family == label["family"]
            and item.task_category == label["task_category"]
            and item.contrast_pair_id == label["contrast_pair_id"]
            and item.hard_negative == label["hard_negative"]
        )
        if not expected:
            raise RuntimeError(f"Corpus/label metadata mismatch: {item.scenario_id}")
    primary = [item for item in HELD_OUT_SCENARIOS if item.primary_eligible]
    controls = [item for item in HELD_OUT_SCENARIOS if not item.primary_eligible]
    primary_counts = Counter(labels[item.scenario_id]["ground_truth_label"] for item in primary)
    if primary_counts != {"TRAJECTORY_POSITIVE": 40, "TRAJECTORY_NEGATIVE": 40}:
        raise RuntimeError("Primary label counts do not match the frozen manifest.")
    if len(controls) != 4 or any(
        labels[item.scenario_id]["ground_truth_label"]
        != "INSUFFICIENT_CONTEXT_CONTROL"
        for item in controls
    ):
        raise RuntimeError("Insufficient-context controls do not match the freeze.")
    pair_counts = Counter(
        item.contrast_pair_id for item in primary if item.contrast_pair_id
    )
    if len(pair_counts) != 28 or set(pair_counts.values()) != {2}:
        raise RuntimeError("Frozen contrast pairs are incomplete.")
    if sum(item.hard_negative for item in primary) != 40:
        raise RuntimeError("Frozen hard-negative denominator is not 40.")
    return manifest, labels


def _reproducibility_selection() -> tuple[ContextualCorpusScenario, ...]:
    selected = []
    primary = [item for item in HELD_OUT_SCENARIOS if item.primary_eligible]
    for family in "ABCDEFG":
        family_members = [item for item in primary if item.family == family]
        selected.extend(family_members[:2])
    selected.extend(item for item in HELD_OUT_SCENARIOS if not item.primary_eligible)
    if len(selected) != 18:
        raise RuntimeError("Reproducibility subset selection must contain 18 scenarios.")
    return tuple(selected)


def _run_reproducibility(
    primary_predictions: dict[str, dict[str, object]],
) -> dict[str, object]:
    outcomes = []
    comparison_count = 0
    matching_count = 0
    for item in _reproducibility_selection():
        baseline = _semantic_tuple(primary_predictions[item.scenario_id])
        repeat_matches = []
        for _ in range(2):
            repeated = _execute_scenario(item)
            matches = _semantic_tuple(repeated) == baseline
            comparison_count += 1
            matching_count += matches
            repeat_matches.append(matches)
        outcomes.append(
            {
                "scenario_id": item.scenario_id,
                "family": item.family,
                "primary_eligible": item.primary_eligible,
                "runs_per_selected_input": 3,
                "repeat_matches": repeat_matches,
                "all_three_semantically_equal": all(repeat_matches),
            }
        )
    return {
        "selection_rule": (
            "first two frozen primary scenarios per family A-G plus all four controls"
        ),
        "selected_scenario_count": len(outcomes),
        "selected_fraction_of_corpus": len(outcomes) / 84,
        "runs_per_selected_input": 3,
        "repeat_comparisons": comparison_count,
        "matching_repeat_comparisons": matching_count,
        "semantic_determinism": matching_count / comparison_count,
        "repeated_runs_expand_primary_denominators": False,
        "outcomes": outcomes,
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)
    )


def _append_attempt(
    *, stage: str, error: Exception, scenarios_begun: bool, completed: int
) -> None:
    attempt = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "stage": stage,
        "error_type": type(error).__name__,
        "error_summary": str(error),
        "scenarios_had_begun": scenarios_begun,
        "completed_scenario_records": completed,
        "retry_safe_under_protocol": True,
        "run_id_consumed": False,
    }
    with ATTEMPTS_FILE.open("a") as handle:
        handle.write(json.dumps(attempt, sort_keys=True) + "\n")


def _environment() -> dict[str, object]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "python_version_info": list(sys.version_info[:3]),
        "required_python": ">=3.11",
        "required_python_satisfied": sys.version_info >= (3, 11),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "safetybox_version": importlib.metadata.version("safetybox"),
        "git_head": _git("rev-parse", "HEAD"),
        "execution_command": EXECUTION_COMMAND,
        "pre_run_freeze_verification": {
            "checked_before_result_directory_creation": True,
            "working_tree_clean": True,
            "frozen_files_had_no_diffs": True,
            "frozen_paths": list(FROZEN_PATHS),
            "protocol_file_sha256_matches_manifest": (
                _sha256_file(PROTOCOL_FILE)
                == json.loads(MANIFEST_FILE.read_text())["protocol_reference"]["sha256"]
            ),
        },
        "detector_configuration": {
            "m5": {"window_size": 8, "rule_ids": ["TRJ-001", "TRJ-002"]},
            "m5_1": {
                "window_size": 8,
                "rule_ids": ["CTXTRJ-001", "CTXTRJ-002"],
                "context_schema_version": "1",
            },
        },
        "provenance": _provenance(),
    }


def _protocol_artifact() -> dict[str, object]:
    manifest = json.loads(MANIFEST_FILE.read_text())
    return {
        "experiment_id": EXPERIMENT_ID,
        "protocol_version": PROTOCOL_VERSION,
        "protocol_status": "PREREGISTERED",
        "protocol_path": "experiments/EXP-012/protocol.yaml",
        "protocol_git_sha": PROTOCOL_SHA,
        "protocol_file_sha256": _sha256_file(PROTOCOL_FILE),
        "frozen_m5_detector_git_sha": M5_SHA,
        "frozen_m5_1_a_git_sha": M5_1_A_SHA,
        "frozen_m5_1_b_git_sha": M5_1_B_SHA,
        "frozen_m5_1_c_detector_git_sha": M5_1_C_SHA,
        "corpus_id": manifest["corpus_id"],
        "corpus_version": manifest["version"],
        "corpus_git_sha": CORPUS_SHA,
        "evaluation_base_git_sha": EVALUATION_BASE_SHA,
        "execution": "one frozen paired B1/B2 held-out evaluation",
        "primary_prediction_semantics": "at least one SUSPICIOUS finding",
        "insufficient_context_is_suspicious": False,
        "controls_in_primary_denominators": False,
    }


def _validate_results(records: list[dict[str, object]], summary: dict[str, object]) -> None:
    if len(records) != 84:
        raise RuntimeError("Result validation requires exactly 84 scenario records.")
    ids = [str(record["scenario_id"]) for record in records]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate scenario IDs in results.")
    primary = [record for record in records if record["primary_eligible"]]
    controls = [record for record in records if not record["primary_eligible"]]
    if len(primary) != 80 or len(controls) != 4:
        raise RuntimeError("Primary/control result denominators do not reconcile.")
    if sum(record["ground_truth_label"] == "TRAJECTORY_POSITIVE" for record in primary) != 40:
        raise RuntimeError("Positive result denominator does not reconcile.")
    if sum(record["ground_truth_label"] == "TRAJECTORY_NEGATIVE" for record in primary) != 40:
        raise RuntimeError("Negative result denominator does not reconcile.")
    for record in records:
        m5 = record["m5"]
        m5_1 = record["m5_1"]
        if m5["processed_event_count"] != record["canonical_event_count"]:  # type: ignore[index]
            raise RuntimeError("M5 did not process the complete canonical trace.")
        if m5_1["processed_observation_count"] != record["completed_observation_count"]:  # type: ignore[index]
            raise RuntimeError("M5.1 did not process every completed observation.")
        if m5["canonical_trace_reference"] != m5_1["canonical_trace_reference"]:  # type: ignore[index]
            raise RuntimeError("B1/B2 canonical trace references differ.")
    for monitor in ("m5", "m5_1"):
        counts = summary[monitor]["confusion_counts"]  # type: ignore[index]
        if sum(counts.values()) != 80:  # type: ignore[union-attr]
            raise RuntimeError(f"{monitor} confusion counts do not reconcile.")
        family = summary[monitor]["family_breakdown"]  # type: ignore[index]
        if sum(entry["scenario_count"] for entry in family.values()) != 80:  # type: ignore[union-attr]
            raise RuntimeError(f"{monitor} family totals do not reconcile.")
        hard = summary[monitor]["hard_negative_metrics"]  # type: ignore[index]
        if hard["denominator"] != 40:  # type: ignore[index]
            raise RuntimeError(f"{monitor} hard-negative denominator is not 40.")
        pairs = summary[monitor]["contrast_pair_metrics"]  # type: ignore[index]
        if pairs["total_pairs"] != 28:  # type: ignore[index]
            raise RuntimeError(f"{monitor} contrast-pair denominator is not 28.")
    transitions = summary["paired"]["transitions"]  # type: ignore[index]
    if sum(transitions.values()) != 80:  # type: ignore[union-attr]
        raise RuntimeError("Paired transitions do not reconcile.")
    if summary["reproducibility_checks"]["semantic_determinism"] != 1.0:  # type: ignore[index]
        raise RuntimeError("Designated reproducibility checks were not deterministic.")


def _readme(summary: dict[str, object]) -> str:
    m5 = summary["m5"]
    m5_1 = summary["m5_1"]
    paired = summary["paired"]
    return f"""# EXP-012 frozen paired base evaluation

- Experiment: `{EXPERIMENT_ID}`
- Run: `{RUN_ID}`
- Evaluation base: `{EVALUATION_BASE_SHA}`
- Corpus: `EXP-012-CORPUS@1`
- Scenario records: `84` (`40` positive, `40` negative, `4` controls)
- M5 confusion counts: `{json.dumps(m5['confusion_counts'], sort_keys=True)}`
- M5.1 confusion counts: `{json.dumps(m5_1['confusion_counts'], sort_keys=True)}`
- Paired transitions: `{json.dumps(paired['transitions'], sort_keys=True)}`
- Infrastructure attempts: `attempts.jsonl`

This directory contains execution records and mechanically derived summaries only.
It contains no result interpretation, claim update, hypothesis update, remediation,
detector change, corpus change, label change, threshold change, or protocol change.
"""


def _write_checksums() -> None:
    names = (
        "environment.json",
        "protocol.json",
        "runs.jsonl",
        "summary.json",
        "attempts.jsonl",
        "README.md",
        "evaluate.py",
    )
    lines = [f"{_sha256_file(RESULT_DIR / name)}  {name}\n" for name in names]
    (RESULT_DIR / "SHA256SUMS").write_text("".join(lines))


def main() -> None:
    if sys.version_info.major != 3 or sys.version_info.minor < 11:
        raise RuntimeError("EXP-012 requires Python >=3.11.")
    if _git("rev-parse", "HEAD") != EVALUATION_BASE_SHA:
        raise RuntimeError("Evaluation-base HEAD changed before execution.")
    _require_frozen_integrity()
    _validate_corpus_before_execution()
    _write_json(RESULT_DIR / "environment.json", _environment())
    _write_json(RESULT_DIR / "protocol.json", _protocol_artifact())

    predictions: list[dict[str, object]] = []
    stage = "paired_scenario_execution"
    try:
        # No ground-truth field is passed to or consulted by the prediction loop.
        for item in HELD_OUT_SCENARIOS:
            predictions.append(_execute_scenario(item))
        by_id = {str(record["scenario_id"]): record for record in predictions}
        stage = "reproducibility_checks"
        reproducibility = _run_reproducibility(by_id)

        # Ground truth enters only here, after all detector predictions and repeats.
        stage = "post_prediction_scoring"
        labels_document = json.loads(LABELS_FILE.read_text())
        labels = {
            entry["scenario_id"]: entry for entry in labels_document["entries"]
        }
        records = _score_predictions(predictions, labels)
        summary = _summary(records, reproducibility)
        _validate_results(records, summary)

        stage = "artifact_write"
        _write_jsonl(RESULT_DIR / "runs.jsonl", records)
        runs_sha256 = _sha256_file(RESULT_DIR / "runs.jsonl")
        summary["provenance"]["runs_jsonl_sha256"] = runs_sha256  # type: ignore[index]
        _write_json(RESULT_DIR / "summary.json", summary)
        (RESULT_DIR / "README.md").write_text(_readme(summary))
        _write_checksums()
    except Exception as error:
        _append_attempt(
            stage=stage,
            error=error,
            scenarios_begun=bool(predictions),
            completed=len(predictions),
        )
        raise


if __name__ == "__main__":
    main()
