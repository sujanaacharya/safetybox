from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from safetybox.authorization import AuthorizationComponent
from safetybox.capabilities import Capability
from safetybox.models import ActionRequest, PolicyDecision
from safetybox.research.auth_coverage_raw import (
    RawImplementationProvenance,
    canonical_json_bytes,
    canonical_sha256,
    capture_authorization_input,
    verify_raw_record,
)
from safetybox.research.auth_coverage_runner import (
    RUNNER_ID,
    CanonicalAuthorizationRunner,
    CrashPoint,
    InjectedCrash,
    RawPersistenceError,
    RawRecordWriter,
    RunnerError,
    RuntimeScenario,
    runtime_scenario_from_mapping,
    verify_raw_seal,
)
from safetybox.research.auth_coverage_state import (
    RunManifest,
    RunState,
    RunStateStore,
    canonical_json,
    sha256_file,
)
from safetybox.research.exposure_ledger import (
    DuplicateExposureError,
    ExposureBinding,
    ExposureEventType,
    ExposureLedger,
)


def scenario() -> RuntimeScenario:
    return RuntimeScenario(
        scenario_id="dev-opaque-7bd37f2b",
        tool_class="filesystem",
        contract_task_id="dev-task",
        contract_description="synthetic development authorization",
        capabilities=(
            Capability("filesystem.read", "/workspace/dev/**"),
            Capability("filesystem.write", "/workspace/output/**"),
        ),
        request=ActionRequest(
            request_id="dev-request",
            session_id="dev-session",
            task_id="dev-task",
            actor="dev-agent",
            action="filesystem.read",
            resource="/workspace/dev/input.txt",
            arguments={"encoding": "utf-8"},
        ),
    )


def scenario_json(item: RuntimeScenario) -> dict[str, object]:
    def request_json(request: ActionRequest) -> dict[str, object]:
        return {
            "request_id": request.request_id,
            "session_id": request.session_id,
            "task_id": request.task_id,
            "actor": request.actor,
            "action": request.action,
            "resource": request.resource,
            "arguments": dict(request.arguments),
        }

    return {
        "scenario_id": item.scenario_id,
        "tool_class": item.tool_class,
        "contract_task_id": item.contract_task_id,
        "contract_description": item.contract_description,
        "capabilities": [
            {"action": capability.action, "resource": capability.resource}
            for capability in item.capabilities
        ],
        "request": request_json(item.request),
        "additional_components": [
            {"name": component.name, "request": request_json(component.request)}
            for component in item.additional_components
        ],
    }


def test_runtime_schema_rejects_ignored_component_metadata() -> None:
    value = scenario_json(scenario())
    value["additional_components"] = [
        {
            "name": "destination",
            "request": value["request"],
            "answer": "ALLOW",
        }
    ]
    with pytest.raises(RunnerError, match="component fields"):
        runtime_scenario_from_mapping(value)


@dataclass
class Harness:
    runner: CanonicalAuthorizationRunner
    manifest: RunManifest
    state: RunStateStore
    ledger: ExposureLedger
    raw: RawRecordWriter
    metadata: Path


