"""Meaningful high-risk branch tests added after the substrate freeze."""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from safetybox.capabilities import Capability
from safetybox.research.auth_coverage_isolation import (
    PROHIBITED_MODULE_PREFIXES,
    IsolationViolation,
    RuntimeOnlyPackage,
    install_import_gate,
    isolation_attestation,
)
from safetybox.research.auth_coverage_raw import (
    RawAuthorizationError,
    RawAuthorizationInput,
    RawCapability,
    RawComponentInput,
    RawImplementationProvenance,
    RawRequest,
    RawSchemaError,
    canonical_json_bytes,
)
from safetybox.research.auth_coverage_reconcile import finalize_complete_raw_seal
from safetybox.research.auth_coverage_runner import (
    RunnerError,
    RuntimeScenario,
    runtime_scenario_from_mapping,
)
from safetybox.research.auth_coverage_state import RunState
from safetybox.research.exposure_ledger import (
    ExposureBinding,
    ExposureEvent,
    ExposureLedger,
    ExposureLedgerError,
    ExposureLedgerIntegrityError,
)


def _load_test_helpers(name: str, filename: str):  # type: ignore[no-untyped-def]
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_raw_helpers = _load_test_helpers("_auth002_raw_helpers", "test_auth_coverage_002_raw.py")
_reconcile_helpers = _load_test_helpers(
    "_auth002_reconcile_helpers", "test_auth_coverage_002_reconcile.py"
)
_runner_helpers = _load_test_helpers("_auth002_runner_helpers", "test_auth_coverage_002_runner.py")
make_record = _raw_helpers.make_record
_binding = _reconcile_helpers._binding
_manifest = _reconcile_helpers._manifest
_record = _reconcile_helpers._record
_state = _reconcile_helpers._state
_write_record = _reconcile_helpers._write_record
harness = _runner_helpers.harness
scenario = _runner_helpers.scenario


def _runtime_mapping() -> dict[str, object]:
    request = {
        "request_id": "r",
        "session_id": "s",
        "task_id": "t",
        "actor": "a",
        "action": "filesystem.read",
        "resource": "/x",
        "arguments": {},
    }
    return {
        "scenario_id": "opaque",
        "tool_class": "FILESYSTEM",
        "contract_task_id": "t",
        "contract_description": "test",
        "capabilities": [{"action": "filesystem.read", "resource": "/x"}],
        "request": request,
        "additional_components": [],
    }


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        lambda value: value.update(extra=True),
        lambda value: value.update(capabilities="not-array"),
        lambda value: value.update(capabilities=[{"action": "a"}]),
        lambda value: value.update(capabilities=[{"action": 1, "resource": "/x"}]),
        lambda value: value.update(additional_components="not-array"),
        lambda value: value.update(additional_components=[{"name": "x"}]),
        lambda value: value.update(
            additional_components=[{"name": 1, "request": value["request"]}]
        ),
        lambda value: value.update(scenario_id=1),
        lambda value: value.update(request={"bad": "shape"}),
        lambda value: value.update(request={**value["request"], "action": 1}),
    ],
)
def test_runtime_parser_fails_closed_for_every_schema_layer(mutation) -> None:  # type: ignore[no-untyped-def]
    if mutation is None:
        value: object = []
    else:
        value = _runtime_mapping()
        mutation(value)
    with pytest.raises((RunnerError, ValueError, TypeError)):
        runtime_scenario_from_mapping(value)


def test_runtime_package_symlink_jsonl_and_attestation_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    not_directory = tmp_path / "file"
    not_directory.write_text("x", encoding="utf-8")
    with pytest.raises(IsolationViolation, match="directory"):
        RuntimeOnlyPackage(not_directory).validate()

    root = tmp_path / "runtime"
    root.mkdir()
    source = tmp_path / "source.txt"
    source.write_text("x", encoding="utf-8")
    (root / "link.txt").symlink_to(source)
    with pytest.raises(IsolationViolation, match="symlink"):
        RuntimeOnlyPackage(root).validate()
    (root / "link.txt").unlink()

    journal = root / "events.jsonl"
    journal.write_text('{"safe":1}\n', encoding="utf-8")
    for name in tuple(sys.modules):
        if any(
            name == prefix or name.startswith(f"{prefix}.") for prefix in PROHIBITED_MODULE_PREFIXES
        ):
            monkeypatch.delitem(sys.modules, name, raising=False)
    assert isolation_attestation(root)["analysis_artifacts_present"] is False
    journal.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(IsolationViolation, match="not valid"):
        RuntimeOnlyPackage(root).validate()


