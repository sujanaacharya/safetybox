#!/usr/bin/env python3
"""DEV/VALIDATION-only frozen scorer schema rehearsal with synthetic observations."""

from __future__ import annotations

import json
from pathlib import Path

from safetybox.research.auth_coverage_metrics import score_authorization

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"


def main() -> None:
    labels = json.loads((CORPUS / "analysis/labels.json").read_text(encoding="utf-8"))
    rehearsal_ids = {
        scenario["scenario_id"]
        for split in ("DEV", "VALIDATION")
        for scenario in json.loads(
            (CORPUS / f"runtime/{split}/scenarios.json").read_text(encoding="utf-8")
        )
    }
    labels = [item for item in labels if item["scenario_id"] in rehearsal_ids]
    label_ids = {item["scenario_id"] for item in labels}
    scenarios = {
        item["scenario_id"]: item
        for split in ("DEV", "VALIDATION")
        for item in json.loads(
            (CORPUS / f"runtime/{split}/scenarios.json").read_text(encoding="utf-8")
        )
    }
    pairs = [
        item
        for item in json.loads((CORPUS / "analysis/pairs.json").read_text(encoding="utf-8"))
        if set(item["scenario_ids"]) <= label_ids
    ]
    groups = [
        item
        for item in json.loads(
            (CORPUS / "analysis/cross_tool_groups.json").read_text(encoding="utf-8")
        )
        if set(item["scenario_ids"]) <= label_ids
    ]
    raw = []
    for label in labels:
        request = scenarios[label["scenario_id"]]["request"]
        decision = label["expected_decision"]
        raw.append(
            {
                "scenario_id": label["scenario_id"],
                "final_decision": decision,
                "evaluated_input": {
                    "request_task_id": request["task_id"],
                    "action": request["action"],
                    "resource": request["resource"],
                },
                "explanation": {
                    "decision": decision,
                    "rule": "SYNTHETIC_SCHEMA_REHEARSAL",
                    "component": "primary",
                    "matched_capability": None,
                    "authority_source": "TaskContract",
                    "task": request["task_id"],
                    "action": request["action"],
                    "resource": request["resource"],
                    "reason_code": "SYNTHETIC_SCHEMA_REHEARSAL",
                },
                "infrastructure_errors": [],
            }
        )
    summary = score_authorization(
        raw,
        labels,
        pairs=pairs,
        cross_tool_groups=groups,
        raw_package_digest="a" * 64,
        label_package_digest="b" * 64,
    )
    output = {
        "audit_id": "AUTH-COVERAGE-002-SCORER-COMPATIBILITY@1",
        "result": "PASS",
        "splits": ["DEV", "VALIDATION"],
        "synthetic_record_count": len(raw),
        "production_calls": 0,
        "false_allow_denominator": summary["primary_metrics"]["FALSE_ALLOW_RATE"]["denominator"],
        "false_deny_denominator": summary["primary_metrics"]["FALSE_DENY_RATE"]["denominator"],
        "strict_pair_denominator": summary["pair_quality"]["strict_strong"]["denominator"],
        "moderate_pair_denominator": summary["pair_quality"]["moderate"]["denominator"],
        "cross_tool_denominator": summary["cross_tool_consistency"]["denominator"],
    }
    (CORPUS / "analysis/scorer_compatibility.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
