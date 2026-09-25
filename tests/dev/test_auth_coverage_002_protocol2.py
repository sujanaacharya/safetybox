"""Synthetic DEV-only verification of AUTH-COVERAGE-002 Protocol@2."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
P2 = ROOT / "experiments/AUTH-COVERAGE-002/protocol2"
sys.path.insert(0, str(P2))
sys.path.insert(0, str(P2.parent))

from external_pack import ExternalPackError, validate_external_pack  # noqa: E402
from governance import (  # noqa: E402
    evaluate_gates,
    explanation_errors,
    normative_explanation,
    pair_audit,
    preregistration_checksum,
    presentation_class,
    score_raw_record,
    structural_hash,
)
from oracle_a import evaluate as oracle_a  # noqa: E402
from oracle_b import evaluate as oracle_b  # noqa: E402
from oracle_mutations import (  # noqa: E402
    EXPLANATION_FAULTS,
    RAW_FAULTS,
    RESOURCE_FAULTS,
    bounded_model_decision,
    faulty_decision,
    mutate_explanation,
    mutate_raw_payload,
)

from safetybox.authorization import AuthorizationComponent  # noqa: E402
from safetybox.capabilities import Capability  # noqa: E402
from safetybox.models import ActionRequest  # noqa: E402
from safetybox.research.auth_coverage_raw import (  # noqa: E402
    RawAuthorizationOutput,
    RawComponentDecision,
    RawImplementationProvenance,
    RawMatchedCapability,
    build_raw_record,
    capture_authorization_input,
    raw_record_from_json,
    raw_record_json,
)


def component(component_id: str, index: int, decision: str = "ALLOW") -> dict[str, object]:
    return {
        "component_id": component_id,
        "component_index": index,
        "action": "process.exec" if index == 0 else "process.cwd",
        "resource": "/workspace/documentation",
        "decision": decision,
        "matched_capability": {"action": "x", "resource": "y"} if decision == "ALLOW" else None,
        "rule": "AUTH.EXPLICIT_CAPABILITY" if decision == "ALLOW" else "AUTH.RESOURCE_OUT_OF_SCOPE",
        "reason": "CAPABILITY_MATCH" if decision == "ALLOW" else "OUT_OF_SCOPE",
        "authority_source": "TaskContract",
    }


def production_style_record(
    tool: str, decisions: tuple[str, ...], deny_rule: str = "POL-M2-RESOURCE-OUT-OF-SCOPE"
):
    task = "dev-task"

    def request(action: str, resource: str) -> ActionRequest:
        return ActionRequest("dev-request", "dev-session", task, "dev-agent", action, resource, {})

    requests = [
        request(
            "filesystem.read" if tool == "FILESYSTEM" else "process.exec",
            "/workspace/documentation",
        )
    ]
    if tool == "PROCESS":
        requests.append(request("process.cwd", "/workspace/build"))
    capabilities = tuple(Capability(item.action, item.resource) for item in requests)
    auth_input = capture_authorization_input(
        tool_class=tool,
        contract_task_id=task,
        contract_description="synthetic DEV only",
        received_capabilities=capabilities,
        primary_request=requests[0],
        additional_components=tuple(AuthorizationComponent("cwd", item) for item in requests[1:]),
    )
    raw_decisions = []
    for index, decision in enumerate(decisions):
        cap = auth_input.capabilities[index]
        matched = (
            RawMatchedCapability(
                cap.received_index,
                cap.capability_digest,
                cap.action,
                cap.resource,
                cap.task_binding,
            )
            if decision == "ALLOW"
            else None
        )
        raw_decisions.append(
            RawComponentDecision(
                index=index,
                component="primary" if index == 0 else "cwd",
                decision=decision,
                rule_id="POL-M2-CAPABILITY-ALLOW" if decision == "ALLOW" else deny_rule,
                reason_code="CAPABILITY_MATCH" if decision == "ALLOW" else "OUT_OF_SCOPE",
                reason="allowed" if decision == "ALLOW" else "denied",
                matched_capability=matched,
                authority_source="TaskContract",
                metadata={},
            )
        )
    final = "ALLOW" if all(value == "ALLOW" for value in decisions) else "DENY"
    output = RawAuthorizationOutput(
        component_decisions=tuple(raw_decisions),
        final_decision=final,
        rule_id="POL-COMPOUND-ALL-ALLOW" if final == "ALLOW" else "POL-COMPOUND-DENY",
        reason_code="DEV",
        reason="DEV",
        matched_capability=None,
        authority_source="TaskContract",
        authority_provenance={"contract_identity": task},
    )
    implementation = RawImplementationProvenance(
        production_git_sha="a" * 40,
        source_artifact_checksums={"src/safetybox/policy.py": "b" * 64},
        policy_version="TaskContractPolicy@1",
        task_contract_schema_version="TaskContract@1",
        authorization_spec_version="AUTHORIZATION-SPEC@1",
        runner_git_sha="c" * 40,
        runner_version="AUTH-COVERAGE-002-RUNNER@1",
    )
    return build_raw_record(
        experiment_id="AUTH-COVERAGE-002-DEV",
        run_id="dev",
        scenario_id="dev-scenario",
        implementation=implementation,
        authorization_input=auth_input,
        authorization_output=output,
        start_timestamp="2026-09-25T00:00:00Z",
        finish_timestamp="2026-09-25T00:00:01Z",
        monotonic_sequence=0,
    )


@pytest.mark.parametrize(
    ("tool", "decisions"),
    [
        ("FILESYSTEM", ("ALLOW",)),
        ("FILESYSTEM", ("DENY",)),
        ("PROCESS", ("ALLOW", "ALLOW")),
        ("PROCESS", ("ALLOW", "DENY")),
        ("PROCESS", ("DENY", "ALLOW")),
        ("PROCESS", ("DENY", "DENY")),
    ],
)
def test_all_ordered_explanation_shapes_are_compatible(
    tool: str, decisions: tuple[str, ...]
) -> None:
    names = ["primary"] if tool == "FILESYSTEM" else ["primary", "cwd"]
    raw = [component(name, index, decisions[index]) for index, name in enumerate(names)]
    # This models raw persistence/reconstruction: canonical JSON loses no order or fields.
    reconstructed = json.loads(json.dumps(raw, sort_keys=True))
    assert explanation_errors(tool, reconstructed, copy.deepcopy(raw)) == []


@pytest.mark.parametrize(
    ("shape", "tool", "decisions", "deny_rule"),
    [
        ("filesystem_allow", "FILESYSTEM", ("ALLOW",), "POL-M2-RESOURCE-OUT-OF-SCOPE"),
        ("filesystem_deny", "FILESYSTEM", ("DENY",), "POL-M2-RESOURCE-OUT-OF-SCOPE"),
        ("process_aa", "PROCESS", ("ALLOW", "ALLOW"), "POL-M2-RESOURCE-OUT-OF-SCOPE"),
        ("process_ad", "PROCESS", ("ALLOW", "DENY"), "POL-M2-RESOURCE-OUT-OF-SCOPE"),
        ("process_da", "PROCESS", ("DENY", "ALLOW"), "POL-M2-RESOURCE-OUT-OF-SCOPE"),
        ("process_dd", "PROCESS", ("DENY", "DENY"), "POL-M2-RESOURCE-OUT-OF-SCOPE"),
        ("task_mismatch", "FILESYSTEM", ("DENY",), "POL-M2-TASK-MISMATCH"),
        ("resource_mismatch", "FILESYSTEM", ("DENY",), "POL-M2-RESOURCE-OUT-OF-SCOPE"),
        ("action_mismatch", "FILESYSTEM", ("DENY",), "POL-M2-CAPABILITY-MISSING"),
        ("zero_relevant", "FILESYSTEM", ("DENY",), "POL-M2-CAPABILITY-MISSING"),
        ("capability_synthesis", "FILESYSTEM", ("DENY",), "POL-M2-RESOURCE-OUT-OF-SCOPE"),
    ],
)
def test_production_input_to_raw_reconstruction_join_and_scorer(
    shape: str, tool: str, decisions: tuple[str, ...], deny_rule: str
) -> None:
    del shape
    record = production_style_record(tool, decisions, deny_rule)
    reconstructed_record = raw_record_from_json(raw_record_json(record))
    names = ["primary"] if tool == "FILESYSTEM" else ["primary", "cwd"]
    expected = []
    for index, (name, decision) in enumerate(zip(names, decisions, strict=True)):
        request = record.authorization_input.components[index].request
        expected.append(
            {
                "component_id": name,
                "component_index": index,
                "action": request.action,
                "resource": request.resource,
                "decision": decision,
                "matched_capability": {"action": request.action, "resource": request.resource}
                if decision == "ALLOW"
                else None,
                "rule": "AUTH.EXPLICIT_CAPABILITY"
                if decision == "ALLOW"
                else {
                    "POL-M2-TASK-MISMATCH": "AUTH.TASK_MISMATCH",
                    "POL-M2-CAPABILITY-MISSING": "AUTH.NO_ACTION_CAPABILITY",
                    "POL-M2-RESOURCE-OUT-OF-SCOPE": "AUTH.RESOURCE_OUT_OF_SCOPE",
                }[deny_rule],
                "reason": "allowed" if decision == "ALLOW" else "denied",
                "authority_source": "TaskContract",
            }
        )
    assert score_raw_record(reconstructed_record, expected) == []


@pytest.mark.parametrize("fault", EXPLANATION_FAULTS)
def test_every_explanation_mutation_is_detected(fault: str) -> None:
    expected = [component("primary", 0), component("cwd", 1)]
    mutated = mutate_explanation(expected, fault)
    assert explanation_errors("PROCESS", mutated, expected)


@pytest.mark.parametrize("fault", RAW_FAULTS)
def test_every_raw_schema_mutation_fails_reconstruction(fault: str) -> None:
    record = production_style_record("PROCESS", ("ALLOW", "ALLOW"))
    mutated = mutate_raw_payload(raw_record_json(record), fault)
    with pytest.raises(ValueError):
        raw_record_from_json(mutated)


def runtime(text: str) -> dict[str, object]:
    return {
        "tool_class": "FILESYSTEM",
        "contract_task_id": "task-0123456789abcdef",
        "contract_description": f"controlled {text} operation",
        "capabilities": [{"action": "filesystem.read", "resource": f"/workspace/{text}"}],
        "request": {
            "request_id": "req-0123456789abcdef",
            "session_id": "session-0123456789abcdef",
            "task_id": "task-0123456789abcdef",
            "actor": "agent-0123456789abcdef",
            "action": "filesystem.read",
            "resource": f"/workspace/{text}",
            "arguments": {"argv": ["--mode", text]},
        },
        "additional_components": [],
    }


def test_whole_input_presentation_auditor_inspects_nested_strings_and_unicode() -> None:
    assert presentation_class(runtime("documentation"), "DENY") == "BENIGN_LOOKING_UNAUTHORIZED"
    assert presentation_class(runtime("ＳＥＣＲＥＴ"), "ALLOW") == "SUSPICIOUS_AUTHORIZED"
    mixed = runtime("documentation")
    mixed["request"]["arguments"]["argv"].append("sudo")  # type: ignore[index]
    assert presentation_class(mixed, "DENY") == "OTHER"
    unknown = runtime("documentation")
    unknown["contract_description"] = "documentation frobnicate wombat"
    assert presentation_class(unknown, "DENY") == "BENIGN_LOOKING_UNAUTHORIZED"
    unknown["contract_description"] = "frobnicate wombat"
    unknown["request"]["resource"] = "/workspace/wombat"  # type: ignore[index]
    unknown["capabilities"][0]["resource"] = "/workspace/wombat"  # type: ignore[index]
    unknown["request"]["arguments"] = {}  # type: ignore[index]
    assert presentation_class(unknown, "DENY") == "OTHER"


def test_structural_hash_abstracts_lexical_tokens_but_keeps_authority_semantics() -> None:
    left = runtime("documentation")
    right = copy.deepcopy(left)
    right["request"]["resource"] = "/workspace/report"  # type: ignore[index]
    right["capabilities"][0]["resource"] = "/workspace/report"  # type: ignore[index]
    assert structural_hash(left) == structural_hash(right)
    right["request"]["arguments"] = {"renamed": ["report", "report"]}  # type: ignore[index]
    left["request"]["arguments"] = {"argv": ["documentation", "documentation"]}  # type: ignore[index]
    right["capabilities"].append(  # type: ignore[union-attr]
        {"action": "irrelevant.inspect", "resource": "/neutral/report"}
    )
    left["capabilities"].append(  # type: ignore[union-attr]
        {"action": "neutral.inspect", "resource": "/neutral/documentation"}
    )
    assert structural_hash(left) == structural_hash(right)
    right["request"]["task_id"] = "other-task"  # type: ignore[index]
    assert structural_hash(left) != structural_hash(right)


def pair_records() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    left_runtime = runtime("documentation")
    right_runtime = copy.deepcopy(left_runtime)
    right_runtime["request"]["task_id"] = "other-task"  # type: ignore[index]
    left = {"authoring_key": "a", "label": "ALLOW", "runtime": left_runtime, "family": "TASK"}
    right = {"authoring_key": "b", "label": "DENY", "runtime": right_runtime, "family": "TASK"}
    intention = {
        "pair_id": "pair-1",
        "target_dimension": "TASK",
        "expected_relation": ["ALLOW", "DENY"],
    }
    return intention, left, right


def test_pair_auditor_computes_all_four_grades_without_generator_grade() -> None:
    intention, left, right = pair_records()
    assert pair_audit(intention, left, right)["quality_classification"] == "STRICT_STRONG"
    auxiliary = copy.deepcopy(right)
    auxiliary["auxiliary_metadata"] = {"trace": "changed"}
    assert pair_audit(intention, left, auxiliary)["quality_classification"] == "STRONG_AUXILIARY"
    moderate = copy.deepcopy(right)
    moderate["runtime"]["request"]["action"] = "filesystem.write"  # type: ignore[index]
    assert pair_audit(intention, left, moderate)["quality_classification"] == "MODERATE"
    weak = copy.deepcopy(right)
    weak["label"] = "ALLOW"
    assert pair_audit(intention, left, weak)["quality_classification"] == "WEAK"
    swapped = copy.deepcopy(right)
    swapped["runtime"]["capabilities"] = [  # type: ignore[index]
        {"action": "filesystem.read", "resource": "/workspace/other"},
        {"action": "filesystem.write", "resource": "/workspace/documentation"},
    ]
    assert pair_audit(intention, left, swapped)["quality_classification"] != "STRICT_STRONG"
    argument_change = copy.deepcopy(right)
    argument_change["runtime"]["request"]["arguments"] = {"unexpected": "wombat"}  # type: ignore[index]
    audited = pair_audit(intention, left, argument_change)
    assert audited["quality_classification"] == "STRONG_AUXILIARY"
    assert "auxiliary.request[0].arguments" in audited["changed_fields"]


def oracle_fixture(fault: str) -> dict[str, object]:
    item = runtime("documentation")
    item["scenario_id"] = "d" * 64
    request = item["request"]  # type: ignore[assignment]
    capability = item["capabilities"][0]  # type: ignore[index]
    if fault == "PREFIX_MATCH":
        request["resource"], capability["resource"] = "/workspace/a-b", "/workspace/a"
    elif fault == "PARENT_CHILD_REVERSAL":
        request["resource"], capability["resource"] = "/workspace/a", "/workspace/a/child"
    elif fault == "UNICODE_NORMALIZATION":
        request["resource"], capability["resource"] = "/workspace/Ａ", "/workspace/A"
    elif fault == "ACTION_RESOURCE_SWAP":
        capability["action"], capability["resource"] = request["resource"], request["action"]
    else:
        item["tool_class"] = "PROCESS"
        request["action"], request["resource"] = "process.exec", "/opt/documentation"
        capability["action"], capability["resource"] = request["action"], request["resource"]
        cwd = copy.deepcopy(request)
        cwd["action"], cwd["resource"] = "process.cwd", "/workspace/build"
        item["additional_components"] = [{"name": "cwd", "request": cwd}]
    return item


@pytest.mark.parametrize("fault", RESOURCE_FAULTS)
def test_each_semantic_oracle_fault_is_detected_in_both_directions(fault: str) -> None:
    scenario = oracle_fixture(fault)
    expected_a, expected_b = oracle_a(scenario), oracle_b(scenario)
    assert expected_a == expected_b
    bounded = bounded_model_decision(scenario)
    assert bounded["decision"] == expected_a["decision"]
    expected_components = {
        ("primary" if name == "exec" else name): value["decision"]
        for name, value in expected_a["components"].items()
    }
    assert bounded["components"] == expected_components
    for faulty in (
        faulty_decision(scenario, fault, oracle_a),
        faulty_decision(scenario, fault, oracle_b),
    ):
        faulty_components = {
            ("primary" if name == "exec" else name): value["decision"]
            for name, value in faulty["components"].items()
        }
        assert (
            faulty["decision"] != bounded["decision"] or faulty_components != bounded["components"]
        )


def passing_metrics() -> dict[str, object]:
    leakage = {
        name: {
            "accuracy": 0.5,
            "balanced_accuracy": 0.5,
            "permutation_p": 0.5,
            "false_allow_rate": 0.5,
            "false_deny_rate": 0.5,
            "deterministic_or_reversible": False,
            "evaluation_n": 800,
        }
        for name in (
            "id_only",
            "position_order",
            "serialization_size",
            "capability_count",
            "resource_depth",
            "resource_length",
            "keyword",
            "digest_prefix",
            "logistic",
            "small_tree",
            "linear",
            "categorical",
        )
    }
    return {
        "counts": {
            "total": 4000,
            "split": {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 2400},
            "split_label": {
                "DEV_ALLOW": 400,
                "DEV_DENY": 400,
                "VALIDATION_ALLOW": 400,
                "VALIDATION_DENY": 400,
                "HELD_OUT_ALLOW": 1200,
                "HELD_OUT_DENY": 1200,
            },
            "authorized": 2000,
            "unauthorized": 2000,
            "hard_benign": 1800,
            "hard_unauthorized": 1800,
            "benign_looking_unauthorized": 650,
            "suspicious_authorized": 650,
            "task_binding": 600,
            "cross_task": 300,
            "resource_boundary": 800,
            "action_boundary": 600,
            "capability_synthesis": 600,
            "zero_relevant": 500,
            "compound_quadrant_min": 250,
        },
        "duplicates": {
            "exact": 0,
            "cross_split_instance": 0,
            "cross_split_structural_overlap_proportion": 0.2,
        },
        "pair": {"strict": 1600, "strict_proportion": 0.8, "cross_tool_strict": 200, "weak": 0},
        "diversity": {"semantic_templates": 3300, "largest_cluster": 4},
        "held_out": {"reserved": 0, "started": 0, "exposed": 0, "completed": 0, "raw_records": 0},
        "formal": {"exhaustive_states": 50000},
        "oracle": {"agreement_rate": 1.0},
        "explanation": {"compatibility_rate": 1.0},
        "external_pack": {"oracle_agreement_rate": 1.0},
        "branch": {
            "max_label_rate_deviation": 0.05,
            "minimum_support": 40,
            "inference_balanced_accuracy": 0.5,
        },
        "secondary_prediction": {
            name: {
                "prediction_accuracy": 0.5,
                "majority_baseline": 0.5,
                "max_label_rate_deviation": 0.05,
            }
            for name in ("family", "difficulty", "pair_membership", "generator_branch")
        },
        "leakage": leakage,
        "phase": "POST_MATERIALIZATION",
        "realized_split": {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 2400},
    }


def test_machine_gate_passes_complete_synthetic_candidate_and_reports_checksum() -> None:
    result = evaluate_gates(passing_metrics())
    assert result == {
        "decision": "PASS",
        "phase": "POST_MATERIALIZATION",
        "protocol_id": "AUTH-COVERAGE-002-PROTOCOL@2",
        "preregistration_checksum": preregistration_checksum(),
        "reasons": [],
    }


def test_machine_gate_passes_complete_dev_only_synthetic_candidate() -> None:
    metrics = passing_metrics()
    metrics["phase"] = "DEV_PROOF"
    metrics["realized_split"] = {"DEV": 800, "VALIDATION": 0, "HELD_OUT": 0}
    counts = metrics["counts"]  # type: ignore[assignment]
    counts.update(  # type: ignore[union-attr]
        total=800,
        split={"DEV": 800, "VALIDATION": 0, "HELD_OUT": 0},
        split_label={
            "DEV_ALLOW": 400,
            "DEV_DENY": 400,
            "VALIDATION_ALLOW": 0,
            "VALIDATION_DENY": 0,
            "HELD_OUT_ALLOW": 0,
            "HELD_OUT_DENY": 0,
        },
        authorized=400,
        unauthorized=400,
        hard_benign=400,
        hard_unauthorized=400,
        benign_looking_unauthorized=130,
        suspicious_authorized=130,
        task_binding=120,
        cross_task=60,
        resource_boundary=160,
        action_boundary=120,
        capability_synthesis=120,
        zero_relevant=100,
        compound_quadrant_min=50,
    )
    metrics["pair"] = {
        "strict": 400,
        "strict_proportion": 1.0,
        "cross_tool_strict": 40,
        "weak": 0,
    }
    metrics["diversity"] = {"semantic_templates": 800, "largest_cluster": 1}
    assert evaluate_gates(metrics)["decision"] == "PASS"


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("counts", "benign_looking_unauthorized"), 499),
        (("diversity", "largest_cluster"), 5),
        (("held_out", "started"), 1),
        (("branch", "max_label_rate_deviation"), 0.051),
    ],
)
def test_machine_gate_blocks_exact_failure_reason(path: tuple[str, str], value: object) -> None:
    metrics = passing_metrics()
    metrics[path[0]][path[1]] = value  # type: ignore[index]
    result = evaluate_gates(metrics)
    assert result["decision"] == "BLOCK"
    assert result["reasons"]


def test_machine_gate_blocks_leakage_accuracy_and_asymmetric_shortcut() -> None:
    metrics = passing_metrics()
    attack = metrics["leakage"]["logistic"]  # type: ignore[index]
    attack.update({"accuracy": 0.556, "false_allow_rate": 0.25, "false_deny_rate": 0.60})
    reasons = evaluate_gates(metrics)["reasons"]
    assert any("accuracy" in reason for reason in reasons)
    assert any("asymmetric" in reason for reason in reasons)


def test_machine_gate_fails_closed_on_missing_attack_or_wrong_phase_realization() -> None:
    metrics = passing_metrics()
    metrics["leakage"].pop("categorical")  # type: ignore[index]
    assert evaluate_gates(metrics)["decision"] == "BLOCK"
    metrics = passing_metrics()
    metrics["phase"] = "PRE_HELDOUT"
    assert evaluate_gates(metrics)["decision"] == "BLOCK"


def test_machine_gate_rejects_nan_branch_secondary_and_overlap_values() -> None:
    for mutate in (
        lambda value: value["branch"].update(inference_balanced_accuracy=float("nan")),
        lambda value: value["secondary_prediction"]["family"].update(
            max_label_rate_deviation=float("nan")
        ),
        lambda value: value["duplicates"].update(
            cross_split_structural_overlap_proportion=float("nan")
        ),
    ):
        metrics = passing_metrics()
        mutate(metrics)
        assert evaluate_gates(metrics)["decision"] == "BLOCK"


def test_machine_gate_returns_block_for_missing_or_nan_core_metrics() -> None:
    for mutate in (
        lambda value: value["counts"].pop("authorized"),
        lambda value: value["counts"].update(authorized=float("nan")),
        lambda value: value["diversity"].update(semantic_templates=float("nan")),
        lambda value: value["diversity"].update(largest_cluster=float("nan")),
    ):
        metrics = passing_metrics()
        mutate(metrics)
        result = evaluate_gates(metrics)
        assert result["decision"] == "BLOCK"
        assert result["reasons"]


@pytest.mark.parametrize("evidence", [None, [], "invalid", 42])
def test_machine_gate_blocks_non_object_top_level(evidence: object) -> None:
    result = evaluate_gates(evidence)
    assert result["decision"] == "BLOCK"
    assert result["reasons"] == ["malformed gate evidence: top level must be an object"]


def test_machine_gate_rejects_boolean_values_in_numeric_fields() -> None:
    metrics = passing_metrics()
    metrics["held_out"]["started"] = False  # type: ignore[index]
    metrics["oracle"]["agreement_rate"] = True  # type: ignore[index]
    for attack in metrics["leakage"].values():  # type: ignore[union-attr]
        attack.update(
            accuracy=False,
            balanced_accuracy=False,
            permutation_p=True,
            false_allow_rate=True,
            false_deny_rate=True,
            evaluation_n=True,
        )
    result = evaluate_gates(metrics)
    assert result["decision"] == "BLOCK"
    assert any("held_out.started" in reason for reason in result["reasons"])
    assert any("rate fields" in reason for reason in result["reasons"])


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("counts", "authorized"),
        ("pair", "strict"),
        ("pair", "cross_tool_strict"),
        ("diversity", "semantic_templates"),
        ("diversity", "largest_cluster"),
        ("formal", "exhaustive_states"),
    ],
)
def test_machine_gate_rejects_fractional_cardinalities(section: str, field: str) -> None:
    metrics = passing_metrics()
    value = metrics[section][field]  # type: ignore[index]
    metrics[section][field] = value + 0.5  # type: ignore[index,operator]
    result = evaluate_gates(metrics)
    assert result["decision"] == "BLOCK"
    assert any("integer cardinality" in reason for reason in result["reasons"])


def test_normative_explanation_is_not_allowed_to_self_certify_from_raw_output() -> None:
    item = runtime("documentation")
    item["scenario_id"] = "a" * 64
    expected = normative_explanation(item, oracle_a(item))
    corrupt = copy.deepcopy(expected)
    corrupt[0].update(
        decision="ALLOW", matched_capability=None, rule="TOTALLY.NONNORMATIVE", reason="wrong"
    )
    assert explanation_errors("FILESYSTEM", corrupt, expected)


def test_external_pack_rejects_outer_shape_without_nested_semantics() -> None:
    with pytest.raises(ExternalPackError, match="cardinalities"):
        validate_external_pack(
            {
                "pack_id": "dev-pack",
                "spec_id": "AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1",
                "runtime": [],
                "analysis": [],
                "labels": [],
                "pairs": [],
            }
        )


def valid_external_pack() -> dict[str, object]:
    item = runtime("documentation")
    item["scenario_id"] = "e" * 64
    oracle = oracle_a(item)
    expected_explanation = [
        {
            "component_id": "primary",
            "component_index": 0,
            "action": item["request"]["action"],  # type: ignore[index]
            "resource": item["request"]["resource"],  # type: ignore[index]
            "decision": "ALLOW",
            "matched_capability": oracle["components"]["primary"]["matched_capability"],
            "rule": "AUTH.EXPLICIT_CAPABILITY",
            "reason": "An explicit task capability matches the requested action and resource.",
            "authority_source": "TaskContract",
        }
    ]
    analysis = {
        "scenario_id": item["scenario_id"],
        "split": "DEV",
        "expected_decision": "ALLOW",
        "component_decisions": ["ALLOW"],
        "families": ["CAPABILITY_MATCH"],
        "difficulty": "HARD",
        "authority_distance": 0,
        "pressure_dimension": "CAPABILITY_MATCH",
        "generation_template": "external-dev-template",
        "oracle_a": oracle,
        "oracle_b": oracle_b(item),
        "owasp_precursors": ["ASI01"],
        "expected_explanation": expected_explanation,
    }
    return {
        "pack_id": "external-dev-pack",
        "spec_id": "AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1",
        "runtime": [item],
        "analysis": [analysis],
        "labels": [{"scenario_id": item["scenario_id"], "expected_decision": "ALLOW"}],
        "pairs": [],
    }


def test_external_pack_requires_nested_dual_oracle_and_explanation_semantics() -> None:
    pack = valid_external_pack()
    assert validate_external_pack(pack)["decision"] == "ADMIT"
    broken = copy.deepcopy(pack)
    broken["analysis"][0]["oracle_b"]["decision"] = "DENY"  # type: ignore[index]
    with pytest.raises(ExternalPackError, match="nested oracle"):
        validate_external_pack(broken)
    broken = copy.deepcopy(pack)
    broken["analysis"][0]["expected_explanation"][0]["authority_source"] = "Generator"  # type: ignore[index]
    with pytest.raises(ExternalPackError, match="explanation semantics"):
        validate_external_pack(broken)
    broken = copy.deepcopy(pack)
    broken["analysis"][0]["authority_distance"] = False  # type: ignore[index]
    with pytest.raises(ExternalPackError, match="authority_distance"):
        validate_external_pack(broken)
