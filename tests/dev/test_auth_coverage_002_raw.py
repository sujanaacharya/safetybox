"""Synthetic DEV-only tests for AUTH-COVERAGE-002 raw evidence."""

from __future__ import annotations

import json
from dataclasses import replace
from types import MappingProxyType

import pytest

from safetybox.capabilities import Capability
from safetybox.models import ActionRequest, Decision
from safetybox.policy import TaskContractPolicy
from safetybox.research.auth_coverage_raw import (
    CANONICAL_SERIALIZATION_ID,
    RAW_SCHEMA_ID,
    RawAuthorizationError,
    RawAuthorizationOutput,
    RawComponentDecision,
    RawImplementationProvenance,
    RawIntegrityError,
    RawMatchedCapability,
    RawSchemaError,
    build_raw_record,
    canonical_json_bytes,
    canonical_sha256,
    capture_authorization_input,
    raw_record_from_json,
    raw_record_json,
    verify_raw_record,
)


def request(
    *, action: str = "filesystem.read", resource: str = "/workspace/dev/a"
) -> ActionRequest:
    return ActionRequest(
        request_id="dev-request-1",
        session_id="dev-session-1",
        task_id="dev-task-1",
        actor="synthetic-dev-agent",
        action=action,
        resource=resource,
        arguments={"recursive": False, "limits": {"bytes": 4096}},
    )


def implementation() -> RawImplementationProvenance:
    return RawImplementationProvenance(
        production_git_sha="a" * 40,
        source_artifact_checksums={"src/safetybox/policy.py": "b" * 64},
        policy_version="TaskContractPolicy@1",
        task_contract_schema_version="TaskContract@1",
        authorization_spec_version="AUTHORIZATION-SPEC@1",
        runner_git_sha="c" * 40,
        runner_version="AUTH-COVERAGE-002-RUNNER@1",
    )


def make_record(*, scenario_id: str = "opaque-dev-correlation-a"):
    capabilities = (
        Capability("filesystem.read", "/workspace/dev/**"),
        Capability("filesystem.write", "/workspace/dev/output/**"),
        Capability("filesystem.read", "/workspace/shared/exact"),
    )
    auth_input = capture_authorization_input(
        tool_class="filesystem",
        contract_task_id="dev-task-1",
        contract_description="synthetic DEV authorization only",
        received_capabilities=capabilities,
        primary_request=request(),
    )
    matched = auth_input.capabilities[0]
    matched_output = RawMatchedCapability(
        received_index=matched.received_index,
        capability_digest=matched.capability_digest,
        action=matched.action,
        resource=matched.resource,
        task_binding=matched.task_binding,
    )
    component = RawComponentDecision(
        index=0,
        component="primary",
        decision="ALLOW",
        rule_id="POL-M2-CAPABILITY-ALLOW",
        reason_code="CAPABILITY_MATCH",
        reason="An explicit task capability matches.",
        matched_capability=matched_output,
        authority_source="TaskContract",
        metadata={"contract_task_id": "dev-task-1"},
    )
    output = RawAuthorizationOutput(
        component_decisions=(component,),
        final_decision="ALLOW",
        rule_id=component.rule_id,
        reason_code=component.reason_code,
        reason=component.reason,
        matched_capability=matched_output,
        authority_source="TaskContract",
        authority_provenance={
            "contract_identity": "dev-task-1",
            "capability_digest": matched.capability_digest,
            "issuer": "synthetic-dev-fixture",
        },
    )
    return build_raw_record(
        experiment_id="AUTH-COVERAGE-002-DEV",
        run_id="dev-run-1",
        scenario_id=scenario_id,
        implementation=implementation(),
        authorization_input=auth_input,
        authorization_output=output,
        start_timestamp="2026-09-25T00:00:00.000000Z",
        finish_timestamp="2026-09-25T00:00:00.000100Z",
        monotonic_sequence=0,
    )


def test_frozen_identity_and_canonical_mapping_order() -> None:
    assert RAW_SCHEMA_ID == "AUTH-COVERAGE-002-RAW-SCHEMA@1"
    assert CANONICAL_SERIALIZATION_ID == "AUTH-COVERAGE-002-CANONICAL-JSON@1"
    assert canonical_json_bytes({"z": 1, "a": 2}) == canonical_json_bytes({"a": 2, "z": 1})
    assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 2})


def test_capability_order_is_preserved_and_digest_is_order_sensitive() -> None:
    record = make_record()
    auth_input = record.authorization_input

    assert [item.received_index for item in auth_input.capabilities] == [0, 1, 2]
    assert [item.action for item in auth_input.capabilities] == [
        "filesystem.read",
        "filesystem.write",
        "filesystem.read",
    ]
    reversed_input = replace(
        auth_input,
        capabilities=tuple(
            replace(capability, received_index=index)
            for index, capability in enumerate(reversed(auth_input.capabilities))
        ),
    )
    assert canonical_sha256(reversed_input) != record.input_digest


