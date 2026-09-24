"""Static corpus integrity gate; deliberately never imports or executes the adapter."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent
scenarios = json.loads((ROOT / "scenarios.json").read_text())["scenarios"]
labels = json.loads((ROOT / "labels.json").read_text())["labels"]
assert len(scenarios) == 120 and len(labels) == 120
ids = [x["scenario_id"] for x in scenarios]
assert len(set(ids)) == len(ids) and set(ids) == {x["scenario_id"] for x in labels}
assert all("expected" not in x and "ground_truth" not in x for x in scenarios)
assert sum(x["quality"] == "HARD_BENIGN" for x in labels) >= 30
assert sum(x["quality"] == "HARD_UNAUTHORIZED" for x in labels) >= 30
assert sum(x["pair_id"] is not None for x in labels) >= 40
assert sum(x["pair_id"] is not None for x in labels) >= 40
assert not (ROOT / "results").exists()
print("EXP-015 corpus integrity: PASS (120 scenarios; labels isolated; adapter not imported)")
