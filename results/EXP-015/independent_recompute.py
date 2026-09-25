# ruff: noqa: E501
"""Independent EXP-015 recomputation; never imports or executes the adapter."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULT = Path(__file__).resolve().parent
CORPUS = ROOT / "experiments/EXP-015/corpus2"


def load_lines(name: str):
    return [json.loads(line) for line in (RESULT / name).read_text().splitlines() if line]


def score(records, labels):
    failures = [r["scenario_id"] for r in records if r["compound_authorization_decision"] != labels[r["scenario_id"]]["expected_compound_authority"]]
    return {"correct": len(records) - len(failures), "total": len(records), "failure_ids": failures}


def normalize(record):
    value = json.loads(json.dumps(record))
    for key in ("ordinal", "phase_record_kind", "pid", "child_token", "timing", "adapter_request_executable", "canonical_executable", "primitive_invocations", "exec_authorization_provenance", "cwd_authorization_provenance"):
        value.pop(key, None)
    for event in value.get("audit_events", []):
        for key in ("event_id", "timestamp", "parent_event_id"):
            event.pop(key, None)
        for field in ("requested_executable", "canonical_executable"):
            event.get("metadata", {}).pop(field, None)
    for auth in value.get("authorization_evidence", []):
        for field in ("resource", "applicable_capability_resource"):
            resource = auth.get(field)
            if isinstance(resource, str) and "/safetybox-exp015-" in resource:
                auth[field] = resource.split("/workspace/", 1)[-1]
    return value


def main():
    runs = load_lines("runs.jsonl")
    repeats = load_lines("repeats.jsonl")
    labels_list = json.loads((CORPUS / "labels.json").read_text())["labels"]
    pairs = json.loads((CORPUS / "pairs.json").read_text())["pairs"]
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    labels = {x["scenario_id"]: x for x in labels_list}
    by_id = {x["scenario_id"]: x for x in runs}
    repeat_by_id = {x["scenario_id"]: x for x in repeats}
    positives = [r for r in runs if labels[r["scenario_id"]]["expected_compound_authority"] == "ALLOW"]
    negatives = [r for r in runs if labels[r["scenario_id"]]["expected_compound_authority"] == "DENY"]
    groups = {name: [r for r in runs if labels[r["scenario_id"]]["difficulty"] == name] for name in ("HARD_BENIGN", "EDGE_BENIGN", "HARD_UNAUTHORIZED", "EDGE_UNAUTHORIZED")}
    pair_by_dimension = defaultdict(list)
    pair_results = []
    for pair in pairs:
        correct = all(by_id[sid]["compound_authorization_decision"] == labels[sid]["expected_compound_authority"] for sid in (pair["scenario_a"], pair["scenario_b"]))
        pair_results.append(correct)
        pair_by_dimension[pair["changed_dimension"]].append(correct)
    denied = [r for r in runs if r["compound_authorization_decision"] == "DENY"]
    argv_cases = [r for r in runs if labels[r["scenario_id"]].get("expected_argv_preservation") not in {None, "NOT_APPLICABLE", "N/A"}]
    argv_preserved = sum(any(marker["present"] and json.loads(marker["utf8"]) == r["request_argv"] for marker in r["marker_observations"] if marker["utf8"] is not None) for r in argv_cases)
    validation = [r for r in runs if labels[r["scenario_id"]].get("expected_validation") == "REJECT"]
    terminal_correct = sum(r["terminal_classification"] == labels[r["scenario_id"]]["expected_terminal"] for r in runs)
    basis = {
        "authorization": {"true_allow": sum(r["compound_authorization_decision"] == "ALLOW" for r in positives), "false_deny": sum(r["compound_authorization_decision"] != "ALLOW" for r in positives), "true_deny": sum(r["compound_authorization_decision"] == "DENY" for r in negatives), "false_allow": sum(r["compound_authorization_decision"] != "DENY" for r in negatives)},
        "difficulty": {name: score(records, labels) for name, records in groups.items()},
        "strong_pairs": {"correct": sum(pair_results), "total": len(pair_results), "by_dimension": {name: {"correct": sum(values), "total": len(values)} for name, values in pair_by_dimension.items()}},
        "task_binding": {"correct": sum(pair_by_dimension["TASK_BINDING"]), "total": len(pair_by_dimension["TASK_BINDING"])},
        "denied_spawn": {"correct": sum(r["primitive_invocation_count"] == 0 and r["child_created"] in {False, None} for r in denied), "total": len(denied)},
        "argv_preservation": {"correct": argv_preserved, "total": len(argv_cases)},
        "validation": {"correct": sum(r["validation_outcome"] == "REJECT" for r in validation), "total": len(validation)},
        "terminal_accuracy": {"correct": terminal_correct, "total": len(runs)},
        "repeats": {"correct": sum(normalize(by_id[sid]) == normalize(repeat_by_id[sid]) for sid in manifest["repeat_set"]), "total": 6},
    }
    summary = json.loads((RESULT / "summary.json").read_text())
    comparisons = {
        "authorization_confusion_matrix": basis["authorization"] == {key: summary["authorization"][key] for key in basis["authorization"]},
        "hard_benign": basis["difficulty"]["HARD_BENIGN"]["correct"] == summary["difficulty"]["HARD_BENIGN"]["correct"],
        "edge_benign": basis["difficulty"]["EDGE_BENIGN"]["correct"] == summary["difficulty"]["EDGE_BENIGN"]["correct"],
        "hard_unauthorized": basis["difficulty"]["HARD_UNAUTHORIZED"]["correct"] == summary["difficulty"]["HARD_UNAUTHORIZED"]["correct"],
        "edge_unauthorized": basis["difficulty"]["EDGE_UNAUTHORIZED"]["correct"] == summary["difficulty"]["EDGE_UNAUTHORIZED"]["correct"],
        "strong_pairs": basis["strong_pairs"]["correct"] == summary["strong_pairs"]["correct"],
        "task_binding": basis["task_binding"]["correct"] == summary["task_binding"]["correct"],
        "denied_spawn": basis["denied_spawn"]["correct"] == summary["denied_spawn_prevention"]["correct"],
        "argv_preservation": basis["argv_preservation"]["correct"] == summary["argv_preservation"]["correct"],
        "validation": basis["validation"]["correct"] == summary["validation"]["semantics"]["correct"],
        "terminal_accuracy": basis["terminal_accuracy"]["correct"] == summary["terminal_accuracy"]["correct"],
        "six_repeats": basis["repeats"]["correct"] == summary["determinism"]["correct"],
    }
    output = {"adapter_executed": False, "basis": basis, "comparisons": comparisons, "all_match": all(comparisons.values())}
    (RESULT / "independent_recompute.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    if not output["all_match"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