def harness(
    tmp_path: Path,
    *,
    split: str = "DEV",
    factory=None,
    fixture_scenario: RuntimeScenario | None = None,
) -> Harness:
    tmp_path.mkdir(parents=True, exist_ok=True)
    runtime_directory = tmp_path / "runtime"
    runtime_directory.mkdir()
    runtime = runtime_directory / "runtime-package.json"
    scenarios = runtime_directory / "scenarios.json"
    corpus = runtime_directory / "corpus-manifest.json"
    source = tmp_path / "production-policy.py"
    metadata = tmp_path / "run_metadata.json"
    dev_scenario = fixture_scenario or scenario()
    input_digest = canonical_sha256(
        capture_authorization_input(
            tool_class=dev_scenario.tool_class,
            contract_task_id=dev_scenario.contract_task_id,
            contract_description=dev_scenario.contract_description,
            received_capabilities=dev_scenario.capabilities,
            primary_request=dev_scenario.request,
            additional_components=dev_scenario.additional_components,
        )
    )
    scenarios.write_text(json.dumps([scenario_json(dev_scenario)]) + "\n", encoding="utf-8")
    binding = {
        "corpus_id": "AUTH-COVERAGE-002-DEV-FIXTURES@1",
        "split": split,
        "scenario_ids": [dev_scenario.scenario_id],
        "scenario_input_digests": {dev_scenario.scenario_id: input_digest},
        "runtime_scenarios_checksum": sha256_file(scenarios),
    }
    runtime.write_text(json.dumps(binding) + "\n", encoding="utf-8")
    corpus.write_text(json.dumps(binding) + "\n", encoding="utf-8")
    source.write_text("# synthetic source binding\n", encoding="utf-8")
    metadata.write_text("{}\n", encoding="utf-8")
    governance = tmp_path / "governance"
    governance.mkdir()
    exposure_path = governance / "exposure_ledger.jsonl"
    manifest = RunManifest(
        experiment_id="AUTH-COVERAGE-002-DEV",
        protocol_id="AUTH-COVERAGE-002-EXECUTION-PROTOCOL@1",
        corpus_id="AUTH-COVERAGE-002-DEV-FIXTURES@1",
        split=split,
        run_id="dev-run",
        production_component="TaskContractPolicy.authorize",
        exposure_ledger_path=str(exposure_path),
        runtime_package_path=str(runtime),
        runtime_package_checksum=sha256_file(runtime),
        runtime_scenarios_path=str(scenarios),
        runtime_scenarios_checksum=sha256_file(scenarios),
        corpus_manifest_path=str(corpus),
        corpus_manifest_checksum=sha256_file(corpus),
        implementation_sha="1" * 40,
        implementation_artifacts=((str(source), sha256_file(source)),),
        policy_version="TaskContractPolicy@1",
        authorization_spec_version="AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1",
        task_contract_schema_version="TaskContract@1",
        runner_version=RUNNER_ID,
        runner_sha="2" * 64,
        raw_schema_version="AUTH-COVERAGE-002-RAW-SCHEMA@1",
        ledger_version="AUTH-COVERAGE-EXPOSURE-LEDGER@1",
        scenario_count=1,
        scenario_order=(dev_scenario.scenario_id,),
        scenario_input_digests=((dev_scenario.scenario_id, input_digest),),
    )
    metadata.write_bytes(canonical_json(manifest.as_dict()) + b"\n")
    state = RunStateStore(tmp_path / "run_state.json", manifest)
    state.create()
    state.transition(RunState.READY)
    state.transition(RunState.RUNNING_UNEXPOSED)
    ledger = ExposureLedger(exposure_path)
    raw = RawRecordWriter(tmp_path / "raw_decisions.jsonl")
    implementation = RawImplementationProvenance(
        production_git_sha=manifest.implementation_sha,
        source_artifact_checksums={str(source): sha256_file(source)},
        policy_version=manifest.policy_version,
        task_contract_schema_version=manifest.task_contract_schema_version,
        authorization_spec_version=manifest.authorization_spec_version,
        runner_git_sha=manifest.runner_sha,
        runner_version=RUNNER_ID,
    )
    runner = CanonicalAuthorizationRunner(
        manifest=manifest,
        implementation=implementation,
        state=state,
        ledger=ledger,
        raw_writer=raw,
        implementation_sha_provider=lambda: "1" * 40,
        purpose="CANONICAL_RUN" if split == "HELD_OUT" else "DEV_EXECUTION",
        authorizer_factory=factory,
    )
    return Harness(runner, manifest, state, ledger, raw, metadata)


def crashing_at(target: CrashPoint):
    def crash(point: CrashPoint) -> None:
        if point is target:
            raise InjectedCrash(target.value)

    return crash


def test_raw_first_end_to_end_seals_and_then_blocks_execution(tmp_path: Path) -> None:
    item = harness(tmp_path)
    record = item.runner.execute_scenario(scenario())
    reconstructed = verify_raw_record(record)
    assert reconstructed.received_capabilities == scenario().capabilities
    assert item.ledger.prediction_exposure_count(
        experiment_id=item.manifest.experiment_id, split="DEV"
    ) == 1
    assert [event.event_type for event in item.ledger.events()] == [
        ExposureEventType.RESERVED,
        ExposureEventType.STARTED,
        ExposureEventType.COMPLETED,
    ]

    raw_manifest = tmp_path / "raw_manifest.json"
    item.runner.seal_raw(raw_manifest_path=raw_manifest, run_metadata_path=item.metadata)
    assert item.state.load().state is RunState.SEALED_RAW
    assert verify_raw_seal(
        raw_manifest_path=raw_manifest,
        raw_path=item.raw.path,
        ledger=item.ledger,
        run_metadata_path=item.metadata,
    )
    with pytest.raises(Exception, match="additional production"):
        item.runner.execute_scenario(scenario())


