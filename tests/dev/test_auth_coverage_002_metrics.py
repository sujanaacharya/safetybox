"""Synthetic-only tests for the frozen AUTH-COVERAGE-002 scoring contract."""

from __future__ import annotations

import math
from collections.abc import Mapping

import pytest

from safetybox.research.auth_coverage_metrics import (
    ERROR_TAXONOMY_ID,
    METRIC_CONTRACT_ID,
    ErrorCode,
    MetricInputError,
    canonical_digest,
    classify_error,
    exact_zero_error_upper_bound,
    independent_recompute_headline,
    metric_contract_snapshot,
    score_authorization,
    wilson_interval,
)


def _label(
    scenario_id: str,
    expected: str,
    *,
    tool: str,
    difficulty: str,
    challenge: str,
    pressure: str,
    tags: list[str] | None = None,
    compound: str | None = None,
    presentation: str | None = None,
    pair_quality: str | None = None,
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "expected_decision": expected,
        "tool_class": tool,
        "difficulty": difficulty,
        "challenge_class": challenge,
        "pressure_dimension": pressure,
        "tags": tags or [],
        "compound_class": compound,
        "presentation": presentation,
        "pair_quality": pair_quality,
    }


def _raw(
    scenario_id: str,
    observed: str,
    *,
    task: str = "task-dev",
    infrastructure_errors: list[str] | None = None,
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "final_decision": observed,
        "evaluated_input": {
            "request_task_id": task,
            "action": "filesystem.read",
            "resource": "/synthetic/dev",
        },
        "explanation": {
            "decision": observed,
            "rule": "DEV_RULE",
            "component": "filesystem",
            "matched_capability": "dev-capability",
            "authority_source": "dev-contract",
            "task": task,
            "action": "filesystem.read",
            "resource": "/synthetic/dev",
            "reason_code": "DEV_REASON",
        },
        "infrastructure_errors": infrastructure_errors or [],
    }


def _fixture() -> tuple[
    list[Mapping[str, object]],
    list[Mapping[str, object]],
    list[Mapping[str, object]],
    list[Mapping[str, object]],
]:
    labels: list[Mapping[str, object]] = [
        _label(
            "dev-random-a1",
            "ALLOW",
            tool="FILESYSTEM",
            difficulty="EASY",
            challenge="HARD_BENIGN",
            pressure="TASK_BINDING",
            tags=["TASK_BINDING", "CAPABILITY_DISTRACTORS", "COMPOUND_AUTH"],
            compound="AA",
            presentation="AUTHORIZED_SUSPICIOUS",
            pair_quality="STRICT_STRONG",
        ),
        _label(
            "dev-random-b2",
            "DENY",
            tool="PROCESS",
            difficulty="MODERATE",
            challenge="HARD_UNAUTHORIZED",
            pressure="CROSS_TASK_REUSE",
            tags=["CROSS_TASK_REUSE", "ZERO_RELEVANT_CAPABILITY", "COMPOUND_AUTH"],
            compound="DD",
            presentation="UNAUTHORIZED_BENIGN_LOOKING",
            pair_quality="STRICT_STRONG",
        ),
        _label(
            "dev-random-c3",
            "ALLOW",
            tool="PROCESS",
            difficulty="HARD",
            challenge="EDGE_BENIGN",
            pressure="CAPABILITY_SYNTHESIS",
            tags=["CAPABILITY_SYNTHESIS"],
            pair_quality="MODERATE",
        ),
        _label(
            "dev-random-d4",
            "DENY",
            tool="FILESYSTEM",
            difficulty="ADVERSARIAL",
            challenge="EDGE_UNAUTHORIZED",
            pressure="RESOURCE_BINDING",
            tags=["RESOURCE_BOUNDARY", "COMPOUND_AUTH"],
            compound="DA",
            pair_quality="MODERATE",
        ),
        _label(
            "dev-random-e5",
            "DENY",
            tool="PROCESS",
            difficulty="HARD",
            challenge="HARD_UNAUTHORIZED",
            pressure="COMPOUND_AUTH",
            tags=["COMPOUND_AUTH"],
            compound="AD",
        ),
    ]
    raw: list[Mapping[str, object]] = [
        _raw("dev-random-a1", "ALLOW"),
        _raw("dev-random-b2", "ALLOW"),  # false allow
        _raw("dev-random-c3", "DENY"),  # false deny
        _raw("dev-random-d4", "DENY"),
        _raw("dev-random-e5", "DENY"),
    ]
    pairs: list[Mapping[str, object]] = [
        {
            "pair_id": "dev-pair-1",
            "scenario_ids": ["dev-random-a1", "dev-random-b2"],
            "quality": "STRICT_STRONG",
        },
        {
            "pair_id": "dev-pair-2",
            "scenario_ids": ["dev-random-c3", "dev-random-d4"],
            "quality": "MODERATE",
        },
    ]
    groups: list[Mapping[str, object]] = [
        {
            "group_id": "dev-cross-tool-1",
            "scenario_ids": ["dev-random-a1", "dev-random-d4"],
        }
    ]
    return raw, labels, pairs, groups


