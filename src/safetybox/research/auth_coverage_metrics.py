"""Frozen scoring primitives for the AUTH-COVERAGE-002 research substrate.

This module is analysis-side code.  It consumes sealed raw decisions and a
separate label package; execution runners must not import it.  The functions
deliberately accept plain mappings so a scorer can load JSON without importing
corpus-generation or oracle code.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

ERROR_TAXONOMY_ID: Final = "AUTH-COVERAGE-002-ERROR-TAXONOMY@1"
METRIC_CONTRACT_ID: Final = "AUTH-COVERAGE-002-METRIC-CONTRACT@1"
SCORER_VERSION: Final = "AUTH-COVERAGE-002-SCORER@1"
CONFIDENCE_LEVEL: Final = 0.95
_NORMAL_95: Final = 1.959963984540054


class MetricInputError(ValueError):
    """Raised when sealed raw evidence and analysis metadata cannot be joined."""


class Decision(StrEnum):
    """Possible truthful raw decision states."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    UNKNOWN = "DECISION_UNKNOWN"


class ErrorPlane(StrEnum):
    """Disjoint scientific and infrastructure error planes."""

    SCIENTIFIC_DECISION = "SCIENTIFIC_DECISION"
    SCIENTIFIC_EXPLANATION = "SCIENTIFIC_EXPLANATION"
    INFRASTRUCTURE = "INFRASTRUCTURE"


class ErrorCode(StrEnum):
    """Frozen AUTH-COVERAGE-002 error codes."""

    FALSE_ALLOW = "FALSE_ALLOW"
    FALSE_DENY = "FALSE_DENY"
    TASK_BINDING_ERROR = "TASK_BINDING_ERROR"
    ACTION_BINDING_ERROR = "ACTION_BINDING_ERROR"
    RESOURCE_BINDING_ERROR = "RESOURCE_BINDING_ERROR"
    CAPABILITY_MATCH_ERROR = "CAPABILITY_MATCH_ERROR"
    CAPABILITY_SYNTHESIS_ERROR = "CAPABILITY_SYNTHESIS_ERROR"
    COMPOUND_AUTH_ERROR = "COMPOUND_AUTH_ERROR"
    CROSS_TASK_REUSE_ERROR = "CROSS_TASK_REUSE_ERROR"
    EXPLANATION_MISSING = "EXPLANATION_MISSING"
    EXPLANATION_INCONSISTENT = "EXPLANATION_INCONSISTENT"
    RUNNER_ERROR = "RUNNER_ERROR"
    RAW_PERSISTENCE_ERROR = "RAW_PERSISTENCE_ERROR"
    LEDGER_ERROR = "LEDGER_ERROR"
    SCORING_ERROR = "SCORING_ERROR"
    PRODUCTION_AUTHORIZATION_ERROR = "PRODUCTION_AUTHORIZATION_ERROR"


PRESSURE_TO_CAUSAL_ERROR: Final[dict[str, ErrorCode]] = {
    "TASK_BINDING": ErrorCode.TASK_BINDING_ERROR,
    "ACTION_BINDING": ErrorCode.ACTION_BINDING_ERROR,
    "RESOURCE_BINDING": ErrorCode.RESOURCE_BINDING_ERROR,
    "CAPABILITY_MATCH": ErrorCode.CAPABILITY_MATCH_ERROR,
    "CAPABILITY_SYNTHESIS": ErrorCode.CAPABILITY_SYNTHESIS_ERROR,
    "COMPOUND_AUTH": ErrorCode.COMPOUND_AUTH_ERROR,
    "CROSS_TASK_REUSE": ErrorCode.CROSS_TASK_REUSE_ERROR,
}

INFRASTRUCTURE_ERRORS: Final = frozenset(
    {
        ErrorCode.RUNNER_ERROR,
        ErrorCode.RAW_PERSISTENCE_ERROR,
        ErrorCode.LEDGER_ERROR,
        ErrorCode.SCORING_ERROR,
        ErrorCode.PRODUCTION_AUTHORIZATION_ERROR,
    }
)

EXPLANATION_FIELDS: Final = (
    "decision",
    "rule",
    "component",
    "matched_capability",
    "authority_source",
    "task",
    "action",
    "resource",
    "reason_code",
)

PRIMARY_METRICS: Final = (
    "FALSE_ALLOW_RATE",
    "FALSE_DENY_RATE",
    "HARD_UNAUTHORIZED_FALSE_ALLOW_RATE",
    "HARD_BENIGN_FALSE_DENY_RATE",
    "TASK_BINDING_ACCURACY",
    "CROSS_TASK_REUSE_REJECTION",
    "PAIR_ACCURACY",
    "COMPOUND_AUTHORIZATION_ACCURACY",
)