def test_raw_seal_uses_stable_snapshot_of_shared_append_only_ledger(
    tmp_path: Path,
) -> None:
    item = harness(tmp_path)
    item.runner.execute_scenario(scenario())
    raw_manifest = tmp_path / "raw_manifest.json"
    original = item.runner.seal_raw(
        raw_manifest_path=raw_manifest,
        run_metadata_path=item.metadata,
    )
    unrelated = ExposureBinding(
        experiment_id="OTHER-DEV-EXPERIMENT",
        corpus_id="OTHER-DEV-CORPUS",
        split="DEV",
        run_id="other-run",
        scenario_id="opaque-other-scenario",
        component="OtherPolicy.authorize",
        implementation_sha="3" * 40,
        token="other-token",
    )
    item.ledger.reserve(unrelated)

    assert verify_raw_seal(
        raw_manifest_path=raw_manifest,
        raw_path=item.raw.path,
        ledger=item.ledger,
        run_metadata_path=item.metadata,
    )
    assert item.runner.seal_raw(
        raw_manifest_path=raw_manifest,
        run_metadata_path=item.metadata,
    ) == original


def test_compound_component_decisions_are_preserved_in_order(tmp_path: Path) -> None:
    base = scenario()
    compound = RuntimeScenario(
        scenario_id=base.scenario_id,
        tool_class=base.tool_class,
        contract_task_id=base.contract_task_id,
        contract_description=base.contract_description,
        capabilities=base.capabilities,
        request=base.request,
        additional_components=(
            AuthorizationComponent(
                "destination",
                ActionRequest(
                    request_id="dev-request-destination",
                    session_id="dev-session",
                    task_id="dev-task",
                    actor="dev-agent",
                    action="filesystem.write",
                    resource="/workspace/output/result.txt",
                ),
            ),
        ),
    )
    item = harness(tmp_path, fixture_scenario=compound)
    record = item.runner.execute_scenario(compound)
    assert [value.component for value in record.authorization_output.component_decisions] == [
        "primary",
        "destination",
    ]
    assert [value.decision for value in record.authorization_output.component_decisions] == [
        "ALLOW",
        "ALLOW",
    ]


@pytest.mark.parametrize(
    ("point", "exposures", "raw_count", "state"),
    [
        (CrashPoint.BEFORE_RESERVATION, 0, 0, RunState.RUNNING_UNEXPOSED),
        (CrashPoint.AFTER_RESERVATION, 0, 0, RunState.RUNNING_UNEXPOSED),
        (CrashPoint.IMMEDIATELY_BEFORE_PRODUCTION_CALL, 0, 0, RunState.RUNNING_UNEXPOSED),
        (CrashPoint.IMMEDIATELY_AFTER_PRODUCTION_CALL, 1, 0, RunState.RUNNING_EXPOSED),
        (CrashPoint.DURING_RAW_SERIALIZATION, 1, 0, RunState.RUNNING_EXPOSED),
        (CrashPoint.AFTER_RAW_WRITE, 1, 1, RunState.RUNNING_EXPOSED),
        (CrashPoint.BEFORE_FSYNC, 1, 1, RunState.RUNNING_EXPOSED),
        (CrashPoint.AFTER_FSYNC, 1, 1, RunState.RUNNING_EXPOSED),
        (CrashPoint.BEFORE_COMPLETION_EVENT, 1, 1, RunState.RUNNING_EXPOSED),
        (CrashPoint.AFTER_COMPLETION_EVENT, 1, 1, RunState.RUNNING_EXPOSED),
    ],
)
def test_crash_injection_matrix(
    tmp_path: Path,
    point: CrashPoint,
    exposures: int,
    raw_count: int,
    state: RunState,
) -> None:
    item = harness(tmp_path)
    with pytest.raises(InjectedCrash):
        item.runner.execute_scenario(scenario(), crash_hook=crashing_at(point))
    assert item.ledger.prediction_exposure_count(
        experiment_id=item.manifest.experiment_id, split="DEV"
    ) == exposures
    assert len(item.raw.records()) == raw_count
    assert item.state.load().state is state