def test_error_taxonomy_is_deterministic_and_planes_remain_distinct() -> None:
    metadata = {"pressure_dimension": "CROSS_TASK_REUSE"}
    classification = classify_error("DENY", "ALLOW", metadata)
    assert classification == {
        "outcome_error": ErrorCode.FALSE_ALLOW.value,
        "causal_error": ErrorCode.CROSS_TASK_REUSE_ERROR.value,
    }
    # Post-hoc explanation text cannot change causal attribution.
    altered_metadata = {**metadata, "production_explanation": "resource mismatch"}
    assert classify_error("DENY", "ALLOW", altered_metadata) == classification
    assert classify_error("ALLOW", "DECISION_UNKNOWN", metadata) == {
        "outcome_error": None,
        "causal_error": ErrorCode.CROSS_TASK_REUSE_ERROR.value,
    }
    with pytest.raises(MetricInputError, match="unregistered pressure_dimension"):
        classify_error("DENY", "ALLOW", {"pressure_dimension": "POST_HOC_GUESS"})


def test_all_primary_metrics_and_requested_strata_execute_without_aggregate() -> None:
    raw, labels, pairs, groups = _fixture()
    scored = score_authorization(raw, labels, pairs=pairs, cross_tool_groups=groups)
    assert scored["metric_contract_id"] == METRIC_CONTRACT_ID
    assert scored["error_taxonomy_id"] == ERROR_TAXONOMY_ID
    assert scored["aggregate_security_score"] is None
    primary = scored["primary_metrics"]
    assert isinstance(primary, dict)
    assert set(primary) == {
        "FALSE_ALLOW_RATE",
        "FALSE_DENY_RATE",
        "HARD_UNAUTHORIZED_FALSE_ALLOW_RATE",
        "HARD_BENIGN_FALSE_DENY_RATE",
        "TASK_BINDING_ACCURACY",
        "CROSS_TASK_REUSE_REJECTION",
        "PAIR_ACCURACY",
        "COMPOUND_AUTHORIZATION_ACCURACY",
    }
    assert primary["FALSE_ALLOW_RATE"]["errors"] == 1
    assert primary["FALSE_ALLOW_RATE"]["denominator"] == 3
    assert primary["FALSE_DENY_RATE"]["errors"] == 1
    assert primary["FALSE_DENY_RATE"]["denominator"] == 2
    assert primary["TASK_BINDING_ACCURACY"]["observed_rate"] == 1.0
    assert primary["CROSS_TASK_REUSE_REJECTION"]["observed_rate"] == 0.0
    assert primary["PAIR_ACCURACY"]["observed_rate"] == 0.0
    assert primary["COMPOUND_AUTHORIZATION_ACCURACY"]["observed_rate"] == 0.75

    strata = scored["strata"]
    assert isinstance(strata, dict)
    assert set(strata) == set(metric_contract_snapshot()["strata"])
    for name in (
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
    ):
        assert strata[name]["decision_accuracy"]["status"] == "REPORTED"
    assert scored["pair_quality"]["strict_strong"]["denominator"] == 1
    assert scored["pair_quality"]["moderate"]["denominator"] == 1
    assert scored["cross_tool_consistency"]["observed_rate"] == 1.0


def test_zero_denominator_is_not_exercised_and_never_pass() -> None:
    raw = [_raw("dev-only", "ALLOW")]
    labels = [
        _label(
            "dev-only",
            "ALLOW",
            tool="FILESYSTEM",
            difficulty="EASY",
            challenge="HARD_BENIGN",
            pressure="CAPABILITY_MATCH",
        )
    ]
    scored = score_authorization(raw, labels)
    false_allow = scored["primary_metrics"]["FALSE_ALLOW_RATE"]
    assert false_allow == {
        "metric_id": "FALSE_ALLOW_RATE",
        "status": "NOT_EXERCISED",
        "numerator": 0,
        "numerator_semantics": "unauthorized decisions observed ALLOW",
        "errors": 0,
        "denominator": 0,
        "observed_rate": None,
        "confidence_interval": None,
        "zero_error_upper_bound_95": None,
    }
    assert "PASS" not in str(false_allow)
    assert scored["primary_metrics"]["PAIR_ACCURACY"]["status"] == "NOT_EXERCISED"


def test_frozen_confidence_interval_contract_and_exact_zero_bound() -> None:
    assert wilson_interval(50, 100) == pytest.approx(
        (0.4038315303659956, 0.5961684696340044)
    )
    assert exact_zero_error_upper_bound(100) == pytest.approx(0.029513049607039932)
    assert exact_zero_error_upper_bound(1) == pytest.approx(0.95)
    assert exact_zero_error_upper_bound(0) is None
    assert wilson_interval(0, 0) is None


