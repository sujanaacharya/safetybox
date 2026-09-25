"""Additional invariant-focused DEV coverage without modifying the frozen substrate."""

from __future__ import annotations

from pathlib import Path

import pytest

from safetybox.research.exposure_ledger import (
    GENESIS_DIGEST,
    ExposureBinding,
    ExposureEvent,
    ExposureEventType,
    ExposureLedger,
    ExposureLedgerError,
    ExposureLedgerIntegrityError,
    duplicate_exposure_count,
    incomplete_exposure_count,
    run_has_exposure,
)


def binding() -> ExposureBinding:
    return ExposureBinding(
        experiment_id="AUTH-COVERAGE-002-PROTOCOL2-DEV",
        corpus_id="AUTH-COVERAGE-002-PROTOCOL2-DEV-FIXTURE",
        split="DEV",
        run_id="dev-run",
        scenario_id="opaque-dev-scenario",
        component="TaskContractPolicy.authorize",
        implementation_sha="a" * 40,
        token="dev-token",
    )


def test_event_decoder_rejects_every_malformed_schema_layer() -> None:
    valid = ExposureEvent(
        1, ExposureEventType.RESERVED, binding(), "2026-09-25T10:00:01Z", {}
    ).to_dict()
    invalid_values: list[object] = [
        [],
        {**valid, "extra": True},
        {**valid, "sequence": True},
        {**valid, "sequence": 0},
        {**valid, "timestamp": ""},
        {**valid, "details": []},
        {**valid, "details": {1: "not-a-string-key"}},
        {**valid, "details": {"float": 1.5}},
        {**valid, "event_type": "UNKNOWN"},
        {**valid, "binding": []},
        {**valid, "binding": {**binding().to_dict(), "extra": "x"}},
        {**valid, "binding": {**binding().to_dict(), "token": ""}},
    ]
    for value in invalid_values:
        with pytest.raises(ExposureLedgerIntegrityError):
            ExposureEvent.from_dict(value)


def test_empty_snapshot_anchor_mismatches_and_query_wrappers(tmp_path: Path) -> None:
    ledger = ExposureLedger(tmp_path / "empty.jsonl")
    assert ledger.events() == ()
    assert ledger.head == GENESIS_DIGEST
    snapshot = ledger.snapshot_to(tmp_path / "snapshot.jsonl")
    assert snapshot.events() == ()

    item = binding()
    ledger.reserve(item, timestamp="2026-09-25T10:00:01Z")
    integrity = ledger.verify_integrity(expected_head="0" * 64, expected_event_count=2)
    assert not integrity.valid
    assert len(integrity.errors) == 2
    assert not run_has_exposure(ledger, experiment_id=item.experiment_id, run_id=item.run_id)
    assert duplicate_exposure_count(ledger) == 0
    assert incomplete_exposure_count(ledger, experiment_id="OTHER", run_id="OTHER") == 0
    with pytest.raises(ExposureLedgerError, match="non-empty"):
        ledger.reconcile(item, status="")
    with pytest.raises(ExposureLedgerError, match="override"):
        ledger.reconcile(item, status="RESERVED_NOT_EXPOSED", details={"status": "bad"})
