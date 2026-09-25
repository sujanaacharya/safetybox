#!/usr/bin/env python3
"""Independent crash reconciliation and partial-evidence finalization."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from safetybox.research.auth_coverage_reconcile import (
    finalize_complete_raw_seal,
    reconcile_run,
    seal_reconciled_partial,
)
from safetybox.research.auth_coverage_state import RunManifest, RunState, RunStateStore
from safetybox.research.exposure_ledger import ExposureLedger


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--partial-manifest", type=Path)
    parser.add_argument("--complete-manifest", type=Path)
    args = parser.parse_args()

    value = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("run manifest must be a JSON object")
    manifest = RunManifest.from_dict(value)
    state = RunStateStore(args.state, manifest)
    ledger = ExposureLedger(args.ledger)
    report = reconcile_run(
        manifest=manifest,
        state=state,
        ledger=ledger,
        raw_path=args.raw,
        repair=args.repair,
    )
    if (
        args.repair
        and args.partial_manifest is not None
        and state.load().state is RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE
    ):
        seal_reconciled_partial(
            manifest=manifest,
            state=state,
            ledger=ledger,
            raw_path=args.raw,
            run_metadata_path=args.manifest,
            partial_manifest_path=args.partial_manifest,
        )
    if (
        args.repair
        and args.complete_manifest is not None
        and state.load().state in {RunState.COMPLETED_RAW, RunState.SEALED_RAW}
    ):
        finalize_complete_raw_seal(
            manifest=manifest,
            state=state,
            ledger=ledger,
            raw_path=args.raw,
            run_metadata_path=args.manifest,
            raw_manifest_path=args.complete_manifest,
        )
    output = asdict(report)
    output["statuses"] = [status.value for status in report.statuses]
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