def test_import_gate_blocks_every_prohibited_namespace_without_duplicate_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in tuple(sys.modules):
        if any(
            name == prefix or name.startswith(f"{prefix}.") for prefix in PROHIBITED_MODULE_PREFIXES
        ):
            monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setattr(sys, "meta_path", [])
    install_import_gate()
    assert len(sys.meta_path) == 1
    finder = sys.meta_path[0]
    assert finder.find_spec("safe_runtime_module") is None
    for prefix in PROHIBITED_MODULE_PREFIXES:
        with pytest.raises(IsolationViolation, match="prohibited execution-process import"):
            finder.find_spec(f"{prefix}.nested")
    install_import_gate()
    assert len(sys.meta_path) == 1


def test_exact_inventory_rejects_outside_path_and_prohibited_open(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    safe = root / "safe.json"
    safe.write_text("{}\n", encoding="utf-8")
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    with pytest.raises(IsolationViolation, match="outside"):
        RuntimeOnlyPackage(root).validate_exact((outside,))
    labels = root / "labels"
    labels.mkdir()
    (labels / "key.bin").write_bytes(b"x")
    with pytest.raises(IsolationViolation, match="analysis artifact"):
        RuntimeOnlyPackage(root).open_binary("labels/key.bin")


def test_complete_reconciliation_seal_finalization_and_idempotence(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    state = _state(tmp_path, manifest)
    ledger = ExposureLedger(tmp_path / "ledger.jsonl")
    raw = tmp_path / "raw.jsonl"
    binding = _binding(manifest, manifest.scenario_order[0])
    record = _record(manifest, binding.scenario_id)
    ledger.reserve(binding)
    ledger.mark_started(binding)
    state.mark_call_boundary(binding.scenario_id)
    _write_record(raw, record)
    ledger.complete(binding, details={"record_digest": record.record_digest, "raw_sequence": 0})
    state.transition(RunState.COMPLETED_RAW)
    raw_manifest = tmp_path / "sealed/raw_manifest.json"
    first = finalize_complete_raw_seal(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw,
        run_metadata_path=manifest_path(tmp_path, manifest),
        raw_manifest_path=raw_manifest,
    )
    second = finalize_complete_raw_seal(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=raw,
        run_metadata_path=manifest_path(tmp_path, manifest),
        raw_manifest_path=raw_manifest,
    )
    assert first == second
    assert state.load().state is RunState.SEALED_RAW


def manifest_path(tmp_path: Path, manifest) -> Path:  # type: ignore[no-untyped-def]
    path = tmp_path / "run_metadata.json"
    if not path.exists():
        path.write_text(json.dumps(manifest.as_dict(), sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_complete_seal_refuses_wrong_state(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    state = _state(tmp_path, manifest)
    with pytest.raises(ValueError, match="COMPLETED_RAW"):
        finalize_complete_raw_seal(
            manifest=manifest,
            state=state,
            ledger=ExposureLedger(tmp_path / "ledger.jsonl"),
            raw_path=tmp_path / "raw.jsonl",
            run_metadata_path=manifest_path(tmp_path, manifest),
            raw_manifest_path=tmp_path / "raw_manifest.json",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("experiment_id", ""),
        ("scenario_count", 2),
        ("scenario_order", ("opaque-dev-0", "opaque-dev-0")),
        ("concurrency_policy", "PARALLEL"),
        ("ordering_policy", "RANDOM"),
        ("manifest_id", "OTHER"),
        ("runner_version", "OTHER"),
        ("protocol_id", "OTHER"),
        ("production_component", "OTHER"),
        ("raw_schema_version", "OTHER"),
        ("ledger_version", "OTHER"),
        ("implementation_sha", "bad"),
        ("split", "TEST"),
        ("environment", (("secret", "value"),)),
    ],
)
def test_run_manifest_rejects_dangerous_binding_variants(
    tmp_path: Path, field: str, value: object
) -> None:
    manifest = _manifest(tmp_path)
    with pytest.raises(ValueError):
        replace(manifest, **{field: value})


@pytest.mark.parametrize(
    "value",
    [
        None,
        {},
        {"component": "x"},
        {
            "component": "x",
            "corpus_id": "c",
            "experiment_id": "e",
            "implementation_sha": "s",
            "run_id": "r",
            "scenario_id": "i",
            "split": "DEV",
            "token": 1,
        },
    ],
)
def test_exposure_binding_parser_rejects_malformed_values(value: object) -> None:
    with pytest.raises(ExposureLedgerIntegrityError):
        ExposureBinding.from_dict(value)


@pytest.mark.parametrize(
    "value",
    [
        None,
        {},
        {"binding": {}, "details": {}, "event_type": "RESERVED", "sequence": 0, "timestamp": "t"},
        {"binding": {}, "details": [], "event_type": "RESERVED", "sequence": 1, "timestamp": "t"},
        {"binding": {}, "details": {}, "event_type": "UNKNOWN", "sequence": 1, "timestamp": "t"},
    ],
)
def test_exposure_event_parser_rejects_malformed_values(value: object) -> None:
    with pytest.raises(ExposureLedgerIntegrityError):
        ExposureEvent.from_dict(value)


def test_runner_order_digest_exhaustion_and_seal_guards(tmp_path: Path) -> None:
    item = harness(tmp_path / "wrong-order")
    with pytest.raises(RunnerError, match="next frozen"):
        item.runner.execute_scenario(replace(scenario(), scenario_id="other"))

    item = harness(tmp_path / "wrong-digest")
    with pytest.raises(RunnerError, match="input differs"):
        item.runner.execute_scenario(
            replace(scenario(), capabilities=(Capability("filesystem.read", "/changed"),))
        )

    item = harness(tmp_path / "seal-before")
    with pytest.raises(RunnerError, match="forbidden"):
        item.runner.seal_raw(
            raw_manifest_path=tmp_path / "seal-before/raw-manifest.json",
            run_metadata_path=item.metadata,
        )

    item = harness(tmp_path / "exhausted")
    item.runner.execute_scenario(scenario())
    with pytest.raises(RunnerError, match="exhausted"):
        item.runner.execute_scenario(scenario())


def test_runtime_scenario_rejects_empty_identity() -> None:
    parsed = runtime_scenario_from_mapping(_runtime_mapping())
    with pytest.raises(ValueError, match="must not be empty"):
        RuntimeScenario(
            scenario_id="",
            tool_class=parsed.tool_class,
            contract_task_id=parsed.contract_task_id,
            contract_description=parsed.contract_description,
            capabilities=parsed.capabilities,
            request=parsed.request,
        )


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), {1: "non-string-key"}, object()],
)
def test_raw_canonicalization_rejects_ambiguous_or_contaminated_values(value: object) -> None:
    with pytest.raises(RawSchemaError):
        canonical_json_bytes(value)


def test_raw_input_structural_guards_are_fail_closed() -> None:
    capability = RawCapability(0, "read", "/x", "/x", "task", "digest")
    request = make_record().authorization_input.primary.request
    component = RawComponentInput(0, "primary", request)
    invalid_capabilities = (
        (-1, "read", "/x", "/x", "task", "digest"),
        (0, "", "/x", "/x", "task", "digest"),
        (0, "read", "/x", "/other", "task", "digest"),
    )
    for invalid in invalid_capabilities:
        with pytest.raises(RawSchemaError):
            RawCapability(*invalid)
    with pytest.raises(RawSchemaError, match="prohibited benchmark metadata"):
        RawRequest("r", "s", "t", "a", "read", "/x", {"difficulty": "HARD"})
    with pytest.raises(RawSchemaError, match="component index"):
        replace(component, index=-1)
    with pytest.raises(RawSchemaError, match="capability indexes"):
        RawAuthorizationInput(
            "tool", "task", "", (replace(capability, received_index=1),), (component,)
        )
    with pytest.raises(RawSchemaError, match="task binding"):
        RawAuthorizationInput("tool", "other-task", "", (capability,), (component,))
    with pytest.raises(RawSchemaError, match="component indexes"):
        RawAuthorizationInput("tool", "task", "", (capability,), (replace(component, index=1),))
    with pytest.raises(RawSchemaError, match="primary component"):
        RawAuthorizationInput("tool", "task", "", (capability,), ())


def test_raw_output_and_record_cross_field_guards_are_fail_closed() -> None:
    record = make_record()
    decision = record.authorization_output.component_decisions[0]
    matched = record.authorization_output.matched_capability
    assert matched is not None
    with pytest.raises(RawSchemaError, match="matched capability index"):
        replace(matched, received_index=-1)
    with pytest.raises(RawSchemaError, match="decision index"):
        replace(decision, index=-1)
    with pytest.raises(RawSchemaError, match="unsupported component"):
        replace(decision, decision="MAYBE")
    with pytest.raises(RawSchemaError, match="unsupported final"):
        replace(record.authorization_output, final_decision="MAYBE")
    error = RawAuthorizationError("FAILED", "Synthetic", "message", False)
    with pytest.raises(RawSchemaError, match="DECISION_UNKNOWN"):
        replace(record.authorization_output, error=error)
    with pytest.raises(RawSchemaError, match="contiguous ordered"):
        replace(record.authorization_output, component_decisions=(replace(decision, index=1),))
    with pytest.raises(RawSchemaError, match="schema identity"):
        replace(record, schema_id="OTHER")
    with pytest.raises(RawSchemaError, match="canonical serialization"):
        replace(record, canonical_serialization="OTHER")
    with pytest.raises(RawSchemaError, match="monotonic_sequence"):
        replace(record, monotonic_sequence=-1)
    extra = replace(decision, index=1, component="extra")
    two_decisions = replace(record.authorization_output, component_decisions=(decision, extra))
    with pytest.raises(RawSchemaError, match="corresponding input"):
        replace(record, authorization_output=two_decisions)
    with pytest.raises(RawSchemaError, match="name does not match"):
        replace(
            record,
            authorization_output=replace(
                record.authorization_output,
                component_decisions=(replace(decision, component="other"),),
            ),
        )
    outside = replace(matched, received_index=len(record.authorization_input.capabilities))
    with pytest.raises(RawSchemaError, match="outside received"):
        replace(
            record,
            authorization_output=replace(record.authorization_output, matched_capability=outside),
        )
    changed = replace(matched, action="different")
    with pytest.raises(RawSchemaError, match="differs"):
        replace(
            record,
            authorization_output=replace(record.authorization_output, matched_capability=changed),
        )


def test_raw_implementation_requires_source_binding() -> None:
    implementation = make_record().implementation
    with pytest.raises(RawSchemaError, match="source checksum"):
        RawImplementationProvenance(
            implementation.production_git_sha,
            {},
            implementation.policy_version,
            implementation.task_contract_schema_version,
            implementation.authorization_spec_version,
            implementation.runner_git_sha,
            implementation.runner_version,
        )


def test_ledger_json_and_identity_guards_are_fail_closed() -> None:
    import safetybox.research.exposure_ledger as ledger_module

    item = _binding(_manifest(Path("/tmp")), "scenario")
    with pytest.raises(ExposureLedgerError, match="previous_digest"):
        ledger_module.event_digest(
            "bad", ExposureEvent(1, ledger_module.ExposureEventType.RESERVED, item, "t", {})
        )
    for invalid in ({1: "bad"}, {"float": 1.5}, {"nested": [object()]}):
        with pytest.raises(ExposureLedgerError):
            ledger_module.canonical_json(invalid)  # type: ignore[arg-type]
    with pytest.raises(ExposureLedgerError, match="non-empty"):
        replace(item, token="")
    base = ExposureEvent(1, ledger_module.ExposureEventType.RESERVED, item, "t", {}).to_dict()
    for field, value in (("sequence", True), ("timestamp", ""), ("details", {1: "bad"})):
        invalid = dict(base)
        invalid[field] = value
        with pytest.raises(ExposureLedgerIntegrityError):
            ExposureEvent.from_dict(invalid)