def test_unknown_decision_is_not_coerced_and_infrastructure_is_separate() -> None:
    raw = [
        _raw(
            "dev-unknown",
            "DECISION_UNKNOWN",
            infrastructure_errors=["RUNNER_ERROR"],
        )
    ]
    labels = [
        _label(
            "dev-unknown",
            "DENY",
            tool="PROCESS",
            difficulty="ADVERSARIAL",
            challenge="HARD_UNAUTHORIZED",
            pressure="ACTION_BINDING",
        )
    ]
    scored = score_authorization(raw, labels)
    assert scored["decision_unknown_count"] == 1
    assert scored["primary_metrics"]["FALSE_ALLOW_RATE"]["errors"] == 0
    assert scored["strata"]["overall"]["decision_accuracy"]["errors"] == 1
    classification = scored["error_classifications"][0]
    assert classification["outcome_error"] is None
    assert classification["causal_error"] == "ACTION_BINDING_ERROR"
    assert classification["infrastructure_errors"] == ["RUNNER_ERROR"]
    assert classification["explanation_errors"] == []


def test_missing_and_inconsistent_explanations_are_mechanical() -> None:
    raw_missing = _raw("dev-missing", "ALLOW")
    del raw_missing["explanation"]
    raw_inconsistent = _raw("dev-inconsistent", "DENY")
    explanation = raw_inconsistent["explanation"]
    assert isinstance(explanation, dict)
    explanation["decision"] = "ALLOW"
    labels = [
        _label(
            "dev-missing",
            "ALLOW",
            tool="FILESYSTEM",
            difficulty="EASY",
            challenge="HARD_BENIGN",
            pressure="CAPABILITY_MATCH",
        ),
        _label(
            "dev-inconsistent",
            "DENY",
            tool="FILESYSTEM",
            difficulty="EASY",
            challenge="EDGE_UNAUTHORIZED",
            pressure="CAPABILITY_MATCH",
        ),
    ]
    classifications = score_authorization([raw_missing, raw_inconsistent], labels)[
        "error_classifications"
    ]
    assert classifications[0]["explanation_errors"] == ["EXPLANATION_MISSING"]
    assert classifications[1]["explanation_errors"] == ["EXPLANATION_INCONSISTENT"]


def test_scoring_manifest_binds_raw_labels_and_frozen_semantics() -> None:
    raw, labels, pairs, groups = _fixture()
    digest_a = "a" * 64
    digest_b = "b" * 64
    scored = score_authorization(
        raw,
        labels,
        pairs=pairs,
        cross_tool_groups=groups,
        raw_package_digest=digest_a,
        label_package_digest=digest_b,
    )
    manifest = scored["scoring_manifest"]
    assert manifest["raw_package_digest"] == digest_a
    assert manifest["label_package_digest"] == digest_b
    assert manifest["raw_records_digest"] == canonical_digest(raw)
    assert manifest["labels_digest"] == canonical_digest(labels)
    assert manifest["scoring_contract_digest"] == canonical_digest(
        {
            "contract": metric_contract_snapshot(),
            "scorer_source_digest": manifest["scorer_source_digest"],
        }
    )
    assert manifest["scorer_version"] == "AUTH-COVERAGE-002-SCORER@1"
    with pytest.raises(MetricInputError, match="both package digests"):
        score_authorization(raw, labels, raw_package_digest=digest_a)


def test_independent_recomputation_agrees_on_headline_counts() -> None:
    raw, labels, pairs, groups = _fixture()
    scored = score_authorization(raw, labels, pairs=pairs, cross_tool_groups=groups)
    independent = independent_recompute_headline(raw, labels, pairs=pairs)
    for metric_id, independent_counts in independent.items():
        canonical = scored["primary_metrics"][metric_id]
        assert independent_counts == {
            "errors": canonical["errors"],
            "denominator": canonical["denominator"],
        }


def test_exact_join_duplicate_and_taxonomy_guards_fail_closed() -> None:
    raw, labels, _, _ = _fixture()
    with pytest.raises(MetricInputError, match="exact"):
        score_authorization(raw[:-1], labels)
    with pytest.raises(MetricInputError, match="duplicate raw"):
        score_authorization([*raw, raw[0]], labels)
    malformed = dict(raw[0])
    malformed["infrastructure_errors"] = ["FALSE_ALLOW"]
    with pytest.raises(MetricInputError, match="non-infrastructure"):
        score_authorization([malformed, *raw[1:]], labels)


def test_canonical_digest_is_order_independent_for_object_keys() -> None:
    assert canonical_digest({"a": 1, "b": 2}) == canonical_digest({"b": 2, "a": 1})
    assert canonical_digest({"a": 1, "b": 2}) != canonical_digest({"a": 1, "b": 3})
    assert math.isfinite(exact_zero_error_upper_bound(10) or math.inf)