def test_crash_during_seal_never_opens_scoring_boundary(tmp_path: Path) -> None:
    item = harness(tmp_path)
    item.runner.execute_scenario(scenario())
    with pytest.raises(InjectedCrash):
        item.runner.seal_raw(
            raw_manifest_path=tmp_path / "raw_manifest.json",
            run_metadata_path=item.metadata,
            crash_hook=crashing_at(CrashPoint.DURING_SEALING),
        )
    assert item.state.load().state is RunState.COMPLETED_RAW
    with pytest.raises(Exception, match="SEALED_RAW"):
        item.state.require_scoring_allowed()
    item.ledger.snapshot_to(tmp_path / "exposure_ledger.snapshot.jsonl")
    item.ledger.reserve(
        ExposureBinding(
            experiment_id="OTHER-DEV-EXPERIMENT",
            corpus_id="OTHER-DEV-CORPUS",
            split="DEV",
            run_id="other-run",
            scenario_id="other-opaque-id",
            component="OtherPolicy.authorize",
            implementation_sha="3" * 40,
            token="other-token",
        )
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/reconcile_auth_coverage_002.py",
            "--manifest",
            str(item.metadata),
            "--state",
            str(item.state.path),
            "--ledger",
            str(item.ledger.path),
            "--raw",
            str(item.raw.path),
            "--repair",
            "--complete-manifest",
            str(tmp_path / "raw_manifest.json"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert item.state.load().state is RunState.SEALED_RAW
    assert verify_raw_seal(
        raw_manifest_path=tmp_path / "raw_manifest.json",
        raw_path=item.raw.path,
        ledger=item.ledger,
        run_metadata_path=item.metadata,
    )


class SpyAuthorizer:
    def __init__(self, *, result: object = None, error: Exception | None = None) -> None:
        self.calls = 0
        self.result = result
        self.error = error

    def authorize(self, request: ActionRequest) -> PolicyDecision:
        del request
        self.calls += 1
        if self.error:
            raise self.error
        return cast(PolicyDecision, self.result)


def test_duplicate_token_and_scenario_fail_before_second_call(tmp_path: Path) -> None:
    from safetybox.policy import TaskContractPolicy

    spy = SpyAuthorizer()

    def factory(contract, components):
        del components
        production = TaskContractPolicy(contract)

        class Counting:
            def authorize(self, request):
                spy.calls += 1
                return production.authorize(request)

        return Counting()

    item = harness(tmp_path, factory=factory)
    token = "dev-single-use-token"
    with pytest.raises(InjectedCrash):
        item.runner.execute_scenario(
            scenario(),
            token=token,
            crash_hook=crashing_at(CrashPoint.IMMEDIATELY_AFTER_PRODUCTION_CALL),
        )
    assert spy.calls == 1
    with pytest.raises(DuplicateExposureError, match="token"):
        item.runner.execute_scenario(scenario(), token=token)
    with pytest.raises(DuplicateExposureError, match="scenario"):
        item.runner.execute_scenario(scenario(), token="different-dev-token")
    assert spy.calls == 1


def test_production_exception_is_unknown_exposed_and_terminal(tmp_path: Path) -> None:
    spy = SpyAuthorizer(error=RuntimeError("synthetic production failure"))
    item = harness(tmp_path, factory=lambda contract, components: spy)
    record = item.runner.execute_scenario(scenario())
    assert spy.calls == 1
    assert record.authorization_output.final_decision == "DECISION_UNKNOWN"
    assert record.authorization_output.error is not None
    assert item.state.load().state is RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE
    assert item.ledger.events()[-1].event_type is ExposureEventType.FAILED_AFTER_CALL


def test_malformed_return_is_unknown_not_coerced_to_deny(tmp_path: Path) -> None:
    spy = SpyAuthorizer(result={"decision": "DENY"})
    item = harness(tmp_path, factory=lambda contract, components: spy)
    record = item.runner.execute_scenario(scenario())
    assert record.authorization_output.final_decision == "DECISION_UNKNOWN"
    assert record.authorization_output.error is not None


class FailingRawWriter(RawRecordWriter):
    def append(self, record, crash_hook=lambda point: None):
        del record, crash_hook
        raise OSError("synthetic disk failure")


def test_raw_failure_after_call_is_exposed_and_cannot_rerun(tmp_path: Path) -> None:
    item = harness(tmp_path)
    item.runner.raw_writer = FailingRawWriter(item.raw.path)
    with pytest.raises(RawPersistenceError):
        item.runner.execute_scenario(scenario())
    assert item.ledger.prediction_exposure_count(
        experiment_id=item.manifest.experiment_id, split="DEV"
    ) == 1
    assert item.ledger.events()[-1].event_type is ExposureEventType.FAILED_AFTER_CALL
    assert item.state.load().state is RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE
    partial_manifest = tmp_path / "partial_raw_manifest.json"
    partial = item.runner.seal_partial_raw(
        partial_manifest_path=partial_manifest,
        run_metadata_path=item.metadata,
    )
    assert partial["complete_for_scoring"] is False
    assert partial["record_count"] == 0
    with pytest.raises(Exception, match="additional production"):
        item.runner.execute_scenario(scenario())


def test_implementation_change_refuses_before_reservation(tmp_path: Path) -> None:
    item = harness(tmp_path)
    item.runner.implementation_sha_provider = lambda: "9" * 40
    with pytest.raises(Exception, match="implementation SHA"):
        item.runner.execute_scenario(scenario())
    assert item.ledger.event_count == 0


def test_implementation_change_after_prediction_refuses_before_next_reservation(
    tmp_path: Path,
) -> None:
    item = harness(tmp_path)
    item.runner.execute_scenario(scenario())
    prior_event_count = item.ledger.event_count
    item.runner.implementation_sha_provider = lambda: "9" * 40
    with pytest.raises(Exception, match="implementation SHA"):
        item.runner.execute_scenario(scenario())
    assert item.ledger.event_count == prior_event_count


def test_heldout_custom_seam_and_ordinary_pytest_process_are_forbidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(RunnerError, match="custom"):
        harness(
            tmp_path / "custom",
            split="HELD_OUT",
            factory=lambda contract, components: object(),
        )

    with pytest.raises(RunnerError, match="fresh canonical process"):
        harness(tmp_path / "guard", split="HELD_OUT")

    monkeypatch.setenv("SAFETYBOX_CANONICAL_EXECUTION_PROCESS", "1")
    guarded = tmp_path / "pytest-guard"
    with pytest.raises(RunnerError, match="pytest"):
        harness(guarded, split="HELD_OUT")
    ledger_path = guarded / "governance" / "exposure_ledger.jsonl"
    assert not ledger_path.exists()


def test_raw_tamper_breaks_seal_verification(tmp_path: Path) -> None:
    item = harness(tmp_path)
    item.runner.execute_scenario(scenario())
    raw_manifest = tmp_path / "raw_manifest.json"
    item.runner.seal_raw(raw_manifest_path=raw_manifest, run_metadata_path=item.metadata)
    item.raw.path.write_bytes(item.raw.path.read_bytes().replace(b"ALLOW", b"DENYX", 1))
    assert not verify_raw_seal(
        raw_manifest_path=raw_manifest,
        raw_path=item.raw.path,
        ledger=item.ledger,
        run_metadata_path=item.metadata,
    )


def test_raw_and_manifest_cotamper_is_detected_by_ledger_cross_link(tmp_path: Path) -> None:
    item = harness(tmp_path)
    item.runner.execute_scenario(scenario())
    raw_manifest = tmp_path / "raw_manifest.json"
    item.runner.seal_raw(raw_manifest_path=raw_manifest, run_metadata_path=item.metadata)

    raw_value = json.loads(item.raw.path.read_text(encoding="utf-8"))
    raw_value["authorization_output"]["reason"] = "tampered but internally rehashed"
    raw_value["output_digest"] = canonical_sha256(raw_value["authorization_output"])
    raw_value["record_digest"] = canonical_sha256(
        {key: value for key, value in raw_value.items() if key != "record_digest"}
    )
    item.raw.path.write_bytes(canonical_json_bytes(raw_value) + b"\n")
    seal_value = json.loads(raw_manifest.read_text(encoding="utf-8"))
    seal_value["raw_package_checksum"] = sha256_file(item.raw.path)
    raw_manifest.write_bytes(canonical_json(seal_value) + b"\n")

    assert not verify_raw_seal(
        raw_manifest_path=raw_manifest,
        raw_path=item.raw.path,
        ledger=item.ledger,
        run_metadata_path=item.metadata,
    )


def test_fresh_process_runner_cli_executes_dev_rehearsal_raw_first(tmp_path: Path) -> None:
    item = harness(tmp_path)
    manifest_path = Path(item.manifest.runtime_package_path).parent / "run_manifest.json"
    manifest_path.write_bytes(canonical_json(item.manifest.as_dict()) + b"\n")
    outputs = tmp_path / "cli-results"
    outputs.mkdir()
    cli_state = outputs / "cli_state.json"
    cli_ledger = ExposureLedger(item.manifest.exposure_ledger_path)
    cli_raw = outputs / "cli_raw.jsonl"
    cli_seal = outputs / "cli_raw_manifest.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/run_auth_coverage_002.py",
            "--manifest",
            str(manifest_path),
            "--scenarios",
            item.manifest.runtime_scenarios_path,
            "--state",
            str(cli_state),
            "--ledger",
            str(cli_ledger.path),
            "--raw",
            str(cli_raw),
            "--raw-manifest",
            str(cli_seal),
            "--implementation-sha",
            item.manifest.implementation_sha,
            "--dev-rehearsal",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert RawRecordWriter(cli_raw).records()[0].scenario_id == scenario().scenario_id
    assert cli_ledger.prediction_exposure_count(
        experiment_id=item.manifest.experiment_id,
        split=item.manifest.split,
    ) == 1
    assert RunStateStore(cli_state, item.manifest).load().state is RunState.SEALED_RAW
