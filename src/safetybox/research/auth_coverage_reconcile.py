"""Independent reconciliation for AUTH-COVERAGE-002 execution evidence.

The reconciler joins only the frozen run manifest, durable state snapshot,
exposure ledger, and raw JSONL records.  It has no production authorization
entry point.  Repair is deliberately narrow and append-only: it can terminate
an abandoned reservation, conservatively terminate an exposed call whose raw
record is missing, or attach a completion event to an already durable raw
record.  It never reconstructs a prediction by calling production.
"""

from __future__ import annotations

import hashlib
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from safetybox.research.auth_coverage_raw import (
    RawAuthorizationRecord,
    RawSchemaError,
    raw_record_from_json,
    verify_raw_record,
)
from safetybox.research.auth_coverage_state import (
    RunManifest,
    RunState,
    RunStateStore,
    canonical_json,
    exclusive_run_lock,
    sha256_file,
)
from safetybox.research.exposure_ledger import (
    ExposureBinding,
    ExposureEvent,
    ExposureEventType,
    ExposureLedger,
)


class ReconciliationStatus(StrEnum):
    """Frozen, deterministic reconciliation classifications."""

    CONSISTENT_COMPLETE = "CONSISTENT_COMPLETE"
    CONSISTENT_PARTIAL_AFTER_EXPOSURE = "CONSISTENT_PARTIAL_AFTER_EXPOSURE"
    INTERRUPTED_BEFORE_RESERVATION = "INTERRUPTED_BEFORE_RESERVATION"
    RUN_INTERRUPTED_AFTER_EXPOSURE = "RUN_INTERRUPTED_AFTER_EXPOSURE"
    RESERVED_NOT_EXPOSED = "RESERVED_NOT_EXPOSED"
    EXPOSED_RAW_MISSING = "EXPOSED_RAW_MISSING"
    RAW_PRESENT_COMPLETION_EVENT_MISSING = "RAW_PRESENT_COMPLETION_EVENT_MISSING"
    DUPLICATE_EXPOSURE = "DUPLICATE_EXPOSURE"
    HASH_CHAIN_INVALID = "HASH_CHAIN_INVALID"
    RUN_STATE_INCONSISTENT = "RUN_STATE_INCONSISTENT"
    RAW_INVALID = "RAW_INVALID"


PARTIAL_RAW_MANIFEST_ID = "AUTH-COVERAGE-002-PARTIAL-RAW-MANIFEST@1"
RAW_MANIFEST_ID = "AUTH-COVERAGE-002-RAW-MANIFEST@1"


_STATUS_ORDER = {status: index for index, status in enumerate(ReconciliationStatus)}


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    """Stable result of one read-only audit or narrowly scoped repair pass."""

    statuses: tuple[ReconciliationStatus, ...]
    exposure_count: int
    raw_record_count: int
    ledger_event_count: int
    repairs: tuple[str, ...] = ()
    details: tuple[str, ...] = ()

    @property
    def consistent(self) -> bool:
        return self.statuses == (ReconciliationStatus.CONSISTENT_COMPLETE,)

    @property
    def changed(self) -> bool:
        return bool(self.repairs)


@dataclass(frozen=True, slots=True)
class _Evidence:
    events: tuple[ExposureEvent, ...]
    records: tuple[RawAuthorizationRecord, ...]
    histories: dict[str, tuple[ExposureEvent, ...]]
    record_by_scenario: dict[str, RawAuthorizationRecord]


