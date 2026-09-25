"""Synthetic DEV proofs for AUTH-COVERAGE-EXPOSURE-LEDGER@1."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from safetybox.research.exposure_ledger import (
    GENESIS_DIGEST,
    LEDGER_VERSION,
    DuplicateExposureError,
    ExposureBinding,
    ExposureBindingError,
    ExposureEvent,
    ExposureEventType,
    ExposureLedger,
    ExposureLedgerError,
    ExposureLedgerIntegrityError,
    ExposurePresentError,
    ExposureTransitionError,
    canonical_json,
    event_digest,
    ledger_integrity,
    new_exposure_token,
    prediction_exposure_count,
    scenario_exposed,
    zero_exposure_gate,
)


def binding(
    *,
    token: str = "dev-token-001",
    scenario_id: str = "opaque-dev-id-a75cc70f",
    run_id: str = "dev-run-001",
    implementation_sha: str = "a" * 40,
) -> ExposureBinding:
    return ExposureBinding(
        experiment_id="AUTH-COVERAGE-002-DEV",
        corpus_id="AUTH-COVERAGE-002-DEV-MOCK-CORPUS@1",
        split="DEV",
        run_id=run_id,
        scenario_id=scenario_id,
        component="TaskContractPolicy.authorize",
        implementation_sha=implementation_sha,
        token=token,
    )


def timestamp(index: int) -> str:
    return f"2026-09-25T10:00:{index:02d}.000000Z"


def test_canonical_event_digest_is_order_independent_and_semantic(tmp_path: Path) -> None:
    first = canonical_json({"z": 1, "nested": {"b": 2, "a": "हिमाल"}})
    second = canonical_json({"nested": {"a": "हिमाल", "b": 2}, "z": 1})
    assert first == second
    assert first == (
        b'{"nested":{"a":"\xe0\xa4\xb9\xe0\xa4\xbf\xe0\xa4\xae\xe0\xa4\xbe\xe0\xa4\xb2",'
        b'"b":2},"z":1}'
    )

    base = ExposureEvent(1, ExposureEventType.RESERVED, binding(), timestamp(1), {"x": 1})
    reordered = ExposureEvent(1, ExposureEventType.RESERVED, binding(), timestamp(1), {"x": 1})
    changed = ExposureEvent(1, ExposureEventType.RESERVED, binding(), timestamp(1), {"x": 2})
    assert event_digest(GENESIS_DIGEST, base) == event_digest(GENESIS_DIGEST, reordered)
    assert event_digest(GENESIS_DIGEST, base) != event_digest(GENESIS_DIGEST, changed)


def test_durable_reserve_start_complete_chain_and_queries(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    item = binding()
    ledger.reserve(item, timestamp=timestamp(1))
    assert ledger.event_count == 1
    assert ledger.head != GENESIS_DIGEST
    assert prediction_exposure_count(ledger, experiment_id=item.experiment_id, split="DEV") == 0

    ledger.mark_started(item, timestamp=timestamp(2))
    ledger.complete(item, timestamp=timestamp(3), details={"raw_record_sequence": 1})

    assert [event.event_type for event in ledger.events()] == [
        ExposureEventType.RESERVED,
        ExposureEventType.STARTED,
        ExposureEventType.COMPLETED,
    ]
    assert ledger.event_count == 3
    assert scenario_exposed(ledger, item)
    assert scenario_exposed(ledger, replace(item, token="unused-query-token"))
    assert ledger.run_has_exposure(experiment_id=item.experiment_id, run_id=item.run_id)
    assert ledger.incomplete_exposure_count() == 0
    assert ledger.duplicate_exposure_count() == 0
    assert ledger.verify_integrity().valid


def test_reservation_is_fsynced_before_exposure_can_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import safetybox.research.exposure_ledger as module

    real_fsync = module.os.fsync
    synced: list[int] = []

    def recording_fsync(descriptor: int) -> None:
        synced.append(descriptor)
        real_fsync(descriptor)

    monkeypatch.setattr(module.os, "fsync", recording_fsync)
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    ledger.reserve(binding(), timestamp=timestamp(1))
    assert len(synced) >= 2  # new file and its parent directory
    ledger.mark_started(binding(), timestamp=timestamp(2))
    assert len(synced) >= 3


def test_failed_before_call_is_reserved_but_not_exposed(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    item = binding()
    ledger.reserve(item, timestamp=timestamp(1))
    ledger.fail_before_call(item, timestamp=timestamp(2), details={"reason": "DEV injection"})
    assert not ledger.scenario_exposed(item)
    assert ledger.prediction_exposure_count(experiment_id=item.experiment_id, split="DEV") == 0
    assert ledger.incomplete_exposure_count() == 0
    with pytest.raises(DuplicateExposureError):
        ledger.mark_started(item, timestamp=timestamp(3))


def test_failed_after_call_is_exposed_and_incomplete(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    item = binding()
    ledger.reserve(item, timestamp=timestamp(1))
    ledger.mark_started(item, timestamp=timestamp(2))
    ledger.fail_after_call(item, timestamp=timestamp(3), details={"raw_result": "missing"})
    assert ledger.scenario_exposed(item)
    assert ledger.incomplete_exposure_count() == 1
    with pytest.raises(DuplicateExposureError):
        ledger.mark_started(item, timestamp=timestamp(4))
    with pytest.raises(ExposureTransitionError):
        ledger.complete(item, timestamp=timestamp(4))


def test_single_use_token_cannot_change_any_binding_field(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    original = binding()
    ledger.reserve(original, timestamp=timestamp(1))
    for changed in (
        replace(original, experiment_id="OTHER-DEV"),
        replace(original, corpus_id="OTHER-DEV-CORPUS"),
        replace(original, split="VALIDATION"),
        replace(original, run_id="dev-run-002"),
        replace(original, scenario_id="opaque-dev-id-other"),
        replace(original, component="other.authorize"),
        replace(original, implementation_sha="b" * 40),
    ):
        with pytest.raises(ExposureBindingError):
            ledger.mark_started(changed, timestamp=timestamp(2))
    assert ledger.event_count == 1


def test_duplicate_token_and_same_scenario_different_token_are_rejected(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    original = binding()
    ledger.reserve(original, timestamp=timestamp(1))
    with pytest.raises(DuplicateExposureError):
        ledger.reserve(original, timestamp=timestamp(2))
    with pytest.raises(DuplicateExposureError):
        ledger.reserve(replace(original, token="dev-token-002"), timestamp=timestamp(2))
    assert ledger.event_count == 1


def test_distinct_scenarios_may_be_reserved_in_frozen_order(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    first = binding()
    second = binding(token="dev-token-002", scenario_id="opaque-dev-id-498762b1")
    ledger.reserve(first, timestamp=timestamp(1))
    ledger.reserve(second, timestamp=timestamp(2))
    assert [event.binding.scenario_id for event in ledger.events()] == [
        first.scenario_id,
        second.scenario_id,
    ]


def test_implementation_binding_refuses_mid_run_change(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    item = binding()
    ledger.reserve(item, timestamp=timestamp(1))
    with pytest.raises(ExposureBindingError):
        ledger.mark_started(replace(item, implementation_sha="f" * 40), timestamp=timestamp(2))
    assert ledger.prediction_exposure_count(experiment_id=item.experiment_id, split="DEV") == 0


def test_zero_exposure_gate_uses_exact_research_scope(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    item = binding()
    ledger.reserve(item, timestamp=timestamp(1))
    zero_exposure_gate(
        ledger,
        experiment_id=item.experiment_id,
        corpus_id=item.corpus_id,
        split=item.split,
        component=item.component,
    )
    ledger.mark_started(item, timestamp=timestamp(2))
    with pytest.raises(ExposurePresentError):
        zero_exposure_gate(
            ledger,
            experiment_id=item.experiment_id,
            corpus_id=item.corpus_id,
            split=item.split,
            component=item.component,
        )
    # A distinct exact scope is not contaminated by this DEV exposure.
    zero_exposure_gate(
        ledger,
        experiment_id=item.experiment_id,
        corpus_id="OTHER-DEV-CORPUS",
        split=item.split,
        component=item.component,
    )


def test_heldout_scope_is_atomically_bound_to_one_run(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    first = replace(binding(), split="HELD_OUT", run_id="canonical-run-one")
    with pytest.raises(ExposureBindingError, match="canonical-scope"):
        ledger.reserve(first)
    second_run = replace(
        first,
        token="heldout-token-two",
        run_id="canonical-run-two",
        scenario_id="opaque-heldout-id-two",
    )
    ledger.reserve_canonical_scope(first)
    with pytest.raises(ExposurePresentError, match="another run"):
        ledger.reserve_canonical_scope(second_run)
    assert ledger.event_count == 1


def test_hash_chain_detects_historical_replacement(tmp_path: Path) -> None:
    path = tmp_path / "exposure.jsonl"
    ledger = ExposureLedger(path)
    item = binding()
    ledger.reserve(item, timestamp=timestamp(1))
    ledger.mark_started(item, timestamp=timestamp(2))
    ledger.complete(item, timestamp=timestamp(3))

    records = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(records[0])
    first["event"]["timestamp"] = timestamp(9)
    records[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(records) + "\n", encoding="utf-8")

    result = ledger_integrity(ledger)
    assert not result.valid
    assert "digest does not match" in result.errors[0]
    with pytest.raises(ExposureLedgerIntegrityError):
        ledger.events()


def test_durable_head_and_count_anchor_detect_valid_suffix_deletion(tmp_path: Path) -> None:
    path = tmp_path / "exposure.jsonl"
    ledger = ExposureLedger(path)
    item = binding()
    ledger.reserve(item, timestamp=timestamp(1))
    ledger.mark_started(item, timestamp=timestamp(2))
    expected_head = ledger.head
    expected_count = ledger.event_count
    lines = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(lines[0])

    unanchored = ledger.verify_integrity()
    assert not unanchored.valid
    assert unanchored.errors == ("durable ledger anchor does not match history",)
    anchored = ledger.verify_integrity(
        expected_head=expected_head, expected_event_count=expected_count
    )
    assert not anchored.valid
    assert anchored.errors == ("durable ledger anchor does not match history",)


def test_stale_prefix_anchor_recovers_forward_without_losing_exposure(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    item = binding()
    ledger.reserve(item, timestamp=timestamp(1))
    prefix_anchor = ledger.anchor_path.read_bytes()
    ledger.mark_started(item, timestamp=timestamp(2))
    ledger.anchor_path.write_bytes(prefix_anchor)  # injected crash between two durable writes

    assert ledger.prediction_exposure_count(
        experiment_id=item.experiment_id, split=item.split
    ) == 1
    assert ledger.verify_integrity().valid
    assert json.loads(ledger.anchor_path.read_text(encoding="utf-8"))["event_count"] == 2


def test_first_event_recovers_from_durable_genesis_anchor(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    item = binding()
    ledger.reserve(item, timestamp=timestamp(1))
    ledger.anchor_path.write_bytes(
        canonical_json(
            {
                "event_count": 0,
                "head": GENESIS_DIGEST,
                "ledger_version": LEDGER_VERSION,
            }
        )
        + b"\n"
    )

    assert ledger.events() == (
        ExposureEvent(1, ExposureEventType.RESERVED, item, timestamp(1), {}),
    )
    assert ledger.verify_integrity().valid
    assert json.loads(ledger.anchor_path.read_text(encoding="utf-8"))["event_count"] == 1


def test_missing_anchor_after_nonempty_history_is_detected(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    ledger.reserve(binding(), timestamp=timestamp(1))
    ledger.anchor_path.unlink()
    assert not ledger.verify_integrity().valid


def test_snapshot_is_stable_prefix_when_shared_live_ledger_advances(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    first = binding()
    ledger.reserve(first, timestamp=timestamp(1))
    snapshot_path = tmp_path / "result" / "exposure.snapshot.jsonl"
    snapshot = ledger.snapshot_to(snapshot_path)
    snapshot_bytes = snapshot.path.read_bytes()

    second = binding(
        token="other-token",
        scenario_id="opaque-other-scenario",
        run_id="other-run",
    )
    ledger.reserve(second, timestamp=timestamp(2))
    recovered = ledger.snapshot_to(snapshot_path)
    assert recovered.path.read_bytes() == snapshot_bytes
    assert recovered.event_count == 1

    recovered.path.write_bytes(recovered.path.read_bytes().replace(b"dev-token", b"bad-token", 1))
    with pytest.raises(ExposureLedgerIntegrityError):
        ledger.snapshot_to(snapshot_path)


def test_partial_line_is_invalid_and_cannot_be_appended(tmp_path: Path) -> None:
    path = tmp_path / "exposure.jsonl"
    path.write_bytes(b'{"interrupted":true')
    ledger = ExposureLedger(path)
    assert not ledger.verify_integrity().valid
    with pytest.raises(ExposureLedgerIntegrityError):
        ledger.reserve(binding(), timestamp=timestamp(1))
    assert path.read_bytes() == b'{"interrupted":true'


def test_noncanonical_or_out_of_contract_json_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ExposureLedgerError):
        canonical_json({"floating_point_is_not_in_v1": 1.5})  # type: ignore[dict-item]

    path = tmp_path / "exposure.jsonl"
    path.write_text('{ "noncanonical": true }\n', encoding="utf-8")
    result = ExposureLedger(path).verify_integrity()
    assert not result.valid
    assert "not canonically serialized" in result.errors[0]


def test_reconciliation_is_idempotently_single_event_and_never_adds_exposure(
    tmp_path: Path,
) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    item = binding()
    ledger.reserve(item, timestamp=timestamp(1))
    ledger.fail_before_call(item, timestamp=timestamp(2))
    event = ledger.reconcile(item, status="RESERVED_NOT_EXPOSED", timestamp=timestamp(2))
    assert event.details == {"status": "RESERVED_NOT_EXPOSED"}
    assert not ledger.scenario_exposed(item)
    with pytest.raises(ExposureTransitionError):
        ledger.reconcile(item, status="RESERVED_NOT_EXPOSED", timestamp=timestamp(3))
    with pytest.raises(ExposureTransitionError):
        ledger.mark_started(item, timestamp=timestamp(3))


def test_reconciliation_requires_matching_terminal_evidence(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    item = binding()
    ledger.reserve(item, timestamp=timestamp(1))
    with pytest.raises(ExposureTransitionError, match="terminal"):
        ledger.reconcile(item, status="RESERVED_NOT_EXPOSED", timestamp=timestamp(2))
    ledger.fail_before_call(item, timestamp=timestamp(2))
    with pytest.raises(ExposureTransitionError, match="differs"):
        ledger.reconcile(item, status="EXPOSED_RAW_MISSING", timestamp=timestamp(3))


def test_unknown_or_out_of_order_events_are_rejected(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "exposure.jsonl")
    item = binding()
    with pytest.raises(ExposureTransitionError):
        ledger.mark_started(item, timestamp=timestamp(1))
    ledger.reserve(item, timestamp=timestamp(1))
    with pytest.raises(ExposureTransitionError):
        ledger.complete(item, timestamp=timestamp(2))
    assert ledger.event_count == 1


def test_new_token_has_256_bits_and_ledger_version_is_frozen() -> None:
    first = new_exposure_token()
    second = new_exposure_token()
    assert LEDGER_VERSION == "AUTH-COVERAGE-EXPOSURE-LEDGER@1"
    assert len(first) == 64 and int(first, 16) >= 0
    assert len(second) == 64 and first != second
