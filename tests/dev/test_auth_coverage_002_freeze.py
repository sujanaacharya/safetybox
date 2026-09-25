from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "experiments/AUTH-COVERAGE-002/SUBSTRATE_SHA256SUMS"
CONTRACT = ROOT / "experiments/AUTH-COVERAGE-002/contracts/execution_substrate.json"
REGISTRY = ROOT / "experiments/AUTH-COVERAGE-002/dev/contamination_registry.json"


def test_substrate_freeze_manifest_verifies_every_listed_artifact() -> None:
    entries: dict[str, str] = {}
    for line in FREEZE.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        assert relative not in entries
        entries[relative] = digest
    assert len(entries) >= 30
    for relative, expected in entries.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_freeze_contains_no_corpus_labels_results_or_exposure() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert contract["corpus_identity"] is None
    assert contract["held_out_labels"] is None
    assert contract["held_out_scenarios_authored"] == 0
    assert contract["held_out_prediction_exposure"] == 0
    assert registry["held_out_scenarios_authored"] == 0
    assert registry["held_out_prediction_exposure"] == 0
    prohibited = [
        ROOT / "experiments/AUTH-COVERAGE-002/heldout-runtime",
        ROOT / "experiments/AUTH-COVERAGE-002/labels",
        ROOT / "results/AUTH-COVERAGE-002",
    ]
    assert all(not path.exists() for path in prohibited)