def verify_complete_sealed_evidence(
    *,
    manifest: RunManifest,
    records: tuple[RawAuthorizationRecord, ...],
    ledger: ExposureLedger,
) -> bool:
    """Cross-link immutable raw records to their hash-chained completion events."""
    if not ledger.verify_integrity().valid:
        return False
    if len(records) != manifest.scenario_count:
        return False
    if tuple(record.scenario_id for record in records) != manifest.scenario_order:
        return False
    if tuple(record.monotonic_sequence for record in records) != tuple(range(len(records))):
        return False
    expected_inputs = dict(manifest.scenario_input_digests)
    expected_artifacts = dict(manifest.implementation_artifacts)
    run_events = tuple(
        event
        for event in ledger.events()
        if event.binding.experiment_id == manifest.experiment_id
        and event.binding.run_id == manifest.run_id
    )
    histories: dict[str, list[ExposureEvent]] = defaultdict(list)
    for event in run_events:
        if not _binding_matches_manifest(event.binding, manifest):
            return False
        histories[event.binding.scenario_id].append(event)
    if set(histories) != set(manifest.scenario_order):
        return False
    records_by_id = {record.scenario_id: record for record in records}
    if len(records_by_id) != len(records):
        return False
    for record in records:
        try:
            verify_raw_record(record)
        except (RawSchemaError, ValueError):
            return False
        if (
            record.experiment_id != manifest.experiment_id
            or record.run_id != manifest.run_id
            or record.schema_id != manifest.raw_schema_version
            or record.input_digest != expected_inputs.get(record.scenario_id)
            or record.implementation.production_git_sha != manifest.implementation_sha
            or dict(record.implementation.source_artifact_checksums) != expected_artifacts
            or record.implementation.policy_version != manifest.policy_version
            or record.implementation.authorization_spec_version
            != manifest.authorization_spec_version
            or record.implementation.task_contract_schema_version
            != manifest.task_contract_schema_version
            or record.implementation.runner_git_sha != manifest.runner_sha
            or record.implementation.runner_version != manifest.runner_version
        ):
            return False
        history = histories[record.scenario_id]
        if [event.event_type for event in history] != [
            ExposureEventType.RESERVED,
            ExposureEventType.STARTED,
            ExposureEventType.COMPLETED,
        ]:
            return False
        completion = history[-1]
        if (
            completion.details.get("record_digest") != record.record_digest
            or completion.details.get("raw_sequence") != record.monotonic_sequence
        ):
            return False
    return True


def reconcile_run(
    *,
    manifest: RunManifest,
    state: RunStateStore,
    ledger: ExposureLedger,
    raw_path: Path,
    repair: bool = False,
    expected_ledger_head: str | None = None,
    expected_ledger_event_count: int | None = None,
) -> ReconciliationReport:
    with exclusive_run_lock(state.path):
        return _reconcile_run_locked(
            manifest=manifest,
            state=state,
            ledger=ledger,
            raw_path=raw_path,
            repair=repair,
            expected_ledger_head=expected_ledger_head,
            expected_ledger_event_count=expected_ledger_event_count,
        )


