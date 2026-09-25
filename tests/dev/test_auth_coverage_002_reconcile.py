"""Synthetic DEV reconciliation tests; no held-out corpus or labels exist here."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from safetybox.capabilities import Capability
from safetybox.models import ActionRequest
from safetybox.research.auth_coverage_raw import (
    RawAuthorizationOutput,
    RawImplementationProvenance,
    build_raw_record,
    canonical_sha256,
    capture_authorization_input,
    raw_record_json,
)
from safetybox.research.auth_coverage_reconcile import (
    ReconciliationStatus,
    reconcile_run,
    seal_reconciled_partial,
)
from safetybox.research.auth_coverage_state import (
    RunManifest,
    RunState,
    RunStateStore,
    sha256_file,
)
from safetybox.research.auth_coverage_state import (
    canonical_json as state_canonical_json,
)
from safetybox.research.exposure_ledger import (
    GENESIS_DIGEST,
    LEDGER_VERSION,
    ExposureBinding,
    ExposureEvent,
    ExposureEventType,
    ExposureLedger,
    canonical_json,
    event_digest,
)


def _manifest(tmp_path: Path, *, scenario_count: int = 1) -> RunManifest:
    runtime = tmp_path / "runtime.json"
    scenarios = tmp_path / "scenarios.json"
    corpus = tmp_path / "corpus.json"
    source = tmp_path / "policy.py"
    authorization_input = capture_authorization_input(
        tool_class="filesystem",
        contract_task_id="dev-task",
        contract_description="synthetic reconciliation input",
        received_capabilities=(Capability("filesystem.read", "/dev/**"),),
        primary_request=ActionRequest(
            request_id="request-one",
            session_id="session-one",
            task_id="dev-task",
            actor="synthetic-agent",
            action="filesystem.read",
            resource="/dev/input",
            arguments={},
        ),
    )
    input_digest = canonical_sha256(authorization_input)
    scenario_ids = [f"opaque-dev-{index}" for index in range(scenario_count)]
    scenarios.write_text("[]\n", encoding="utf-8")
    binding = {
        "corpus_id": "AUTH-COVERAGE-002-DEV-FIXTURES@1",
        "split": "DEV",
        "scenario_ids": scenario_ids,
        "scenario_input_digests": {
            scenario_id: input_digest for scenario_id in scenario_ids
        },
        "runtime_scenarios_checksum": sha256_file(scenarios),
    }
    runtime.write_text(json.dumps(binding) + "\n", encoding="utf-8")
    corpus.write_text(json.dumps(binding) + "\n", encoding="utf-8")
    source.write_text("# synthetic development artifact\n", encoding="utf-8")
    return RunManifest(
        experiment_id="AUTH-COVERAGE-002-DEV",
        protocol_id="AUTH-COVERAGE-002-EXECUTION-PROTOCOL@1",
        corpus_id="AUTH-COVERAGE-002-DEV-FIXTURES@1",
        split="DEV",
        run_id="reconciliation-dev-run",
        production_component="TaskContractPolicy.authorize",
        exposure_ledger_path=str(tmp_path / "ledger.jsonl"),
        runtime_package_path=str(runtime),
        runtime_package_checksum=sha256_file(runtime),
        runtime_scenarios_path=str(scenarios),
        runtime_scenarios_checksum=sha256_file(scenarios),
        corpus_manifest_path=str(corpus),
        corpus_manifest_checksum=sha256_file(corpus),
        implementation_sha="a" * 40,
        implementation_artifacts=((str(source), sha256_file(source)),),
        policy_version="TASK-CONTRACT-POLICY@1",
        authorization_spec_version="AUTHORIZATION-SPEC@1",
        task_contract_schema_version="TASK-CONTRACT@1",
        runner_version="AUTH-COVERAGE-002-RUNNER@1",
        runner_sha="b" * 64,
        raw_schema_version="AUTH-COVERAGE-002-RAW-SCHEMA@1",
        ledger_version="AUTH-COVERAGE-EXPOSURE-LEDGER@1",
        scenario_count=scenario_count,
        scenario_order=tuple(f"opaque-dev-{index}" for index in range(scenario_count)),
        scenario_input_digests=tuple(
            (scenario_id, input_digest) for scenario_id in scenario_ids
        ),
    )


def _state(tmp_path: Path, manifest: RunManifest) -> RunStateStore:
    state = RunStateStore(tmp_path / "state.json", manifest)
    state.create()
    state.transition(RunState.READY)
    state.transition(RunState.RUNNING_UNEXPOSED)
    return state


def _binding(
    manifest: RunManifest, scenario_id: str, *, token: str = "token-one"
) -> ExposureBinding:
    return ExposureBinding(
        experiment_id=manifest.experiment_id,
        corpus_id=manifest.corpus_id,
        split=manifest.split,
        run_id=manifest.run_id,
        scenario_id=scenario_id,
        component=manifest.production_component,
        implementation_sha=manifest.implementation_sha,
        token=token,
    )


def _record(manifest: RunManifest, scenario_id: str, *, sequence: int = 0):
    auth_input = capture_authorization_input(
        tool_class="filesystem",
        contract_task_id="dev-task",
        contract_description="synthetic reconciliation input",
        received_capabilities=(Capability("filesystem.read", "/dev/**"),),
        primary_request=ActionRequest(
            request_id="request-one",
            session_id="session-one",
            task_id="dev-task",
            actor="synthetic-agent",
            action="filesystem.read",
            resource="/dev/input",
            arguments={},
        ),
    )
    output = RawAuthorizationOutput(
        component_decisions=(),
        final_decision="DENY",
        rule_id="DEV-DENY",
        reason_code="DEV-DENY",
        reason="synthetic",
        matched_capability=None,
        authority_source="TaskContract",
        authority_provenance={"contract_identity": "dev-task"},
    )
    implementation = RawImplementationProvenance(
        production_git_sha=manifest.implementation_sha,
        source_artifact_checksums=dict(manifest.implementation_artifacts),
        policy_version=manifest.policy_version,
        task_contract_schema_version=manifest.task_contract_schema_version,
        authorization_spec_version=manifest.authorization_spec_version,
        runner_git_sha=manifest.runner_sha,
        runner_version=manifest.runner_version,
    )
    return build_raw_record(
        experiment_id=manifest.experiment_id,
        run_id=manifest.run_id,
        scenario_id=scenario_id,
        implementation=implementation,
        authorization_input=auth_input,
        authorization_output=output,
        start_timestamp="2026-09-25T00:00:00.000000Z",
        finish_timestamp="2026-09-25T00:00:00.000001Z",
        monotonic_sequence=sequence,
    )


def _write_record(path: Path, record: object) -> None:
    path.write_bytes(raw_record_json(record) + b"\n")  # type: ignore[arg-type]


def test_consistent_completed_evidence_is_reported_without_mutation(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    state = _state(tmp_path, manifest)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    raw_path = tmp_path / "raw.jsonl"
    binding = _binding(manifest, manifest.scenario_order[0])
    record = _record(manifest, binding.scenario_id)
    ledger.reserve(binding)
    ledger.mark_started(binding)
    state.mark_call_boundary(binding.scenario_id)
    _write_record(raw_path, record)
    ledger.complete(
        binding,
        details={"record_digest": record.record_digest, "raw_sequence": 0},
    )

    state.transition(RunState.COMPLETED_RAW)
    before = (ledger.path.read_bytes(), state.path.read_bytes(), raw_path.read_bytes())
    report = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw_path,
        repair=True,
    )

    assert report.statuses == (ReconciliationStatus.CONSISTENT_COMPLETE,)
    assert report.consistent and not report.changed
    assert report.exposure_count == report.raw_record_count == 1
    assert before == (ledger.path.read_bytes(), state.path.read_bytes(), raw_path.read_bytes())


def test_completed_prediction_in_active_run_is_terminalized_without_rerun(
    tmp_path: Path,
) -> None:
    manifest = _manifest(tmp_path, scenario_count=2)
    state = _state(tmp_path, manifest)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    raw_path = tmp_path / "raw.jsonl"
    binding = _binding(manifest, manifest.scenario_order[0])
    record = _record(manifest, binding.scenario_id)
    ledger.reserve(binding)
    ledger.mark_started(binding)
    state.mark_call_boundary(binding.scenario_id)
    _write_record(raw_path, record)
    ledger.complete(
        binding,
        details={"record_digest": record.record_digest, "raw_sequence": 0},
    )

    report = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw_path,
        repair=True,
    )
    assert report.statuses == (
        ReconciliationStatus.RUN_INTERRUPTED_AFTER_EXPOSURE,
    )
    assert state.load().state is RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE
    assert ledger.prediction_exposure_count(
        experiment_id=manifest.experiment_id,
        split=manifest.split,
    ) == 1


def test_reservation_without_start_is_terminated_before_call_idempotently(
    tmp_path: Path,
) -> None:
    manifest = _manifest(tmp_path)
    state = _state(tmp_path, manifest)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    binding = _binding(manifest, manifest.scenario_order[0])
    ledger.reserve(binding)

    first = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=tmp_path / "raw.jsonl",
        repair=True,
    )
    assert first.statuses == (ReconciliationStatus.RESERVED_NOT_EXPOSED,)
    assert first.changed
    snapshot = state.load()
    assert snapshot.state is RunState.ABORTED_BEFORE_PREDICTION
    assert snapshot.last_scenario_id == binding.scenario_id
    assert snapshot.reason == "RECONCILED_RESERVED_NOT_EXPOSED"
    assert [event.event_type for event in ledger.events()] == [
        ExposureEventType.RESERVED,
        ExposureEventType.FAILED_BEFORE_CALL,
        ExposureEventType.RECONCILED,
    ]
    assert ledger.prediction_exposure_count(
        experiment_id=manifest.experiment_id, split=manifest.split
    ) == 0

    count = ledger.event_count
    second = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=tmp_path / "raw.jsonl",
        repair=True,
    )
    assert second.statuses == (ReconciliationStatus.RESERVED_NOT_EXPOSED,)
    assert not second.changed
    assert ledger.event_count == count


@pytest.mark.parametrize(
    "initial_state",
    [RunState.CREATED, RunState.READY, RunState.RUNNING_UNEXPOSED],
)
def test_interruption_before_reservation_is_terminalized_without_exposure(
    tmp_path: Path, initial_state: RunState
) -> None:
    manifest = _manifest(tmp_path)
    state = RunStateStore(tmp_path / "state.json", manifest)
    state.create()
    if initial_state in {RunState.READY, RunState.RUNNING_UNEXPOSED}:
        state.transition(RunState.READY)
    if initial_state is RunState.RUNNING_UNEXPOSED:
        state.transition(RunState.RUNNING_UNEXPOSED)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")

    first = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=tmp_path / "raw.jsonl",
        repair=True,
    )
    assert first.statuses == (
        ReconciliationStatus.INTERRUPTED_BEFORE_RESERVATION,
    )
    assert first.changed
    snapshot = state.load()
    assert snapshot.state is RunState.ABORTED_BEFORE_PREDICTION
    assert snapshot.last_scenario_id is None
    assert snapshot.reason == "RECONCILED_INTERRUPTED_BEFORE_RESERVATION"
    assert ledger.event_count == 0

    second = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=tmp_path / "raw.jsonl",
        repair=True,
    )
    assert second.statuses == (
        ReconciliationStatus.INTERRUPTED_BEFORE_RESERVATION,
    )
    assert not second.changed and ledger.event_count == 0


def test_started_without_raw_is_conservatively_exposed_and_partial(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    state = _state(tmp_path, manifest)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    binding = _binding(manifest, manifest.scenario_order[0])
    ledger.reserve(binding)
    ledger.mark_started(binding)
    # Simulates interruption between durable STARTED and the state boundary.

    first = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=tmp_path / "raw.jsonl",
        repair=True,
    )
    assert ReconciliationStatus.EXPOSED_RAW_MISSING in first.statuses
    assert ReconciliationStatus.RUN_STATE_INCONSISTENT in first.statuses
    assert state.load().state is RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE
    assert [event.event_type for event in ledger.events()][-2:] == [
        ExposureEventType.FAILED_AFTER_CALL,
        ExposureEventType.RECONCILED,
    ]

    count = ledger.event_count
    second = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=tmp_path / "raw.jsonl",
        repair=True,
    )
    assert second.statuses == (ReconciliationStatus.EXPOSED_RAW_MISSING,)
    assert not second.changed and ledger.event_count == count


def test_durable_raw_without_completion_is_recovered_without_production_rerun(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = _manifest(tmp_path)
    state = _state(tmp_path, manifest)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    raw_path = tmp_path / "raw.jsonl"
    binding = _binding(manifest, manifest.scenario_order[0])
    record = _record(manifest, binding.scenario_id)
    ledger.reserve(binding)
    ledger.mark_started(binding)
    state.mark_call_boundary(binding.scenario_id)
    _write_record(raw_path, record)

    calls = 0

    def forbidden_authorization(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("reconciliation must never invoke production")

    monkeypatch.setattr(
        "safetybox.policy.TaskContractPolicy.authorize", forbidden_authorization
    )
    first = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw_path,
        repair=True,
    )
    assert first.statuses == (
        ReconciliationStatus.RUN_INTERRUPTED_AFTER_EXPOSURE,
        ReconciliationStatus.RAW_PRESENT_COMPLETION_EVENT_MISSING,
    )
    assert calls == 0
    assert state.load().state is RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE
    assert [event.event_type for event in ledger.events()][-2:] == [
        ExposureEventType.COMPLETED,
        ExposureEventType.RECONCILED,
    ]

    count = ledger.event_count
    second = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw_path,
        repair=True,
    )
    assert second.statuses == (
        ReconciliationStatus.CONSISTENT_PARTIAL_AFTER_EXPOSURE,
    )
    assert not second.changed and ledger.event_count == count and calls == 0


def test_raw_digest_corruption_is_preserved_while_run_is_terminalized(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    state = _state(tmp_path, manifest)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    raw_path = tmp_path / "raw.jsonl"
    binding = _binding(manifest, manifest.scenario_order[0])
    ledger.reserve(binding)
    ledger.mark_started(binding)
    state.mark_call_boundary(binding.scenario_id)
    record = json.loads(raw_record_json(_record(manifest, binding.scenario_id)))
    record["input_digest"] = "0" * 64
    raw_path.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    corrupted_bytes = raw_path.read_bytes()

    report = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw_path,
        repair=True,
    )
    assert report.statuses == (ReconciliationStatus.RAW_INVALID,)
    assert report.changed
    assert raw_path.read_bytes() == corrupted_bytes
    assert state.load().state is RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE
    assert ledger.event_count == 4


def test_torn_raw_tail_is_exposed_reconciled_and_forensically_sealed(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    state = _state(tmp_path, manifest)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    raw_path = tmp_path / "raw.jsonl"
    binding = _binding(manifest, manifest.scenario_order[0])
    ledger.reserve(binding)
    ledger.mark_started(binding)
    state.mark_call_boundary(binding.scenario_id)
    raw_path.write_bytes(b'{"torn":')

    report = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw_path,
        repair=True,
    )
    assert report.statuses == (ReconciliationStatus.RAW_INVALID,)
    assert report.exposure_count == 1
    assert state.load().state is RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE
    assert ExposureEventType.FAILED_AFTER_CALL in {
        event.event_type for event in ledger.events()
    }

    metadata = tmp_path / "run_metadata.json"
    metadata.write_bytes(state_canonical_json(manifest.as_dict()) + b"\n")
    partial_path = tmp_path / "partial_raw_manifest.json"
    partial = seal_reconciled_partial(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw_path,
        run_metadata_path=metadata,
        partial_manifest_path=partial_path,
    )
    assert partial["complete_for_scoring"] is False
    assert partial["reconciliation_statuses"] == ["RAW_INVALID"]


def test_valid_raw_with_mixed_implementation_provenance_is_rejected(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    state = _state(tmp_path, manifest)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    raw_path = tmp_path / "raw.jsonl"
    binding = _binding(manifest, manifest.scenario_order[0])
    original = _record(manifest, binding.scenario_id)
    altered = build_raw_record(
        experiment_id=original.experiment_id,
        run_id=original.run_id,
        scenario_id=original.scenario_id,
        implementation=replace(original.implementation, policy_version="MIXED-POLICY@2"),
        authorization_input=original.authorization_input,
        authorization_output=original.authorization_output,
        start_timestamp=original.start_timestamp,
        finish_timestamp=original.finish_timestamp,
        monotonic_sequence=original.monotonic_sequence,
    )
    ledger.reserve(binding)
    ledger.mark_started(binding)
    state.mark_call_boundary(binding.scenario_id)
    _write_record(raw_path, altered)

    report = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw_path,
        repair=True,
    )
    assert report.statuses == (
        ReconciliationStatus.RUN_INTERRUPTED_AFTER_EXPOSURE,
        ReconciliationStatus.RAW_PRESENT_COMPLETION_EVENT_MISSING,
        ReconciliationStatus.RAW_INVALID,
    )
    assert not report.changed and ledger.event_count == 2


def test_hash_chain_and_semantic_duplicate_exposure_are_detected(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, scenario_count=2)
    state = _state(tmp_path, manifest)
    path = tmp_path / "ledger.jsonl"
    ledger = ExposureLedger(path)
    first = _binding(manifest, manifest.scenario_order[0], token="token-one")
    second = _binding(manifest, manifest.scenario_order[1], token="token-two")
    ledger.reserve(first)
    ledger.mark_started(first)
    ledger.reserve(second)
    ledger.mark_started(second)

    decoded = [json.loads(line) for line in path.read_bytes().splitlines()]
    for envelope in decoded[2:]:
        envelope["event"]["binding"]["scenario_id"] = first.scenario_id
    previous = GENESIS_DIGEST
    rewritten: list[bytes] = []
    for envelope in decoded:
        event = ExposureEvent.from_dict(envelope["event"])
        envelope["previous_digest"] = previous
        envelope["event_digest"] = event_digest(previous, event)
        envelope["ledger_version"] = LEDGER_VERSION
        previous = envelope["event_digest"]
        rewritten.append(canonical_json(envelope))
    path.write_bytes(b"\n".join(rewritten) + b"\n")

    report = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=tmp_path / "raw.jsonl",
        repair=True,
    )
    assert report.statuses == (
        ReconciliationStatus.DUPLICATE_EXPOSURE,
        ReconciliationStatus.HASH_CHAIN_INVALID,
    )
    assert not report.changed


def test_completion_digest_mismatch_and_impossible_state_are_inconsistent(
    tmp_path: Path,
) -> None:
    manifest = _manifest(tmp_path)
    state = _state(tmp_path, manifest)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    raw_path = tmp_path / "raw.jsonl"
    binding = _binding(manifest, manifest.scenario_order[0])
    record = _record(manifest, binding.scenario_id)
    ledger.reserve(binding)
    ledger.mark_started(binding)
    _write_record(raw_path, record)
    ledger.complete(binding, details={"record_digest": "0" * 64, "raw_sequence": 0})

    report = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw_path,
    )
    assert report.statuses == (ReconciliationStatus.RUN_STATE_INCONSISTENT,)
    assert any("completion does not identify" in detail for detail in report.details)


def test_failed_after_call_with_durable_raw_repairs_only_the_state(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    state = _state(tmp_path, manifest)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    raw_path = tmp_path / "raw.jsonl"
    binding = _binding(manifest, manifest.scenario_order[0])
    record = _record(manifest, binding.scenario_id)
    ledger.reserve(binding)
    ledger.mark_started(binding)
    state.mark_call_boundary(binding.scenario_id)
    _write_record(raw_path, record)
    ledger.fail_after_call(binding, details={"error_type": "SyntheticProductionError"})

    report = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw_path,
        repair=True,
    )
    assert report.statuses == (
        ReconciliationStatus.RUN_INTERRUPTED_AFTER_EXPOSURE,
        ReconciliationStatus.RUN_STATE_INCONSISTENT,
    )
    assert report.repairs == ("RUN:PARTIAL_AFTER_PREDICTION_EXPOSURE",)
    assert state.load().state is RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE
    assert ledger.event_count == 3
    second = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw_path,
        repair=True,
    )
    assert second.statuses == (
        ReconciliationStatus.CONSISTENT_PARTIAL_AFTER_EXPOSURE,
    )
