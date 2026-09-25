#!/usr/bin/env python3
"""Read-only final zero-exposure reconciliation for the frozen authorship state."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from safetybox.research.exposure_ledger import ExposureEventType, ExposureLedger

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "governance/exposure_ledger.jsonl"


def main() -> None:
    ledger = ExposureLedger(LEDGER)
    events = ledger.events()
    relevant = [
        event
        for event in events
        if event.binding.experiment_id == "AUTH-COVERAGE-002"
        and event.binding.corpus_id == "AUTH-COVERAGE-002-CORPUS@1"
        and event.binding.split == "HELD_OUT"
        and event.binding.component == "TaskContractPolicy.authorize"
    ]
    counts = Counter(event.event_type.value for event in relevant)
    result_root = ROOT.parents[1] / "results/AUTH-COVERAGE-002"
    raw_records = 0
    if result_root.exists():
        raw_records = sum(
            len(path.read_text(encoding="utf-8").splitlines())
            for path in result_root.rglob("raw*.jsonl")
        )
    output = {
        "audit_id": "AUTH-COVERAGE-002-ZERO-EXPOSURE@1",
        "ledger_path": str(LEDGER.relative_to(ROOT.parents[1])),
        "ledger_exists": LEDGER.exists(),
        "reserved": counts[ExposureEventType.RESERVED.value],
        "started": counts[ExposureEventType.STARTED.value],
        "exposed": counts[ExposureEventType.STARTED.value],
        "completed": counts[ExposureEventType.COMPLETED.value],
        "failed_after_call": counts[ExposureEventType.FAILED_AFTER_CALL.value],
        "raw_records": raw_records,
        "result_package_exists": result_root.exists(),
        "reconciliation": "PASS"
        if not relevant and raw_records == 0 and not result_root.exists()
        else "BLOCKING",
    }
    (ROOT / "corpus/analysis/zero_exposure_audit.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if output["reconciliation"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
