#!/usr/bin/env python3
"""DEV/VALIDATION rehearsal of full raw-component explanation scoring."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from explanation_scoring import RULE_MAP, score_raw_explanation

from safetybox.research.auth_coverage_raw import (
    RawAuthorizationOutput,
    RawComponentDecision,
    RawImplementationProvenance,
    RawMatchedCapability,
    build_raw_record,
    capture_authorization_input,
)
from safetybox.research.auth_coverage_runner import runtime_scenario_from_mapping

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"
INVERSE_RULE = {value: key for key, value in RULE_MAP.items()}


def _load(path: Path):  # type: ignore[no-untyped-def]
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    analysis = {
        item["scenario_id"]: item for item in _load(CORPUS / "analysis/analysis.json")["records"]
    }
    runtime_values = [
        item
        for split in ("DEV", "VALIDATION")
        for item in _load(CORPUS / f"runtime/{split}/scenarios.json")
    ]
    implementation = RawImplementationProvenance(
        production_git_sha="a" * 40,
        source_artifact_checksums={"synthetic-rehearsal": "b" * 64},
        policy_version="TaskContractPolicy@1",
        task_contract_schema_version="TaskContract@1",
        authorization_spec_version="AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1",
        runner_git_sha="c" * 40,
        runner_version="AUTH-COVERAGE-002-RUNNER@1",
    )
    errors: list[list[str]] = []
    mutation_detected = False
    for sequence, runtime in enumerate(runtime_values):
        parsed = runtime_scenario_from_mapping(runtime)
        captured = capture_authorization_input(
            tool_class=parsed.tool_class,
            contract_task_id=parsed.contract_task_id,
            contract_description=parsed.contract_description,
            received_capabilities=parsed.capabilities,
            primary_request=parsed.request,
            additional_components=parsed.additional_components,
        )
        expected = analysis[runtime["scenario_id"]]["expected_explanation"]
        components = []
        expected_components = list(expected["components"].items())
        for index, (name, wanted) in enumerate(expected_components):
            matched = wanted["matched_capability"]
            raw_match = None
            if matched is not None:
                source = next(
                    item
                    for item in captured.capabilities
                    if item.action == matched["action"] and item.resource == matched["resource"]
                )
                raw_match = RawMatchedCapability(
                    source.received_index,
                    source.capability_digest,
                    source.action,
                    source.resource,
                    source.task_binding,
                )
            rule = INVERSE_RULE[wanted["rule"]]
            components.append(
                RawComponentDecision(
                    index=index,
                    component=(
                        "primary" if runtime["tool_class"] == "PROCESS" and name == "exec" else name
                    ),
                    decision=wanted["decision"],
                    rule_id=rule,
                    reason_code=rule,
                    reason="synthetic structured-field rehearsal",
                    matched_capability=raw_match,
                    authority_source="TaskContract",
                    metadata={},
                )
            )
        final_rule = (
            INVERSE_RULE[expected["rule"]]
            if runtime["tool_class"] == "PROCESS"
            else components[0].rule_id
        )
        output = RawAuthorizationOutput(
            component_decisions=tuple(components),
            final_decision=expected["decision"],
            rule_id=final_rule,
            reason_code=final_rule,
            reason="synthetic structured-field rehearsal",
            matched_capability=components[0].matched_capability if len(components) == 1 else None,
            authority_source="TaskContract",
            authority_provenance={
                "authority_source": "TaskContract",
                "contract_identity": runtime["contract_task_id"],
                "capability_digest": None,
            },
        )
        record = build_raw_record(
            experiment_id="AUTH-COVERAGE-002-EXPLANATION-REHEARSAL",
            run_id="synthetic-no-production",
            scenario_id=runtime["scenario_id"],
            implementation=implementation,
            authorization_input=captured,
            authorization_output=output,
            start_timestamp="2026-09-25T00:00:00.000000Z",
            finish_timestamp="2026-09-25T00:00:00.000001Z",
            monotonic_sequence=sequence,
        )
        observed = score_raw_explanation(record, runtime, analysis[runtime["scenario_id"]])
        errors.append(observed)
        if not mutation_detected and len(components) == 2:
            bad_component = replace(components[1], rule_id="POL-M2-TASK-MISMATCH")
            bad_output = replace(output, component_decisions=(components[0], bad_component))
            bad_record = replace(record, authorization_output=bad_output)
            mutation_detected = bool(
                score_raw_explanation(bad_record, runtime, analysis[runtime["scenario_id"]])
            )
    result = {
        "audit_id": "AUTH-COVERAGE-002-EXPLANATION-COMPATIBILITY@1",
        "splits": ["DEV", "VALIDATION"],
        "record_count": len(errors),
        "complete": sum(not item for item in errors),
        "mutation_detected": mutation_detected,
        "production_calls": 0,
        "result": "PASS" if all(not item for item in errors) and mutation_detected else "FAIL",
    }
    (CORPUS / "analysis/explanation_compatibility.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if result["result"] != "PASS":
        raise SystemExit(result)


if __name__ == "__main__":
    main()
