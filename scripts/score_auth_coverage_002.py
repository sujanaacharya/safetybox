#!/usr/bin/env python3
"""Fresh analysis-only entry point for sealed AUTH-COVERAGE-002 scoring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from safetybox.research.auth_coverage_scoring import score_sealed_run
from safetybox.research.auth_coverage_state import RunManifest, RunStateStore
from safetybox.research.exposure_ledger import ExposureLedger


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    parser.add_argument("--run-metadata", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--cross-tool-groups", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--independent", type=Path, required=True)
    parser.add_argument("--scoring-manifest", type=Path, required=True)
    args = parser.parse_args()

    raw_manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(raw_manifest, dict):
        raise SystemExit("run manifest must be a JSON object")
    manifest = RunManifest.from_dict(raw_manifest)
    score_sealed_run(
        state=RunStateStore(args.state, manifest),
        raw_path=args.raw,
        raw_manifest_path=args.raw_manifest,
        ledger=ExposureLedger(args.ledger),
        run_metadata_path=args.run_metadata,
        labels_path=args.labels,
        pairs_path=args.pairs,
        cross_tool_groups_path=args.cross_tool_groups,
        summary_path=args.summary,
        independent_path=args.independent,
        scoring_manifest_path=args.scoring_manifest,
    )


if __name__ == "__main__":
    main()