def _reconcile_run_locked(
    *,
    manifest: RunManifest,
    state: RunStateStore,
    ledger: ExposureLedger,
    raw_path: Path,
    repair: bool = False,
    expected_ledger_head: str | None = None,
    expected_ledger_event_count: int | None = None,
) -> ReconciliationReport:
    """Audit, and optionally reconcile, a run without invoking authorization.

    Ledger integrity is checked before any event is trusted.  When ``repair`` is
    true, all repairs are append-only and idempotent with respect to already
    reconciled histories.  A repaired post-call interruption always terminates
    the run as ``PARTIAL_AFTER_PREDICTION_EXPOSURE``; it is never restarted.
    """

    integrity = ledger.verify_integrity(
        expected_head=expected_ledger_head,
        expected_event_count=expected_ledger_event_count,
    )
    if not integrity.valid:
        statuses = {ReconciliationStatus.HASH_CHAIN_INVALID}
        if any(
            marker in error
            for error in integrity.errors
            for marker in (
                "single-use token",
                "scenario is already reserved",
                "start production twice",
            )
        ):
            statuses.add(ReconciliationStatus.DUPLICATE_EXPOSURE)
        return _report(
            statuses,
            exposure_count=0,
            raw_record_count=0,
            ledger_event_count=integrity.event_count,
            details=integrity.errors,
        )

    try:
        snapshot = state.load()
    except (OSError, ValueError, KeyError, TypeError) as error:
        return _report(
            {ReconciliationStatus.RUN_STATE_INCONSISTENT},
            exposure_count=ledger.prediction_exposure_count(
                experiment_id=manifest.experiment_id,
                split=manifest.split,
                corpus_id=manifest.corpus_id,
                component=manifest.production_component,
            ),
            raw_record_count=0,
            ledger_event_count=integrity.event_count,
            details=(f"run state cannot be loaded: {type(error).__name__}: {error}",),
        )

    raw_records, raw_errors = _load_raw_records(raw_path)
    if raw_errors:
        events = tuple(
            event
            for event in ledger.events()
            if event.binding.experiment_id == manifest.experiment_id
            and event.binding.run_id == manifest.run_id
        )
        invalid_histories_mutable: dict[str, list[ExposureEvent]] = defaultdict(list)
        for event in events:
            invalid_histories_mutable[event.binding.token].append(event)
        histories = {
            token: tuple(items) for token, items in invalid_histories_mutable.items()
        }
        evidence = _Evidence(
            events,
            raw_records,
            histories,
            {record.scenario_id: record for record in raw_records},
        )
        invalid_repairs: list[str] = []
        if repair and events:
            invalid_repairs.extend(_repair_histories(ledger, evidence))
            invalid_repairs.extend(_repair_state(state, evidence))
        return _report(
            {ReconciliationStatus.RAW_INVALID},
            exposure_count=sum(
                event.event_type is ExposureEventType.STARTED for event in events
            ),
            raw_record_count=len(raw_records),
            ledger_event_count=integrity.event_count,
            repairs=tuple(invalid_repairs),
            details=raw_errors,
        )

    events = tuple(
        event
        for event in ledger.events()
        if event.binding.experiment_id == manifest.experiment_id
        and event.binding.run_id == manifest.run_id
    )
    histories_mutable: dict[str, list[ExposureEvent]] = defaultdict(list)
    for event in events:
        histories_mutable[event.binding.token].append(event)
    histories = {token: tuple(items) for token, items in histories_mutable.items()}
    record_by_scenario = {record.scenario_id: record for record in raw_records}
    evidence = _Evidence(events, raw_records, histories, record_by_scenario)

    statuses, details = _classify(
        manifest, snapshot.state, snapshot.first_prediction_observed, evidence
    )
    repairs: list[str] = []
    actionable = statuses & {
        ReconciliationStatus.INTERRUPTED_BEFORE_RESERVATION,
        ReconciliationStatus.RUN_INTERRUPTED_AFTER_EXPOSURE,
        ReconciliationStatus.RESERVED_NOT_EXPOSED,
        ReconciliationStatus.EXPOSED_RAW_MISSING,
        ReconciliationStatus.RAW_PRESENT_COMPLETION_EVENT_MISSING,
    }
    failed_after_call = any(
        event.event_type is ExposureEventType.FAILED_AFTER_CALL for event in evidence.events
    )
    bindings_match = all(
        _binding_matches_manifest(history[0].binding, manifest)
        for history in evidence.histories.values()
    )
    if (
        repair
        and (actionable or failed_after_call)
        and bindings_match
        and not statuses
        & {
            ReconciliationStatus.DUPLICATE_EXPOSURE,
            ReconciliationStatus.HASH_CHAIN_INVALID,
            ReconciliationStatus.RAW_INVALID,
        }
    ):
        repairs.extend(_repair_histories(ledger, evidence))
        repairs.extend(_repair_state(state, evidence))

    return _report(
        statuses,
        exposure_count=sum(
            event.event_type is ExposureEventType.STARTED for event in evidence.events
        ),
        raw_record_count=len(raw_records),
        ledger_event_count=integrity.event_count,
        repairs=tuple(repairs),
        details=tuple(details),
    )


def _load_raw_records(
    raw_path: Path,
) -> tuple[tuple[RawAuthorizationRecord, ...], tuple[str, ...]]:
    if not raw_path.exists():
        return (), ()
    try:
        data = raw_path.read_bytes()
    except OSError as error:
        return (), (f"raw file cannot be read: {type(error).__name__}: {error}",)
    torn = bool(data and not data.endswith(b"\n"))
    complete_data = data
    if torn:
        complete_data = data.rsplit(b"\n", 1)[0]
        if complete_data:
            complete_data += b"\n"
    records: list[RawAuthorizationRecord] = []
    try:
        for line in complete_data.splitlines():
            record = raw_record_from_json(line)
            verify_raw_record(record)
            records.append(record)
    except (RawSchemaError, UnicodeDecodeError, ValueError) as error:
        return tuple(records), (f"raw record is invalid: {type(error).__name__}: {error}",)
    errors = ("raw JSONL ends with an incomplete record",) if torn else ()
    return tuple(records), errors