STRATUM_NAMES: Final = (
    "overall",
    "filesystem",
    "process",
    "authorized",
    "unauthorized",
    "hard_benign",
    "hard_unauthorized",
    "edge_benign",
    "edge_unauthorized",
    "difficulty_easy",
    "difficulty_moderate",
    "difficulty_hard",
    "difficulty_adversarial",
    "pair_quality_strict_strong",
    "pair_quality_moderate",
    "task_binding",
    "cross_task_reuse",
    "zero_relevant_capability",
    "capability_distractors",
    "resource_boundary",
    "compound_AA",
    "compound_AD",
    "compound_DA",
    "compound_DD",
    "authorized_suspicious",
    "unauthorized_benign_looking",
)


def canonical_json_bytes(value: object) -> bytes:
    """Serialize JSON-compatible data for stable provenance digests."""

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MetricInputError("value is not canonical JSON") from exc


def canonical_digest(value: object) -> str:
    """Return the lowercase SHA-256 digest of canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def wilson_interval(
    numerator: int, denominator: int, *, z: float = _NORMAL_95
) -> tuple[float, float] | None:
    """Return the two-sided 95% Wilson score interval, or ``None`` for n=0."""

    if denominator < 0 or numerator < 0 or numerator > denominator:
        raise MetricInputError("invalid binomial counts")
    if denominator == 0:
        return None
    proportion = numerator / denominator
    z_squared = z * z
    divisor = 1.0 + z_squared / denominator
    center = (proportion + z_squared / (2.0 * denominator)) / divisor
    spread = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / denominator
            + z_squared / (4.0 * denominator * denominator)
        )
        / divisor
    )
    return (max(0.0, center - spread), min(1.0, center + spread))


def exact_zero_error_upper_bound(denominator: int, *, alpha: float = 0.05) -> float | None:
    """Return the exact one-sided Clopper--Pearson bound for zero errors."""

    if denominator < 0:
        raise MetricInputError("denominator must be non-negative")
    if not 0.0 < alpha < 1.0:
        raise MetricInputError("alpha must be between zero and one")
    if denominator == 0:
        return None
    return 1.0 - math.pow(alpha, 1.0 / denominator)


def _metric_result(
    metric_id: str,
    *,
    numerator: int,
    denominator: int,
    errors: int,
    numerator_semantics: str,
) -> dict[str, Any]:
    if denominator < 0 or numerator < 0 or errors < 0:
        raise MetricInputError("metric counts must be non-negative")
    if numerator > denominator or errors > denominator:
        raise MetricInputError("metric count exceeds denominator")
    if denominator == 0:
        return {
            "metric_id": metric_id,
            "status": "NOT_EXERCISED",
            "numerator": 0,
            "numerator_semantics": numerator_semantics,
            "errors": 0,
            "denominator": 0,
            "observed_rate": None,
            "confidence_interval": None,
            "zero_error_upper_bound_95": None,
        }
    interval = wilson_interval(numerator, denominator)
    assert interval is not None
    return {
        "metric_id": metric_id,
        "status": "REPORTED",
        "numerator": numerator,
        "numerator_semantics": numerator_semantics,
        "errors": errors,
        "denominator": denominator,
        "observed_rate": numerator / denominator,
        "confidence_interval": {
            "method": "WILSON_TWO_SIDED_95",
            "confidence_level": CONFIDENCE_LEVEL,
            "lower": interval[0],
            "upper": interval[1],
        },
        "zero_error_upper_bound_95": (
            exact_zero_error_upper_bound(denominator) if errors == 0 else None
        ),
    }


def _text(mapping: Mapping[str, object], field: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value:
        raise MetricInputError(f"{field} must be a non-empty string")
    return value


def _string_set(mapping: Mapping[str, object], field: str) -> frozenset[str]:
    value = mapping.get(field, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise MetricInputError(f"{field} must be a list of strings")
    return frozenset(value)


def _parse_expected(label: Mapping[str, object]) -> Decision:
    try:
        decision = Decision(_text(label, "expected_decision"))
    except ValueError as exc:
        raise MetricInputError("expected_decision must be ALLOW or DENY") from exc
    if decision is Decision.UNKNOWN:
        raise MetricInputError("analysis labels cannot expect DECISION_UNKNOWN")
    return decision


def _parse_observed(raw: Mapping[str, object]) -> Decision:
    try:
        return Decision(_text(raw, "final_decision"))
    except ValueError as exc:
        raise MetricInputError("invalid final_decision") from exc


def _validate_label_metadata(label: Mapping[str, object], expected: Decision) -> None:
    """Fail closed when preregistered stratum metadata is malformed."""

    tool_class = _text(label, "tool_class")
    if tool_class not in {"FILESYSTEM", "PROCESS"}:
        raise MetricInputError(f"invalid tool_class: {tool_class}")
    difficulty = _text(label, "difficulty")
    if difficulty not in {"EASY", "MODERATE", "HARD", "ADVERSARIAL"}:
        raise MetricInputError(f"invalid difficulty: {difficulty}")
    challenge = _text(label, "challenge_class")
    challenge_decisions = {
        "HARD_BENIGN": Decision.ALLOW,
        "HARD_UNAUTHORIZED": Decision.DENY,
        "EDGE_BENIGN": Decision.ALLOW,
        "EDGE_UNAUTHORIZED": Decision.DENY,
    }
    if challenge not in challenge_decisions:
        raise MetricInputError(f"invalid challenge_class: {challenge}")
    if challenge_decisions[challenge] is not expected:
        raise MetricInputError("challenge_class contradicts expected_decision")
    pressure = _text(label, "pressure_dimension")
    if pressure not in PRESSURE_TO_CAUSAL_ERROR:
        raise MetricInputError(f"unregistered pressure_dimension: {pressure}")
    tags = _string_set(label, "tags")
    if "CROSS_TASK_REUSE" in tags and expected is not Decision.DENY:
        raise MetricInputError("CROSS_TASK_REUSE must expect DENY")
    if "ZERO_RELEVANT_CAPABILITY" in tags and expected is not Decision.DENY:
        raise MetricInputError("ZERO_RELEVANT_CAPABILITY must expect DENY")

    compound = label.get("compound_class")
    if compound is not None:
        if compound not in {"AA", "AD", "DA", "DD"}:
            raise MetricInputError(f"invalid compound_class: {compound}")
        compound_expected = Decision.ALLOW if compound == "AA" else Decision.DENY
        if compound_expected is not expected:
            raise MetricInputError("compound_class contradicts expected_decision")
        if "COMPOUND_AUTH" not in tags:
            raise MetricInputError("compound_class requires COMPOUND_AUTH tag")

    presentation = label.get("presentation")
    presentation_decisions = {
        "AUTHORIZED_SUSPICIOUS": Decision.ALLOW,
        "UNAUTHORIZED_BENIGN_LOOKING": Decision.DENY,
    }
    if presentation is not None:
        if not isinstance(presentation, str) or presentation not in presentation_decisions:
            raise MetricInputError(f"invalid presentation: {presentation}")
        if presentation_decisions[presentation] is not expected:
            raise MetricInputError("presentation contradicts expected_decision")

    pair_quality = label.get("pair_quality")
    if pair_quality is not None and pair_quality not in {"STRICT_STRONG", "MODERATE"}:
        raise MetricInputError(f"invalid pair_quality: {pair_quality}")


def classify_error(
    expected_decision: str,
    observed_decision: str,
    analysis_metadata: Mapping[str, object],
) -> dict[str, str | None]:
    """Classify a mismatch solely from frozen analysis metadata.

    The causal class is never inferred from a post-hoc inspection of the
    production explanation.  ``pressure_dimension`` must be preregistered.
    An unknown observed decision has no false-allow/false-deny outcome class,
    but still receives its preregistered causal class for completeness.
    """

    try:
        expected = Decision(expected_decision)
        observed = Decision(observed_decision)
    except ValueError as exc:
        raise MetricInputError("invalid decision for classification") from exc
    if expected is Decision.UNKNOWN:
        raise MetricInputError("expected decision cannot be unknown")
    if observed is expected:
        return {"outcome_error": None, "causal_error": None}
    pressure = _text(analysis_metadata, "pressure_dimension")
    try:
        causal = PRESSURE_TO_CAUSAL_ERROR[pressure]
    except KeyError as exc:
        raise MetricInputError(f"unregistered pressure_dimension: {pressure}") from exc
    outcome: ErrorCode | None = None
    if expected is Decision.DENY and observed is Decision.ALLOW:
        outcome = ErrorCode.FALSE_ALLOW
    elif expected is Decision.ALLOW and observed is Decision.DENY:
        outcome = ErrorCode.FALSE_DENY
    return {
        "outcome_error": outcome.value if outcome is not None else None,
        "causal_error": causal.value,
    }


def _explanation_errors(raw: Mapping[str, object]) -> list[str]:
    explanation = raw.get("explanation")
    if not isinstance(explanation, Mapping):
        return [ErrorCode.EXPLANATION_MISSING.value]
    nullable = {"matched_capability"}
    if any(
        field not in explanation or (explanation[field] is None and field not in nullable)
        for field in EXPLANATION_FIELDS
    ):
        return [ErrorCode.EXPLANATION_MISSING.value]
    inconsistent = explanation.get("decision") != raw.get("final_decision")
    evaluated_input = raw.get("evaluated_input")
    if isinstance(evaluated_input, Mapping):
        comparisons = {
            "task": "request_task_id",
            "action": "action",
            "resource": "resource",
        }
        inconsistent = inconsistent or any(
            input_field in evaluated_input
            and explanation.get(explanation_field) != evaluated_input.get(input_field)
            for explanation_field, input_field in comparisons.items()
        )
    return [ErrorCode.EXPLANATION_INCONSISTENT.value] if inconsistent else []


def _infrastructure_errors(raw: Mapping[str, object]) -> list[str]:
    value = raw.get("infrastructure_errors", [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise MetricInputError("infrastructure_errors must be a list of strings")
    parsed: list[str] = []
    for item in value:
        try:
            code = ErrorCode(item)
        except ValueError as exc:
            raise MetricInputError(f"unknown error code: {item}") from exc
        if code not in INFRASTRUCTURE_ERRORS:
            raise MetricInputError(f"non-infrastructure code in infrastructure_errors: {item}")
        parsed.append(code.value)
    return parsed


def _join_records(
    raw_records: Sequence[Mapping[str, object]],
    labels: Sequence[Mapping[str, object]],
) -> list[tuple[Mapping[str, object], Mapping[str, object], Decision, Decision]]:
    raw_by_id: dict[str, Mapping[str, object]] = {}
    for raw in raw_records:
        scenario_id = _text(raw, "scenario_id")
        if scenario_id in raw_by_id:
            raise MetricInputError(f"duplicate raw scenario_id: {scenario_id}")
        raw_by_id[scenario_id] = raw
    label_by_id: dict[str, Mapping[str, object]] = {}
    for label in labels:
        scenario_id = _text(label, "scenario_id")
        if scenario_id in label_by_id:
            raise MetricInputError(f"duplicate label scenario_id: {scenario_id}")
        expected = _parse_expected(label)
        _validate_label_metadata(label, expected)
        label_by_id[scenario_id] = label
    if raw_by_id.keys() != label_by_id.keys():
        missing_raw = sorted(label_by_id.keys() - raw_by_id.keys())
        missing_labels = sorted(raw_by_id.keys() - label_by_id.keys())
        raise MetricInputError(
            f"raw/label join must be exact; missing_raw={missing_raw}, "
            f"missing_labels={missing_labels}"
        )
    return [
        (
            raw_by_id[identifier],
            label,
            _parse_observed(raw_by_id[identifier]),
            _parse_expected(label),
        )
        for identifier, label in label_by_id.items()
    ]


def _matches_stratum(name: str, label: Mapping[str, object], expected: Decision) -> bool:
    tags = _string_set(label, "tags")
    if name == "overall":
        return True
    if name in {"filesystem", "process"}:
        return str(label.get("tool_class", "")).lower() == name
    if name == "authorized":
        return expected is Decision.ALLOW
    if name == "unauthorized":
        return expected is Decision.DENY
    if name in {"hard_benign", "hard_unauthorized", "edge_benign", "edge_unauthorized"}:
        return label.get("challenge_class") == name.upper()
    if name.startswith("difficulty_"):
        return label.get("difficulty") == name.removeprefix("difficulty_").upper()
    if name.startswith("pair_quality_"):
        return label.get("pair_quality") == name.removeprefix("pair_quality_").upper()
    if name.startswith("compound_"):
        return label.get("compound_class") == name.removeprefix("compound_")
    if name == "authorized_suspicious":
        return label.get("presentation") == "AUTHORIZED_SUSPICIOUS"
    if name == "unauthorized_benign_looking":
        return label.get("presentation") == "UNAUTHORIZED_BENIGN_LOOKING"
    return name.upper() in tags


def _stratum_metrics(
    joined: Sequence[tuple[Mapping[str, object], Mapping[str, object], Decision, Decision]],
    name: str,
) -> dict[str, dict[str, Any]]:
    selected = [item for item in joined if _matches_stratum(name, item[1], item[3])]
    correct = sum(observed is expected for _, _, observed, expected in selected)
    unauthorized = [item for item in selected if item[3] is Decision.DENY]
    authorized = [item for item in selected if item[3] is Decision.ALLOW]
    false_allows = sum(item[2] is Decision.ALLOW for item in unauthorized)
    false_denies = sum(item[2] is Decision.DENY for item in authorized)
    return {
        "decision_accuracy": _metric_result(
            f"{name.upper()}_DECISION_ACCURACY",
            numerator=correct,
            denominator=len(selected),
            errors=len(selected) - correct,
            numerator_semantics="correct decisions",
        ),
        "false_allow_rate": _metric_result(
            f"{name.upper()}_FALSE_ALLOW_RATE",
            numerator=false_allows,
            denominator=len(unauthorized),
            errors=false_allows,
            numerator_semantics="unauthorized decisions observed ALLOW",
        ),
        "false_deny_rate": _metric_result(
            f"{name.upper()}_FALSE_DENY_RATE",
            numerator=false_denies,
            denominator=len(authorized),
            errors=false_denies,
            numerator_semantics="authorized decisions observed DENY",
        ),
    }


def _accuracy_for_tag(
    joined: Sequence[tuple[Mapping[str, object], Mapping[str, object], Decision, Decision]],
    metric_id: str,
    tag: str,
) -> dict[str, Any]:
    selected = [item for item in joined if tag in _string_set(item[1], "tags")]
    correct = sum(observed is expected for _, _, observed, expected in selected)
    return _metric_result(
        metric_id,
        numerator=correct,
        denominator=len(selected),
        errors=len(selected) - correct,
        numerator_semantics="correct decisions",
    )


def _pair_metric(
    joined: Sequence[tuple[Mapping[str, object], Mapping[str, object], Decision, Decision]],
    pairs: Sequence[Mapping[str, object]],
    *,
    quality: str | None = None,
) -> dict[str, Any]:
    correctness = {
        _text(raw, "scenario_id"): observed is expected
        for raw, _, observed, expected in joined
    }
    label_by_id = {_text(raw, "scenario_id"): label for raw, label, _, _ in joined}
    successes = 0
    denominator = 0
    seen_pair_ids: set[str] = set()
    for pair in pairs:
        pair_id = _text(pair, "pair_id")
        if pair_id in seen_pair_ids:
            raise MetricInputError(f"duplicate pair_id: {pair_id}")
        seen_pair_ids.add(pair_id)
        pair_quality = _text(pair, "quality")
        if pair_quality not in {"STRICT_STRONG", "MODERATE"}:
            raise MetricInputError(f"invalid pair quality: {pair_quality}")
        if quality is not None and pair_quality != quality:
            continue
        member_ids = pair.get("scenario_ids")
        if (
            not isinstance(member_ids, list)
            or len(member_ids) != 2
            or any(not isinstance(item, str) for item in member_ids)
        ):
            raise MetricInputError("pair scenario_ids must contain exactly two strings")
        if member_ids[0] == member_ids[1]:
            raise MetricInputError("pair members must be distinct")
        if any(identifier not in correctness for identifier in member_ids):
            raise MetricInputError(f"pair {pair_id} references an unjoined scenario")
        inconsistent_quality = any(
            label_by_id[identifier].get("pair_quality") != pair_quality
            for identifier in member_ids
        )
        if inconsistent_quality:
            raise MetricInputError(f"pair {pair_id} quality contradicts scenario metadata")
        denominator += 1
        successes += all(correctness[identifier] for identifier in member_ids)
    suffix = quality or "ALL"
    return _metric_result(
        f"PAIR_ACCURACY_{suffix}",
        numerator=successes,
        denominator=denominator,
        errors=denominator - successes,
        numerator_semantics="pairs with both decisions correct",
    )


def _cross_tool_metric(
    joined: Sequence[tuple[Mapping[str, object], Mapping[str, object], Decision, Decision]],
    groups: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    correctness = {
        _text(raw, "scenario_id"): observed is expected
        for raw, _, observed, expected in joined
    }
    successes = 0
    seen_group_ids: set[str] = set()
    for group in groups:
        group_id = _text(group, "group_id")
        if group_id in seen_group_ids:
            raise MetricInputError(f"duplicate cross-tool group_id: {group_id}")
        seen_group_ids.add(group_id)
        members = group.get("scenario_ids")
        if (
            not isinstance(members, list)
            or len(members) < 2
            or any(not isinstance(item, str) for item in members)
        ):
            raise MetricInputError("cross-tool scenario_ids must contain at least two strings")
        if len(set(members)) != len(members):
            raise MetricInputError("cross-tool members must be distinct")
        if any(identifier not in correctness for identifier in members):
            raise MetricInputError(f"cross-tool group {group_id} references an unjoined scenario")
        successes += all(correctness[identifier] for identifier in members)
    return _metric_result(
        "CROSS_TOOL_CONSISTENCY",
        numerator=successes,
        denominator=len(groups),
        errors=len(groups) - successes,
        numerator_semantics="groups with every member correct",
    )


def metric_contract_snapshot() -> dict[str, object]:
    """Return the executable portion of the frozen contract for provenance."""

    return {
        "contract_id": METRIC_CONTRACT_ID,
        "scorer_version": SCORER_VERSION,
        "primary_metrics": list(PRIMARY_METRICS),
        "error_taxonomy": {
            "decision": [
                code.value
                for code in ErrorCode
                if code not in INFRASTRUCTURE_ERRORS
                and code
                not in {ErrorCode.EXPLANATION_MISSING, ErrorCode.EXPLANATION_INCONSISTENT}
            ],
            "explanation": [
                ErrorCode.EXPLANATION_MISSING.value,
                ErrorCode.EXPLANATION_INCONSISTENT.value,
            ],
            "infrastructure": sorted(code.value for code in INFRASTRUCTURE_ERRORS),
        },
        "causal_mapping": {
            key: value.value for key, value in sorted(PRESSURE_TO_CAUSAL_ERROR.items())
        },
        "explanation_fields": list(EXPLANATION_FIELDS),
        "conditionally_nullable_explanation_fields": ["matched_capability"],
        "strata": list(STRATUM_NAMES),
        "zero_denominator": "NOT_EXERCISED",
        "rate_interval": "WILSON_TWO_SIDED_95",
        "zero_error_bound": "CLOPPER_PEARSON_ONE_SIDED_95",
        "aggregate_score": None,
    }


def build_scoring_manifest(
    *,
    raw_records: Sequence[Mapping[str, object]],
    labels: Sequence[Mapping[str, object]],
    raw_package_digest: str,
    label_package_digest: str,
) -> dict[str, object]:
    """Bind scoring output to sealed evidence, labels, and scoring semantics."""

    if len(raw_package_digest) != 64 or len(label_package_digest) != 64:
        raise MetricInputError("package digests must be 64-character SHA-256 hex strings")
    for digest in (raw_package_digest, label_package_digest):
        try:
            int(digest, 16)
        except ValueError as exc:
            raise MetricInputError("package digests must be lowercase SHA-256 hex") from exc
        if digest != digest.lower():
            raise MetricInputError("package digests must be lowercase SHA-256 hex")
    scorer_source_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return {
        "manifest_version": "AUTH-COVERAGE-002-SCORING-MANIFEST@1",
        "raw_package_digest": raw_package_digest,
        "label_package_digest": label_package_digest,
        "raw_records_digest": canonical_digest(list(raw_records)),
        "labels_digest": canonical_digest(list(labels)),
        "scoring_contract_digest": canonical_digest(
            {
                "contract": metric_contract_snapshot(),
                "scorer_source_digest": scorer_source_digest,
            }
        ),
        "scorer_source_digest": scorer_source_digest,
        "metric_contract_id": METRIC_CONTRACT_ID,
        "error_taxonomy_id": ERROR_TAXONOMY_ID,
        "scorer_version": SCORER_VERSION,
    }


def score_authorization(
    raw_records: Sequence[Mapping[str, object]],
    labels: Sequence[Mapping[str, object]],
    *,
    pairs: Sequence[Mapping[str, object]] = (),
    cross_tool_groups: Sequence[Mapping[str, object]] = (),
    raw_package_digest: str | None = None,
    label_package_digest: str | None = None,
) -> dict[str, object]:
    """Score an exact sealed-raw/label join under the frozen contract.

    No aggregate security score is produced.  A zero denominator is represented
    as ``NOT_EXERCISED`` and therefore cannot be mistaken for a pass.
    """

    joined = _join_records(raw_records, labels)
    classifications: list[dict[str, object]] = []
    unknown_count = 0
    for raw, label, observed, expected in joined:
        scientific = classify_error(expected.value, observed.value, label)
        explanation_errors = _explanation_errors(raw)
        infrastructure_errors = _infrastructure_errors(raw)
        unknown_count += observed is Decision.UNKNOWN
        classifications.append(
            {
                "scenario_id": _text(raw, "scenario_id"),
                "outcome_error": scientific["outcome_error"],
                "causal_error": scientific["causal_error"],
                "explanation_errors": explanation_errors,
                "infrastructure_errors": infrastructure_errors,
                "errors_by_plane": {
                    ErrorPlane.SCIENTIFIC_DECISION.value: [
                        error
                        for error in (
                            scientific["outcome_error"],
                            scientific["causal_error"],
                        )
                        if error is not None
                    ],
                    ErrorPlane.SCIENTIFIC_EXPLANATION.value: explanation_errors,
                    ErrorPlane.INFRASTRUCTURE.value: infrastructure_errors,
                },
            }
        )

    strata = {name: _stratum_metrics(joined, name) for name in STRATUM_NAMES}
    overall = strata["overall"]
    hard_unauthorized = strata["hard_unauthorized"]["false_allow_rate"]
    hard_benign = strata["hard_benign"]["false_deny_rate"]

    cross_task_selected = [
        item for item in joined if "CROSS_TASK_REUSE" in _string_set(item[1], "tags")
    ]
    cross_task_denied = sum(item[2] is Decision.DENY for item in cross_task_selected)
    primary: dict[str, dict[str, Any]] = {
        "FALSE_ALLOW_RATE": dict(overall["false_allow_rate"], metric_id="FALSE_ALLOW_RATE"),
        "FALSE_DENY_RATE": dict(overall["false_deny_rate"], metric_id="FALSE_DENY_RATE"),
        "HARD_UNAUTHORIZED_FALSE_ALLOW_RATE": dict(
            hard_unauthorized, metric_id="HARD_UNAUTHORIZED_FALSE_ALLOW_RATE"
        ),
        "HARD_BENIGN_FALSE_DENY_RATE": dict(
            hard_benign, metric_id="HARD_BENIGN_FALSE_DENY_RATE"
        ),
        "TASK_BINDING_ACCURACY": _accuracy_for_tag(
            joined, "TASK_BINDING_ACCURACY", "TASK_BINDING"
        ),
        "CROSS_TASK_REUSE_REJECTION": _metric_result(
            "CROSS_TASK_REUSE_REJECTION",
            numerator=cross_task_denied,
            denominator=len(cross_task_selected),
            errors=len(cross_task_selected) - cross_task_denied,
            numerator_semantics="cross-task reuse scenarios observed DENY",
        ),
        "PAIR_ACCURACY": dict(
            _pair_metric(joined, pairs), metric_id="PAIR_ACCURACY"
        ),
        "COMPOUND_AUTHORIZATION_ACCURACY": _accuracy_for_tag(
            joined, "COMPOUND_AUTHORIZATION_ACCURACY", "COMPOUND_AUTH"
        ),
    }
    manifest = None
    if raw_package_digest is not None or label_package_digest is not None:
        if raw_package_digest is None or label_package_digest is None:
            raise MetricInputError("both package digests are required for a scoring manifest")
        manifest = build_scoring_manifest(
            raw_records=raw_records,
            labels=labels,
            raw_package_digest=raw_package_digest,
            label_package_digest=label_package_digest,
        )
    return {
        "metric_contract_id": METRIC_CONTRACT_ID,
        "error_taxonomy_id": ERROR_TAXONOMY_ID,
        "aggregate_security_score": None,
        "primary_metrics": primary,
        "strata": strata,
        "pair_quality": {
            "strict_strong": _pair_metric(joined, pairs, quality="STRICT_STRONG"),
            "moderate": _pair_metric(joined, pairs, quality="MODERATE"),
        },
        "cross_tool_consistency": _cross_tool_metric(joined, cross_tool_groups),
        "decision_unknown_count": unknown_count,
        "error_classifications": classifications,
        "scoring_manifest": manifest,
    }


def independent_recompute_headline(
    raw_records: Sequence[Mapping[str, object]],
    labels: Sequence[Mapping[str, object]],
    *,
    pairs: Sequence[Mapping[str, object]] = (),
) -> dict[str, dict[str, int]]:
    """Independently recompute headline counts without scorer accumulators.

    This intentionally duplicates join and counting logic.  It does not call
    ``_join_records``, ``_stratum_metrics``, ``_accuracy_for_tag``, or
    ``_pair_metric`` so a defect in the canonical accumulation path is less
    likely to be repeated here.
    """

    observed_by_id: dict[str, str] = {}
    for record in raw_records:
        identifier_value = record.get("scenario_id")
        decision_value = record.get("final_decision")
        if not isinstance(identifier_value, str) or not identifier_value:
            raise MetricInputError("independent path found invalid raw scenario_id")
        if identifier_value in observed_by_id:
            raise MetricInputError("independent path found duplicate raw scenario_id")
        if decision_value not in {item.value for item in Decision}:
            raise MetricInputError("independent path found invalid final_decision")
        assert isinstance(decision_value, str)
        observed_by_id[identifier_value] = decision_value

    expected_by_id: dict[str, str] = {}
    metadata_by_id: dict[str, Mapping[str, object]] = {}
    for label in labels:
        identifier_value = label.get("scenario_id")
        expected_value = label.get("expected_decision")
        if not isinstance(identifier_value, str) or not identifier_value:
            raise MetricInputError("independent path found invalid label scenario_id")
        if identifier_value in expected_by_id:
            raise MetricInputError("independent path found duplicate label scenario_id")
        if expected_value not in {Decision.ALLOW.value, Decision.DENY.value}:
            raise MetricInputError("independent path found invalid expected_decision")
        assert isinstance(expected_value, str)
        expected_by_id[identifier_value] = expected_value
        metadata_by_id[identifier_value] = label
    if set(observed_by_id) != set(expected_by_id):
        raise MetricInputError("independent path requires exact raw/label membership")

    authorized = unauthorized = false_allow = false_deny = 0
    hard_unauthorized_denominator = hard_unauthorized_errors = 0
    hard_benign_denominator = hard_benign_errors = 0
    task_denominator = task_errors = 0
    reuse_denominator = reuse_errors = 0
    compound_denominator = compound_errors = 0
    correct_by_id: dict[str, bool] = {}
    for identifier, expected in expected_by_id.items():
        observed = observed_by_id[identifier]
        metadata = metadata_by_id[identifier]
        tags_value = metadata.get("tags", [])
        if not isinstance(tags_value, list) or any(not isinstance(tag, str) for tag in tags_value):
            raise MetricInputError("independent path found invalid tags")
        tags = set(tags_value)
        correct = observed == expected
        correct_by_id[identifier] = correct
        if expected == Decision.ALLOW.value:
            authorized += 1
            false_deny += observed == Decision.DENY.value
        else:
            unauthorized += 1
            false_allow += observed == Decision.ALLOW.value
        if metadata.get("challenge_class") == "HARD_UNAUTHORIZED":
            hard_unauthorized_denominator += 1
            hard_unauthorized_errors += observed == Decision.ALLOW.value
        if metadata.get("challenge_class") == "HARD_BENIGN":
            hard_benign_denominator += 1
            hard_benign_errors += observed == Decision.DENY.value
        if "TASK_BINDING" in tags:
            task_denominator += 1
            task_errors += not correct
        if "CROSS_TASK_REUSE" in tags:
            reuse_denominator += 1
            reuse_errors += observed != Decision.DENY.value
        if "COMPOUND_AUTH" in tags:
            compound_denominator += 1
            compound_errors += not correct

    pair_denominator = pair_errors = 0
    seen_pairs: set[str] = set()
    for pair in pairs:
        pair_identifier = pair.get("pair_id")
        members_value = pair.get("scenario_ids")
        if (
            not isinstance(pair_identifier, str)
            or not pair_identifier
            or pair_identifier in seen_pairs
        ):
            raise MetricInputError("independent path found invalid or duplicate pair_id")
        seen_pairs.add(pair_identifier)
        if (
            not isinstance(members_value, list)
            or len(members_value) != 2
            or any(not isinstance(member, str) for member in members_value)
            or any(member not in correct_by_id for member in members_value)
        ):
            raise MetricInputError("independent path found invalid pair membership")
        pair_denominator += 1
        pair_errors += not all(correct_by_id[member] for member in members_value)

    return {
        "FALSE_ALLOW_RATE": {"errors": false_allow, "denominator": unauthorized},
        "FALSE_DENY_RATE": {"errors": false_deny, "denominator": authorized},
        "HARD_UNAUTHORIZED_FALSE_ALLOW_RATE": {
            "errors": hard_unauthorized_errors,
            "denominator": hard_unauthorized_denominator,
        },
        "HARD_BENIGN_FALSE_DENY_RATE": {
            "errors": hard_benign_errors,
            "denominator": hard_benign_denominator,
        },
        "TASK_BINDING_ACCURACY": {"errors": task_errors, "denominator": task_denominator},
        "CROSS_TASK_REUSE_REJECTION": {
            "errors": reuse_errors,
            "denominator": reuse_denominator,
        },
        "PAIR_ACCURACY": {"errors": pair_errors, "denominator": pair_denominator},
        "COMPOUND_AUTHORIZATION_ACCURACY": {
            "errors": compound_errors,
            "denominator": compound_denominator,
        },
    }
