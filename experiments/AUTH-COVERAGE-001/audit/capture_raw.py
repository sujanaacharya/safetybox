"""Import-isolated one-shot raw capture for AUTH-COVERAGE-001.

This module uses only the Python standard library. It imports no scorer, oracle,
benchmark labels, or SafetyBox production package.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

Json = dict[str, Any]
_REQUIRED_EXPLANATION = {
    "task", "action", "resource", "capability", "rule", "authority_source",
    "component", "decision", "reason",
}


class CaptureFailure(ValueError):
    """Raw capture violates completeness or one-shot constraints."""


def _canonical_bytes(value: Any) -> bytes:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{text}\n".encode()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(path: Path, key: str) -> list[Json]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get(key), list):
        raise CaptureFailure(f"{path} must contain a {key!r} array")
    values = raw[key]
    if not all(isinstance(item, dict) for item in values):
        raise CaptureFailure(f"{path}:{key} must contain objects")
    return values


def _index(items: list[Json], kind: str) -> dict[str, Json]:
    result: dict[str, Json] = {}
    for item in items:
        identifier = item.get("scenario_id")
        if not isinstance(identifier, str) or not identifier or identifier in result:
            raise CaptureFailure(f"missing/duplicate {kind} scenario_id")
        result[identifier] = item
    return result


def _validate_decision(record: Json) -> None:
    if record.get("decision") not in {"ALLOW", "DENY"}:
        raise CaptureFailure("raw decision must be ALLOW or DENY")
    components = record.get("component_decisions")
    if not isinstance(components, dict) or not components or not all(
        isinstance(key, str) and value in {"ALLOW", "DENY"} for key, value in components.items()
    ):
        raise CaptureFailure("raw component_decisions are invalid")
    explanations = record.get("explanations")
    if not isinstance(explanations, list) or not explanations:
        raise CaptureFailure("raw explanations must be a non-empty array")
    for explanation in explanations:
        if not isinstance(explanation, dict) or not _REQUIRED_EXPLANATION <= explanation.keys():
            raise CaptureFailure("raw explanation is missing deterministic fields")
        if not ({"subject_or_session", "subject", "session"} & explanation.keys()):
            raise CaptureFailure("raw explanation is missing subject/session identity")


def capture_raw(
    scenarios_path: Path, incoming_decisions_path: Path, output_dir: Path
) -> Path:
    """Persist a complete raw decision set once, before scoring is importable."""
    if output_dir.exists():
        raise CaptureFailure("one-shot output already exists; rerun prohibited")
    scenarios = _load(scenarios_path, "scenarios")
    decisions = _load(incoming_decisions_path, "predictions")
    if set(_index(scenarios, "scenario")) != set(_index(decisions, "raw decision")):
        raise CaptureFailure("raw decision IDs must exactly equal scenario IDs")
    for record in decisions:
        _validate_decision(record)
    payload = {"schema_id": "AUTH-COVERAGE-001-RAW@1", "predictions": decisions}
    raw_bytes = _canonical_bytes(payload)
    output_dir.mkdir(parents=True, exist_ok=False)
    raw_path = output_dir / "raw_decisions.json"
    receipt_path = output_dir / "capture_receipt.json"
    fd = os.open(raw_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        os.write(fd, raw_bytes)
    finally:
        os.close(fd)
    receipt = {
        "receipt_id": "AUTH-COVERAGE-001-RAW-CAPTURE@1",
        "raw_file": raw_path.name,
        "raw_sha256": _sha256(raw_bytes),
        "scenario_count": len(scenarios),
        "labels_loaded_before_persistence": False,
        "one_shot": True,
    }
    receipt_path.write_bytes(_canonical_bytes(receipt))
    return receipt_path