def _classify(
    manifest: RunManifest,
    run_state: RunState,
    first_prediction_observed: bool,
    evidence: _Evidence,
) -> tuple[set[ReconciliationStatus], list[str]]:
    statuses: set[ReconciliationStatus] = set()
    details: list[str] = []
    started_by_scenario: Counter[str] = Counter()

    for history in evidence.histories.values():
        reservation = history[0]
        binding = reservation.binding
        types = {event.event_type for event in history}
        started = ExposureEventType.STARTED in types
        started_by_scenario[binding.scenario_id] += int(started)
        record = evidence.record_by_scenario.get(binding.scenario_id)
        after_terminal = bool(
            {ExposureEventType.COMPLETED, ExposureEventType.FAILED_AFTER_CALL} & types
        )
        before_terminal = bool(
            {ExposureEventType.FAILED_BEFORE_CALL, ExposureEventType.ABORTED_BEFORE_CALL} & types
        )

        if not _binding_matches_manifest(binding, manifest):
            statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
            details.append(f"token {binding.token} binding differs from run manifest")
        if not started:
            statuses.add(ReconciliationStatus.RESERVED_NOT_EXPOSED)
            if record is not None or after_terminal:
                statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
                details.append(
                    f"scenario {binding.scenario_id} has post-call evidence without STARTED"
                )
            if not before_terminal:
                details.append(f"scenario {binding.scenario_id} reservation is unterminated")
            continue
        if record is None:
            statuses.add(ReconciliationStatus.EXPOSED_RAW_MISSING)
            if not after_terminal:
                details.append(f"scenario {binding.scenario_id} exposure has no terminal event")
            continue
        if not after_terminal:
            statuses.add(ReconciliationStatus.RAW_PRESENT_COMPLETION_EVENT_MISSING)
            details.append(
                f"scenario {binding.scenario_id} has durable raw evidence but no terminal event"
            )
        completed = next(
            (event for event in history if event.event_type is ExposureEventType.COMPLETED),
            None,
        )
        if completed is not None and (
            completed.details.get("record_digest") != record.record_digest
            or completed.details.get("raw_sequence") != record.monotonic_sequence
        ):
            statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
            details.append(
                f"scenario {binding.scenario_id} completion does not identify its raw record"
            )

    if any(count > 1 for count in started_by_scenario.values()):
        statuses.add(ReconciliationStatus.DUPLICATE_EXPOSURE)
        details.append("one or more scenarios have multiple STARTED events")

    _classify_raw(manifest, evidence, started_by_scenario, statuses, details)
    _classify_state(
        manifest,
        run_state,
        first_prediction_observed,
        evidence,
        statuses,
        details,
    )
    if not statuses:
        statuses.add(
            ReconciliationStatus.CONSISTENT_PARTIAL_AFTER_EXPOSURE
            if run_state is RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE
            else ReconciliationStatus.CONSISTENT_COMPLETE
        )
    return statuses, details


def _classify_raw(
    manifest: RunManifest,
    evidence: _Evidence,
    started_by_scenario: Counter[str],
    statuses: set[ReconciliationStatus],
    details: list[str],
) -> None:
    records = evidence.records
    scenario_counts = Counter(record.scenario_id for record in records)
    if any(count > 1 for count in scenario_counts.values()):
        statuses.add(ReconciliationStatus.RAW_INVALID)
        details.append("raw records contain a duplicate scenario")
    if tuple(record.monotonic_sequence for record in records) != tuple(range(len(records))):
        statuses.add(ReconciliationStatus.RAW_INVALID)
        details.append("raw record monotonic sequence has a gap or duplicate")
    if tuple(record.scenario_id for record in records) != manifest.scenario_order[: len(records)]:
        statuses.add(ReconciliationStatus.RAW_INVALID)
        details.append("raw records differ from the frozen manifest order")

    for record in records:
        expected_input_digest = dict(manifest.scenario_input_digests).get(record.scenario_id)
        if (
            record.experiment_id != manifest.experiment_id
            or record.run_id != manifest.run_id
            or record.implementation.production_git_sha != manifest.implementation_sha
            or dict(record.implementation.source_artifact_checksums)
            != dict(manifest.implementation_artifacts)
            or record.implementation.policy_version != manifest.policy_version
            or record.implementation.authorization_spec_version
            != manifest.authorization_spec_version
            or record.implementation.task_contract_schema_version
            != manifest.task_contract_schema_version
            or record.implementation.runner_git_sha != manifest.runner_sha
            or record.implementation.runner_version != manifest.runner_version
            or record.schema_id != manifest.raw_schema_version
            or record.input_digest != expected_input_digest
        ):
            statuses.add(ReconciliationStatus.RAW_INVALID)
            details.append(f"scenario {record.scenario_id} raw binding differs from run manifest")
        if started_by_scenario[record.scenario_id] != 1:
            statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
            details.append(f"scenario {record.scenario_id} raw record lacks one STARTED event")