def test_raw_record_reconstructs_production_input_without_runtime_scenario() -> None:
    record = make_record()
    persisted = raw_record_json(record) + b"\n"
    parsed = raw_record_from_json(persisted)
    reconstructed = verify_raw_record(parsed)

    assert reconstructed.tool_class == "filesystem"
    assert reconstructed.contract.task_id == "dev-task-1"
    assert reconstructed.contract.description == "synthetic DEV authorization only"
    assert reconstructed.received_capabilities == (
        Capability("filesystem.read", "/workspace/dev/**"),
        Capability("filesystem.write", "/workspace/dev/output/**"),
        Capability("filesystem.read", "/workspace/shared/exact"),
    )
    assert dict(reconstructed.primary_request.arguments) == {
        "recursive": False,
        "limits": MappingProxyType({"bytes": 4096}),
    }
    assert raw_record_json(record).endswith(b"}")


def test_strict_parser_rejects_unknown_missing_duplicate_and_noncanonical_fields() -> None:
    canonical = raw_record_json(make_record())
    decoded = json.loads(canonical)

    decoded["unknown"] = "field"
    with pytest.raises(RawSchemaError, match="unknown=.*unknown"):
        raw_record_from_json(json.dumps(decoded, sort_keys=True, separators=(",", ":")))

    decoded = json.loads(canonical)
    del decoded["run_id"]
    with pytest.raises(RawSchemaError, match="missing=.*run_id"):
        raw_record_from_json(json.dumps(decoded, sort_keys=True, separators=(",", ":")))

    with pytest.raises(RawSchemaError, match="duplicate JSON object key"):
        raw_record_from_json('{"record_digest":"a","record_digest":"b"}')

    with pytest.raises(RawSchemaError, match="not frozen canonical JSON"):
        raw_record_from_json(json.dumps(json.loads(canonical), indent=2))


def test_input_output_and_record_tampering_are_independently_detected() -> None:
    record = make_record()
    with pytest.raises(RawIntegrityError, match="input digest"):
        verify_raw_record(replace(record, input_digest="0" * 64))
    with pytest.raises(RawIntegrityError, match="output digest"):
        verify_raw_record(replace(record, output_digest="0" * 64))
    with pytest.raises(RawIntegrityError, match="record digest"):
        verify_raw_record(replace(record, record_digest="0" * 64))


def test_production_exception_is_represented_as_unknown_not_coerced_to_deny() -> None:
    unknown = RawAuthorizationOutput(
        component_decisions=(),
        final_decision="DECISION_UNKNOWN",
        rule_id=None,
        reason_code=None,
        reason=None,
        matched_capability=None,
        authority_source=None,
        authority_provenance={},
        error=RawAuthorizationError(
            state="PRODUCTION_AUTHORIZATION_EXCEPTION",
            error_type="SyntheticDevError",
            message="synthetic DEV exception",
            call_began=True,
        ),
    )

    assert unknown.final_decision == "DECISION_UNKNOWN"
    assert unknown.error is not None
    assert unknown.error.call_began is True


def test_scenario_identifier_is_only_correlation_and_cannot_change_decision() -> None:
    first = make_record(scenario_id="opaque-dev-correlation-a")
    second = make_record(scenario_id="opaque-dev-correlation-z")
    first_reconstructed = verify_raw_record(first)
    second_reconstructed = verify_raw_record(second)

    first_decision = TaskContractPolicy(first_reconstructed.contract).authorize(
        first_reconstructed.primary_request
    )
    second_decision = TaskContractPolicy(second_reconstructed.contract).authorize(
        second_reconstructed.primary_request
    )
    assert first_decision.decision is Decision.ALLOW
    assert second_decision == first_decision
    assert first.input_digest == second.input_digest
    assert first.output_digest == second.output_digest
    assert first.record_digest != second.record_digest


@pytest.mark.parametrize(
    "forbidden",
    [
        "expected_decision",
        "family",
        "difficulty",
        "pair_id",
        "oracle_output",
        "authority_distance",
        "error_category",
        "scoring_category",
        "split_derivation_logic",
    ],
)
def test_benchmark_answer_and_scoring_metadata_are_rejected(forbidden: str) -> None:
    contaminated = request()
    contaminated = replace(contaminated, arguments={forbidden: "must-not-enter-raw-input"})

    with pytest.raises(RawSchemaError, match="prohibited benchmark metadata"):
        capture_authorization_input(
            tool_class="filesystem",
            contract_task_id="dev-task-1",
            contract_description="synthetic DEV authorization only",
            received_capabilities=(),
            primary_request=contaminated,
        )


def test_non_finite_values_and_unordered_values_cannot_enter_canonical_input() -> None:
    for arguments in ({"bad": float("nan")}, {"bad": {"unordered"}}):
        with pytest.raises(RawSchemaError):
            capture_authorization_input(
                tool_class="filesystem",
                contract_task_id="dev-task-1",
                contract_description="synthetic DEV authorization only",
                received_capabilities=(),
                primary_request=replace(request(), arguments=arguments),
            )
