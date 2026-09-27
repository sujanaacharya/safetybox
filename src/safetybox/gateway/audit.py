"""Append-only hash-chained audit events and effect receipts."""

from __future__ import annotations

import fcntl
import hmac
import json
import os
import threading
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from safetybox.gateway.canonical import digest
from safetybox.gateway.models import Action, AuthorizationResult

ZERO_HASH = "0" * 64


@dataclass(frozen=True, slots=True)
class ChainRecord:
    payload: dict[str, Any]
    previous_hash: str
    record_hash: str


class HashChain:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.records: list[ChainRecord] = []
        self._lock = threading.Lock()
        if path is not None and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                raw = json.loads(line)
                self.records.append(ChainRecord(**raw))
            if not self.verify():
                raise ValueError(f"Invalid existing hash chain: {path}")

    def append(
        self, payload: dict[str, Any], *, previous_field: str | None = None
    ) -> ChainRecord:
        with self._lock:
            if self.path is None:
                return self._append_in_memory(payload, previous_field)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a+", encoding="utf-8") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                stream.seek(0)
                disk_records = [ChainRecord(**json.loads(line)) for line in stream if line.strip()]
                if not _records_valid(disk_records):
                    raise ValueError(f"Invalid hash chain while appending: {self.path}")
                self.records = disk_records
                previous = self.records[-1].record_hash if self.records else ZERO_HASH
                if previous_field is not None:
                    payload = {**payload, previous_field: previous}
                record = ChainRecord(
                    payload,
                    previous,
                    digest({"payload": payload, "previous_hash": previous}),
                )
                stream.seek(0, os.SEEK_END)
                stream.write(
                    json.dumps(asdict(record), sort_keys=True, separators=(",", ":")) + "\n"
                )
                stream.flush()
                os.fsync(stream.fileno())
                self.records.append(record)
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                return record

    def _append_in_memory(
        self, payload: dict[str, Any], previous_field: str | None
    ) -> ChainRecord:
        previous = self.records[-1].record_hash if self.records else ZERO_HASH
        if previous_field is not None:
            payload = {**payload, previous_field: previous}
        record = ChainRecord(
            payload, previous, digest({"payload": payload, "previous_hash": previous})
        )
        self.records.append(record)
        return record

    def verify(self, expected_head: str | None = None) -> bool:
        if not _records_valid(self.records):
            return False
        actual_head = self.records[-1].record_hash if self.records else ZERO_HASH
        return expected_head is None or hmac.compare_digest(actual_head, expected_head)

    @property
    def head(self) -> str:
        return self.records[-1].record_hash if self.records else ZERO_HASH


def _records_valid(records: list[ChainRecord]) -> bool:
    previous = ZERO_HASH
    for record in records:
        expected = digest({"payload": record.payload, "previous_hash": previous})
        if record.previous_hash != previous or record.record_hash != expected:
            return False
        previous = record.record_hash
    return True


class AuditLog:
    def __init__(self, directory: Path | None = None) -> None:
        self.events = HashChain(directory / "audit.jsonl" if directory else None)
        self.receipts = HashChain(directory / "receipts.jsonl" if directory else None)

    def event(self, event_type: str, action: Action, **fields: Any) -> None:
        self.events.append(
            {
                "event_id": str(uuid4()),
                "type": event_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "subject": action.subject,
                "agent": action.agent,
                "task": action.task,
                "operation": action.operation,
                "resource": action.resource,
                **fields,
            }
        )

    def receipt(
        self,
        action: Action,
        authorization: AuthorizationResult,
        mediator: str,
        result_class: str,
    ) -> str:
        effect_id = str(uuid4())
        self.receipts.append(
            {
                "effect_id": effect_id,
                "subject": action.subject,
                "agent": action.agent,
                "principal": action.subject,
                "task": action.task,
                "capability_id": authorization.capability_id,
                "action_digest": authorization.action_digest,
                "policy_digest": authorization.policy_digest,
                "decision": authorization.decision.value,
                "mediator": mediator,
                "requested_resource": action.resource,
                "observed_effect": result_class,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            previous_field="previous_receipt_hash",
        )
        return effect_id

    def verify(
        self,
        *,
        expected_audit_head: str | None = None,
        expected_receipt_head: str | None = None,
    ) -> bool:
        return self.events.verify(expected_audit_head) and self.receipts.verify(
            expected_receipt_head
        )

    def reconcile(self) -> bool:
        started = Counter(
            record.payload.get("action_digest")
            for record in self.events.records
            if record.payload.get("type") == "execution_started"
        )
        terminal_effects = Counter(
            record.payload.get("effect_id")
            for record in self.events.records
            if record.payload.get("type") in {"effect_observed", "execution_failed"}
        )
        receipt_actions = Counter(
            record.payload.get("action_digest") for record in self.receipts.records
        )
        receipt_effects = Counter(
            record.payload.get("effect_id") for record in self.receipts.records
        )
        return (
            started == receipt_actions
            and terminal_effects == receipt_effects
            and all(count == 1 for count in receipt_effects.values())
        )