def _classify_state(
    manifest: RunManifest,
    run_state: RunState,
    first_prediction_observed: bool,
    evidence: _Evidence,
    statuses: set[ReconciliationStatus],
    details: list[str],
) -> None:
    exposure_count = sum(
        event.event_type is ExposureEventType.STARTED for event in evidence.events
    )
    has_exposure = exposure_count > 0
    if run_state is RunState.RUNNING_EXPOSED and has_exposure:
        statuses.add(ReconciliationStatus.RUN_INTERRUPTED_AFTER_EXPOSURE)
        details.append("active exposed run must be terminalized after process interruption")
    if (
        run_state
        in {
            RunState.CREATED,
            RunState.READY,
            RunState.RUNNING_UNEXPOSED,
            RunState.ABORTED_BEFORE_PREDICTION,
        }
        and not evidence.events
    ):
        statuses.add(ReconciliationStatus.INTERRUPTED_BEFORE_RESERVATION)
        details.append("run ended before a durable exposure reservation")
    if first_prediction_observed != has_exposure:
        statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
        details.append("state first-prediction boundary disagrees with ledger exposure")
    if run_state in {RunState.CREATED, RunState.READY} and evidence.events:
        statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
        details.append(f"{run_state.value} state cannot have ledger events")
    if run_state is RunState.RUNNING_UNEXPOSED and has_exposure:
        statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
        details.append("RUNNING_UNEXPOSED state has a STARTED exposure")
    if run_state in {
        RunState.RUNNING_EXPOSED,
        RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE,
    } and not has_exposure:
        statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
        details.append(f"{run_state.value} state has no STARTED exposure")
    if run_state is RunState.ABORTED_BEFORE_PREDICTION and has_exposure:
        statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
        details.append("ABORTED_BEFORE_PREDICTION state has a STARTED exposure")
    if run_state is RunState.INVALID:
        statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
        details.append("run is explicitly INVALID")
    if any(
        event.event_type is ExposureEventType.FAILED_AFTER_CALL for event in evidence.events
    ) and run_state is not RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE:
        statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
        details.append("FAILED_AFTER_CALL evidence requires a partial terminal run state")

    sealed_states = {
        RunState.COMPLETED_RAW,
        RunState.SEALED_RAW,
        RunState.SCORING,
        RunState.COMPLETE,
    }
    if run_state in sealed_states:
        completed_scenarios = {
            history[0].binding.scenario_id
            for history in evidence.histories.values()
            if ExposureEventType.COMPLETED in {event.event_type for event in history}
        }
        expected = set(manifest.scenario_order)
        if (
            len(evidence.records) != manifest.scenario_count
            or completed_scenarios != expected
        ):
            statuses.add(ReconciliationStatus.RUN_STATE_INCONSISTENT)
            details.append(f"{run_state.value} state lacks a complete raw/ledger package")


