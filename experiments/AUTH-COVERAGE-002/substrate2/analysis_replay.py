#!/usr/bin/env python3
"""Narrow, non-authorizing counterfactual replay for the preserved blocked evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

HERE = Path(__file__).resolve().parent
EXPERIMENT_ROOT = HERE.parent
EXPECTED_EVIDENCE_DIGEST = "42f046e8aa5cfd9334998dcf1956f09108cb8bd934755fe95f385f2f99308bc0"
EXPECTED_MACHINE_AUDIT_DIGEST = (
    "7d722a43a840bff34671245a51326b94a1a6211aa775a6bfa5d77ed38d669869"
)
EXPECTED_ATTEMPT = "AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1"
DEFECTIVE = {"DEV": 800, "VALIDATION": 800}
CORRECTED = {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 0}


def _load_successor() -> ModuleType:
    path = HERE / "candidate_audit.py"
    spec = importlib.util.spec_from_file_location("auth_coverage_002_substrate2_replay", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load successor audit")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def replay(
    machine_audit: dict[str, Any], evidence_digest: str, machine_audit_digest: str
) -> dict[str, Any]:
    """Replay only the exact known defect; this function cannot grant authority."""
    if evidence_digest != EXPECTED_EVIDENCE_DIGEST:
        raise ValueError("unexpected preserved evidence digest")
    if machine_audit_digest != EXPECTED_MACHINE_AUDIT_DIGEST:
        raise ValueError("unexpected preserved machine-audit digest")
    if machine_audit.get("corpus_attempt_id") != EXPECTED_ATTEMPT:
        raise ValueError("counterfactual replay is restricted to the blocked attempt")
    metrics = machine_audit.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("preserved metrics are missing")
    if metrics.get("phase") != "PRE_HELDOUT" or metrics.get("realized_split") != DEFECTIVE:
        raise ValueError("evidence does not have the exact frozen defect signature")
    if metrics.get("counts", {}).get("split") != CORRECTED:
        raise ValueError("direct split counts do not support the exact repair")
    successor = _load_successor()
    before = cast(dict[str, Any], successor.evaluate_gates(metrics))
    corrected = copy.deepcopy(metrics)
    corrected["realized_split"] = dict(CORRECTED)
    after = cast(dict[str, Any], successor.evaluate_gates(corrected))
    return {
        "classification": "COUNTERFACTUAL_ANALYSIS_ONLY",
        "source_attempt": EXPECTED_ATTEMPT,
        "source_evidence_digest": evidence_digest,
        "changed_metric_fields": ["realized_split"],
        "old_decision": before["decision"],
        "hypothetical_successor_decision": after["decision"],
        "authorized": False,
        "statement": (
            "The successor audit would not reproduce the substrate defect on the "
            "preserved evidence."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("machine_audit", type=Path)
    parser.add_argument("gate_a_evidence", type=Path)
    args = parser.parse_args()
    evidence_bytes = args.gate_a_evidence.read_bytes()
    evidence_digest = hashlib.sha256(evidence_bytes).hexdigest()
    evidence = json.loads(evidence_bytes)
    if evidence_digest != EXPECTED_EVIDENCE_DIGEST:
        raise ValueError("unexpected preserved evidence digest")
    machine_bytes = args.machine_audit.read_bytes()
    machine_digest = hashlib.sha256(machine_bytes).hexdigest()
    if evidence.get("evidence_files", {}).get("machine-audit.json") != machine_digest:
        raise ValueError("machine audit is not bound by the preserved evidence")
    machine_audit = json.loads(machine_bytes)
    print(
        json.dumps(
            replay(machine_audit, evidence_digest, machine_digest),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
