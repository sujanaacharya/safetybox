"""Post-capture scorer; this module is never imported by raw capture."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

try:
    from .audit_core import AuditFailure, _load, score_predictions
except ImportError:  # Direct execution from the audit directory.
    from audit_core import AuditFailure, _load, score_predictions


def _canonical_bytes(value: object) -> bytes:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{text}\n".encode()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def score_sealed(
    receipt_path: Path,
    labels_path: Path,
    pairs_path: Path,
    destination: Path,
    cross_tool_pairs_path: Path | None = None,
) -> None:
    """Score only a byte-verified persisted capture; never invoke a decision system."""
    if destination.exists():
        raise AuditFailure("score destination already exists")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    raw_path = receipt_path.parent / receipt["raw_file"]
    raw_bytes = raw_path.read_bytes()
    if _sha256(raw_bytes) != receipt.get("raw_sha256"):
        raise AuditFailure("sealed raw decision checksum mismatch")
    predictions = json.loads(raw_bytes)["predictions"]
    labels = _load(labels_path, "labels")
    pairs = _load(pairs_path, "pairs")
    cross_tool_pairs = (
        [] if cross_tool_pairs_path is None else _load(cross_tool_pairs_path, "pairs")
    )
    metrics = {
        "schema_id": "AUTH-COVERAGE-001-SCORES@1",
        "raw_sha256": receipt["raw_sha256"],
        "metrics": score_predictions(predictions, labels, pairs, cross_tool_pairs),
    }
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        os.write(fd, _canonical_bytes(metrics))
    finally:
        os.close(fd)