def _repair_histories(ledger: ExposureLedger, evidence: _Evidence) -> list[str]:
    repairs: list[str] = []
    for history in evidence.histories.values():
        binding = history[0].binding
        types = {event.event_type for event in history}
        started = ExposureEventType.STARTED in types
        reconciled = ExposureEventType.RECONCILED in types
        after_terminal = bool(
            {ExposureEventType.COMPLETED, ExposureEventType.FAILED_AFTER_CALL} & types
        )
        before_terminal = bool(
            {ExposureEventType.FAILED_BEFORE_CALL, ExposureEventType.ABORTED_BEFORE_CALL} & types
        )
        record = evidence.record_by_scenario.get(binding.scenario_id)

        if not started:
            if not before_terminal:
                ledger.fail_before_call(
                    binding,
                    details={"error_type": "INTERRUPTED_BEFORE_PRODUCTION_CALL"},
                )
                repairs.append(f"{binding.scenario_id}:FAILED_BEFORE_CALL")
            if not reconciled:
                ledger.reconcile(binding, status="RESERVED_NOT_EXPOSED")
                repairs.append(f"{binding.scenario_id}:RECONCILED_RESERVED_NOT_EXPOSED")
            continue
        if record is None:
            if not after_terminal:
                ledger.fail_after_call(
                    binding,
                    details={"error_type": "EXPOSED_RESULT_INCOMPLETE"},
                )
                repairs.append(f"{binding.scenario_id}:FAILED_AFTER_CALL")
            if not reconciled:
                ledger.reconcile(binding, status="EXPOSED_RAW_MISSING")
                repairs.append(f"{binding.scenario_id}:RECONCILED_EXPOSED_RAW_MISSING")
            continue
        if not after_terminal:
            ledger.complete(
                binding,
                details={
                    "record_digest": record.record_digest,
                    "raw_sequence": record.monotonic_sequence,
                    "recovered_from_durable_raw": True,
                },
            )
            repairs.append(f"{binding.scenario_id}:COMPLETED_FROM_DURABLE_RAW")
            if not reconciled:
                ledger.reconcile(
                    binding,
                    status="RAW_PRESENT_COMPLETION_EVENT_MISSING",
                    details={"record_digest": record.record_digest},
                )
                repairs.append(
                    f"{binding.scenario_id}:RECONCILED_RAW_PRESENT_COMPLETION_EVENT_MISSING"
                )
    return repairs


def _repair_state(
    state: RunStateStore,
    evidence: _Evidence,
) -> list[str]:
    started = [
        event for event in evidence.events if event.event_type is ExposureEventType.STARTED
    ]
    scenario_id = (
        started[-1].binding.scenario_id
        if started
        else (
            next(iter(evidence.histories.values()))[0].binding.scenario_id
            if evidence.histories
            else None
        )
    )
    snapshot = state.load()
    if started:
        started_scenario_id = started[-1].binding.scenario_id
        if snapshot.state is RunState.RUNNING_UNEXPOSED:
            state.mark_call_boundary(started_scenario_id)
            snapshot = state.load()
        if snapshot.state is RunState.RUNNING_EXPOSED:
            state.mark_partial(
                started_scenario_id,
                "RECONCILED_AFTER_PREDICTION_EXPOSURE",
            )
            return ["RUN:PARTIAL_AFTER_PREDICTION_EXPOSURE"]
        return []
    if snapshot.state in {RunState.CREATED, RunState.READY, RunState.RUNNING_UNEXPOSED}:
        reason = (
            "RECONCILED_RESERVED_NOT_EXPOSED"
            if evidence.histories
            else "RECONCILED_INTERRUPTED_BEFORE_RESERVATION"
        )
        state.transition(
            RunState.ABORTED_BEFORE_PREDICTION,
            scenario_id=scenario_id,
            reason=reason,
        )
        return ["RUN:ABORTED_BEFORE_PREDICTION"]
    return []


def _binding_matches_manifest(binding: ExposureBinding, manifest: RunManifest) -> bool:
    return (
        binding.experiment_id == manifest.experiment_id
        and binding.corpus_id == manifest.corpus_id
        and binding.split == manifest.split
        and binding.run_id == manifest.run_id
        and binding.component == manifest.production_component
        and binding.implementation_sha == manifest.implementation_sha
        and binding.scenario_id in manifest.scenario_order
    )


def _report(
    statuses: set[ReconciliationStatus],
    *,
    exposure_count: int,
    raw_record_count: int,
    ledger_event_count: int,
    repairs: tuple[str, ...] = (),
    details: tuple[str, ...] = (),
) -> ReconciliationReport:
    return ReconciliationReport(
        statuses=tuple(sorted(statuses, key=_STATUS_ORDER.__getitem__)),
        exposure_count=exposure_count,
        raw_record_count=raw_record_count,
        ledger_event_count=ledger_event_count,
        repairs=repairs,
        details=details,
    )


def seal_reconciled_partial(
    *,
    manifest: RunManifest,
    state: RunStateStore,
    ledger: ExposureLedger,
    raw_path: Path,
    run_metadata_path: Path,
    partial_manifest_path: Path,
) -> dict[str, object]:
    """Freeze a terminal partial prefix without importing or invoking production."""
    with exclusive_run_lock(state.path):
        if state.load().state is not RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE:
            raise ValueError("partial sealing requires PARTIAL_AFTER_PREDICTION_EXPOSURE")
        report = _reconcile_run_locked(
            manifest=manifest,
            state=state,
            ledger=ledger,
            raw_path=raw_path,
            repair=False,
        )
        blocking = {
            ReconciliationStatus.HASH_CHAIN_INVALID,
            ReconciliationStatus.DUPLICATE_EXPOSURE,
            ReconciliationStatus.RUN_STATE_INCONSISTENT,
        }
        if set(report.statuses) & blocking:
            raise ValueError("partial evidence failed reconciliation")
        raw_digest = (
            sha256_file(raw_path) if raw_path.exists() else hashlib.sha256(b"").hexdigest()
        )
        ledger_snapshot = ledger.snapshot_to(
            partial_manifest_path.parent / "exposure_ledger.snapshot.jsonl"
        )
        value: dict[str, object] = {
            "raw_manifest_id": PARTIAL_RAW_MANIFEST_ID,
            "complete_for_scoring": False,
            "record_count": report.raw_record_count,
            "raw_package_checksum": raw_digest,
            "ledger_snapshot": ledger_snapshot.path.name,
            "ledger_checksum": sha256_file(ledger_snapshot.path),
            "ledger_anchor_checksum": sha256_file(ledger_snapshot.anchor_path),
            "ledger_head": ledger_snapshot.head,
            "ledger_event_count": ledger_snapshot.event_count,
            "run_metadata_checksum": sha256_file(run_metadata_path),
            "run_manifest_digest": manifest.digest,
            "run_state": RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE.value,
            "reconciliation_statuses": [status.value for status in report.statuses],
        }
        payload = canonical_json(value) + b"\n"
        if partial_manifest_path.exists():
            if partial_manifest_path.read_bytes() != payload:
                raise ValueError("existing partial manifest differs from recomputation")
            return value
        partial_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            partial_manifest_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(
            partial_manifest_path.parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return value


def finalize_complete_raw_seal(
    *,
    manifest: RunManifest,
    state: RunStateStore,
    ledger: ExposureLedger,
    raw_path: Path,
    run_metadata_path: Path,
    raw_manifest_path: Path,
) -> dict[str, object]:
    """Recover only the seal step after production has completely finished."""
    with exclusive_run_lock(state.path):
        current = state.load().state
        if current not in {RunState.COMPLETED_RAW, RunState.SEALED_RAW}:
            raise ValueError("complete seal finalization requires COMPLETED_RAW or SEALED_RAW")
        report = _reconcile_run_locked(
            manifest=manifest,
            state=state,
            ledger=ledger,
            raw_path=raw_path,
            repair=False,
        )
        if not report.consistent or report.raw_record_count != manifest.scenario_count:
            raise ValueError("complete evidence failed reconciliation")
        records, errors = _load_raw_records(raw_path)
        if errors:
            raise ValueError("complete raw evidence is invalid")
        ledger_snapshot = ledger.snapshot_to(
            raw_manifest_path.parent / "exposure_ledger.snapshot.jsonl"
        )
        if not verify_complete_sealed_evidence(
            manifest=manifest,
            records=records,
            ledger=ledger_snapshot,
        ):
            raise ValueError("complete raw evidence failed sealed cross-link verification")
        value: dict[str, object] = {
            "raw_manifest_id": RAW_MANIFEST_ID,
            "record_count": report.raw_record_count,
            "raw_package_checksum": sha256_file(raw_path),
            "ledger_snapshot": ledger_snapshot.path.name,
            "ledger_checksum": sha256_file(ledger_snapshot.path),
            "ledger_anchor_checksum": sha256_file(ledger_snapshot.anchor_path),
            "ledger_head": ledger_snapshot.head,
            "ledger_event_count": ledger_snapshot.event_count,
            "run_metadata_checksum": sha256_file(run_metadata_path),
            "run_manifest_digest": manifest.digest,
        }
        payload = canonical_json(value) + b"\n"
        if raw_manifest_path.exists():
            if raw_manifest_path.read_bytes() != payload:
                raise ValueError("existing raw manifest differs from recomputed seal")
        else:
            raw_manifest_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                raw_manifest_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            directory = os.open(
                raw_manifest_path.parent,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        if current is RunState.COMPLETED_RAW:
            state.transition(RunState.SEALED_RAW)
        return value
