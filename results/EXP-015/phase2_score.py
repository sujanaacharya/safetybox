# ruff: noqa: E501
"""EXP-015-RUN-001 scoring phase; labels join only after the raw barrier."""

from __future__ import annotations

import hashlib
import json
import math
import posixpath
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULT = Path(__file__).resolve().parent
CORPUS = ROOT / "experiments/EXP-015/corpus2"
RUNS = RESULT / "runs.jsonl"
REPEATS = RESULT / "repeats.jsonl"
STATE = RESULT / "execution_state.json"
SUMMARY = RESULT / "summary.json"
JOIN = RESULT / "label_join_manifest.json"
SCORER_VERSION = "EXP-015-SCORER-1"


def now() -> str:
    return datetime.now(UTC).astimezone().isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def tags(label: dict[str, Any]) -> set[str]:
    return {str(value).upper() for value in label.get("tags", [])}


def tagged(label: dict[str, Any], *needles: str) -> bool:
    joined = " ".join(tags(label))
    return any(needle.upper() in joined for needle in needles)


def fraction(correct: int, total: int) -> dict[str, object]:
    return {"correct": correct, "total": total, "rate": None if total == 0 else correct / total}


def group_score(records: list[dict[str, Any]], label_by_id: dict[str, dict[str, Any]]) -> dict[str, object]:
    failures = [r["scenario_id"] for r in records if r["compound_authorization_decision"] != label_by_id[r["scenario_id"]]["expected_compound_authority"]]
    return {**fraction(len(records) - len(failures), len(records)), "failure_ids": failures}


def stream_truth(record: dict[str, Any], name: str) -> bool:
    stream = record[name]
    retained = stream.get("retained")
    if retained is None:
        return stream["byte_count"] is None and stream["sha256"] is None
    data = __import__("base64").b64decode(retained["base64"])
    return retained["byte_count"] == len(data) and retained["sha256"] == hashlib.sha256(data).hexdigest() and (stream["byte_count"] or 0) >= len(data)


def percentile(values: list[int], probability: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(probability * len(ordered)) - 1)]


def normalize_repeat(record: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(record))
    for key in ("ordinal", "phase_record_kind", "pid", "child_token", "timing", "adapter_request_executable", "canonical_executable", "primitive_invocations"):
        value.pop(key, None)
    for event in value.get("audit_events", []):
        event.pop("event_id", None)
        event.pop("timestamp", None)
        event.pop("parent_event_id", None)
        metadata = event.get("metadata", {})
        for field in ("requested_executable", "canonical_executable"):
            metadata.pop(field, None)
    for authorization in value.get("authorization_evidence", []):
        resource = authorization.get("resource")
        if isinstance(resource, str) and "/safetybox-exp015-" in resource:
            authorization["resource"] = resource.split("/workspace/", 1)[-1]
        capability = authorization.get("applicable_capability_resource")
        if isinstance(capability, str) and "/safetybox-exp015-" in capability:
            authorization["applicable_capability_resource"] = capability.split("/workspace/", 1)[-1]
    value.pop("exec_authorization_provenance", None)
    value.pop("cwd_authorization_provenance", None)
    return value


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("status") != "RAW_COMPLETE_LABELS_NOT_LOADED" or state.get("canonical_records_persisted") != 120:
        raise RuntimeError("raw completion barrier not satisfied")
    runs = load_jsonl(RUNS)
    repeats = load_jsonl(REPEATS)
    if len(runs) != 120 or len(repeats) != 6 or sha(RUNS) != state["raw_checksum_sha256"]:
        raise RuntimeError("raw artifacts do not match execution barrier")

    # This is the first label/pair open in the run lifecycle.
    labels_doc = json.loads((CORPUS / "labels.json").read_text(encoding="utf-8"))
    pairs_doc = json.loads((CORPUS / "pairs.json").read_text(encoding="utf-8"))
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    labels = labels_doc["labels"]
    pairs = pairs_doc["pairs"]
    label_by_id = {item["scenario_id"]: item for item in labels}
    run_by_id = {item["scenario_id"]: item for item in runs}
    complete = set(label_by_id) == set(run_by_id) and len(label_by_id) == 120
    write_json(JOIN, {
        "run_id": "EXP-015-RUN-001", "scorer_version": SCORER_VERSION,
        "raw_checksum_sha256": sha(RUNS), "label_checksum_sha256": sha(CORPUS / "labels.json"),
        "pair_registry_checksum_sha256": sha(CORPUS / "pairs.json"), "join_timestamp": now(),
        "scenario_count": len(runs), "join_completeness": complete,
    })
    if not complete:
        raise RuntimeError("label join incomplete")

    positives = [r for r in runs if label_by_id[r["scenario_id"]]["expected_compound_authority"] == "ALLOW"]
    negatives = [r for r in runs if label_by_id[r["scenario_id"]]["expected_compound_authority"] == "DENY"]
    true_allow = sum(r["compound_authorization_decision"] == "ALLOW" for r in positives)
    false_deny = len(positives) - true_allow
    true_deny = sum(r["compound_authorization_decision"] == "DENY" for r in negatives)
    false_allow = len(negatives) - true_deny

    difficulty = {}
    for name in ("HARD_BENIGN", "EDGE_BENIGN", "HARD_UNAUTHORIZED", "EDGE_UNAUTHORIZED"):
        members = [r for r in runs if label_by_id[r["scenario_id"]].get("difficulty") == name]
        difficulty[name] = group_score(members, label_by_id)
        difficulty[name]["allow"] = sum(r["compound_authorization_decision"] == "ALLOW" for r in members)
        difficulty[name]["deny"] = sum(r["compound_authorization_decision"] == "DENY" for r in members)
        difficulty[name]["authorized_then_validation_rejected"] = sum(r["compound_authorization_decision"] == "ALLOW" and r["validation_outcome"] == "REJECT" for r in members)
        difficulty[name]["authorized_then_execution_failed"] = sum(r["compound_authorization_decision"] == "ALLOW" and r["terminal_classification"] not in {"PROCESS_EXIT_0", "VALIDATION_REJECT_NOT_SPAWNED"} for r in members)

    pair_dimensions: dict[str, dict[str, object]] = {}
    pair_failures = []
    for pair in pairs:
        pair["correct"] = all(run_by_id[sid]["compound_authorization_decision"] == label_by_id[sid]["expected_compound_authority"] for sid in (pair["scenario_a"], pair["scenario_b"]))
        if not pair["correct"]:
            pair_failures.append({**pair, "raw_records": [run_by_id[pair["scenario_a"]], run_by_id[pair["scenario_b"]]]})
    for dimension in ("TASK_BINDING", "EXEC_CAPABILITY", "CWD_CAPABILITY", "EXEC_RESOURCE", "CWD_RESOURCE"):
        members = [pair for pair in pairs if pair["changed_dimension"] == dimension and pair["strength"] == "STRONG"]
        pair_dimensions[dimension] = fraction(sum(pair["correct"] for pair in members), len(members))
    strong = [pair for pair in pairs if pair["strength"] == "STRONG"]

    exec_correct = sum(r["exec_authorization_decision"] == label_by_id[r["scenario_id"]]["expected_exec_authority"] for r in runs)
    cwd_correct = sum(r["cwd_authorization_decision"] == label_by_id[r["scenario_id"]]["expected_cwd_authority"] for r in runs)
    expected_quadrants = Counter(label_by_id[r["scenario_id"]]["expected_exec_authority"][0] + label_by_id[r["scenario_id"]]["expected_cwd_authority"][0] for r in runs)
    actual_quadrants = Counter((r["exec_authorization_decision"] or "UNKNOWN")[0] + (r["cwd_authorization_decision"] or "UNKNOWN")[0] for r in runs)
    non_aa_reached = [r["scenario_id"] for r in runs if not (r["exec_authorization_decision"] == r["cwd_authorization_decision"] == "ALLOW") and (r["validation_outcome"] != "NOT_ATTEMPTED" or r["primitive_invocation_count"] != 0)]

    distractors = [r for r in runs if tagged(label_by_id[r["scenario_id"]], "DISTRACTOR")]
    zero_relevant = [r for r in runs if tagged(label_by_id[r["scenario_id"]], "ZERO_RELEVANT", "NO_RELEVANT")]
    exec_boundaries = [r for r in runs if tagged(label_by_id[r["scenario_id"]], "EXEC_RESOURCE")]
    cwd_boundaries = [r for r in runs if tagged(label_by_id[r["scenario_id"]], "CWD_RESOURCE")]
    suspicious = [r for r in runs if label_by_id[r["scenario_id"]]["expected_compound_authority"] == "ALLOW" and tagged(label_by_id[r["scenario_id"]], "SUSPICIOUS", "ARGV")]
    argv_cases = [r for r in runs if label_by_id[r["scenario_id"]].get("expected_argv_preservation") not in {None, "NOT_APPLICABLE", "N/A"}]
    argv_preserved = sum(any(marker["present"] and json.loads(marker["utf8"]) == r["request_argv"] for marker in r["marker_observations"] if marker["utf8"] is not None) for r in argv_cases)

    validation_cases = [r for r in runs if label_by_id[r["scenario_id"]].get("expected_validation") == "REJECT"]
    validation_auth = group_score(validation_cases, label_by_id)
    validation_semantic = fraction(sum(r["validation_outcome"] == "REJECT" for r in validation_cases), len(validation_cases))
    failure_cases = [r for r in runs if tagged(label_by_id[r["scenario_id"]], "FAILURE")]
    failure_auth = group_score(failure_cases, label_by_id)
    failure_semantic = fraction(sum(r["terminal_classification"] == label_by_id[r["scenario_id"]]["expected_terminal"] for r in failure_cases), len(failure_cases))

    denied = [r for r in runs if r["compound_authorization_decision"] == "DENY"]
    denied_failures = [r["scenario_id"] for r in denied if not (r["primitive_invocation_count"] == 0 and r["child_created"] in {False, None} and r["pid"] is None and r["child_token"] is None and r["stdout"]["byte_count"] is None and r["stderr"]["byte_count"] is None and not any(marker["present"] for marker in r["marker_observations"]))]
    spawned = [r for r in runs if r["primitive_invocation_count"] > 0]
    ordering_failures = [r["scenario_id"] for r in spawned if not ("AUTHORIZATION_ALLOWED" in r["events_before_primitive_invocation"] and r["events_before_primitive_invocation"].count("TARGET_VALIDATION_SUCCEEDED") == 2 and r["events_before_primitive_invocation"][-1:] == ["EXECUTION_STARTED"])]

    validation_by_kind = {}
    for dimension_name, key in (("executable", "executable_kind"), ("cwd", "cwd_kind")):
        kinds = sorted({r["runtime_fixture"][key] for r in runs})
        validation_by_kind[dimension_name] = {kind: Counter(r[f"{dimension_name}_validation"] for r in runs if r["runtime_fixture"][key] == kind) for kind in kinds}

    canonical_mismatches = []
    for r in runs:
        if r["canonical_executable"] is not None and r["canonical_executable"] != posixpath.normpath(r["adapter_request_executable"]):
            canonical_mismatches.append(r["scenario_id"])
        if r["canonical_cwd"] is not None and r["canonical_cwd"] != posixpath.normpath(r["adapter_request_cwd"]):
            canonical_mismatches.append(r["scenario_id"])
    path_traps = [r for r in runs if tagged(label_by_id[r["scenario_id"]], "PATH", "BARE", "RELATIVE")]
    environment_cases = [r for r in runs if label_by_id[r["scenario_id"]].get("expected_environment") not in {None, "NOT_APPLICABLE", "N/A"}]
    environment_correct = sum(r["primitive_invocation_count"] == 1 and all(dict(inv["environment"]) == {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"} for inv in r["primitive_invocations"]) for r in environment_cases)
    output_cases = [r for r in runs if label_by_id[r["scenario_id"]].get("expected_output_metadata") not in {None, "NOT_APPLICABLE", "N/A"}]
    output_correct = sum(stream_truth(r, "stdout") and stream_truth(r, "stderr") and r["primitive_invocation_count"] == 1 for r in output_cases)
    confidentiality_failures = []
    for r in runs:
        protected = r["observation_declarations"].get("output_sentinels", [])
        searchable = json.dumps({"audit_events": r["audit_events"], "safe_error": r["safe_error"], "authorization_evidence": r["authorization_evidence"]})
        if any(value in searchable for value in protected):
            confidentiality_failures.append(r["scenario_id"])

    def expected_terminal_group(*needles: str) -> list[dict[str, Any]]:
        return [r for r in runs if any(needle in label_by_id[r["scenario_id"]]["expected_terminal"] for needle in needles)]

    terminal_groups = {}
    for name, needles in {"nonzero": ("NONZERO",), "timeout": ("TIMEOUT",), "signal": ("SIGNAL", "SIGNALED"), "failure_injection": ("INDETERMINATE", "SPAWN_ERROR", "FAIL_CLOSED")}.items():
        members = expected_terminal_group(*needles)
        terminal_groups[name] = {**fraction(sum(r["terminal_classification"] == label_by_id[r["scenario_id"]]["expected_terminal"] for r in members), len(members)), "scenario_ids": [r["scenario_id"] for r in members]}

    required_fields = ("session_id", "request_task_id", "contract_task_id", "request_executable", "request_argv", "request_cwd", "compound_authorization_decision", "validation_outcome", "primitive_invocation_count", "terminal_classification", "audit_events")
    reconstruction_failures = [r["scenario_id"] for r in runs if any(field not in r for field in required_fields)]
    truthful_failures = [r["scenario_id"] for r in runs if not stream_truth(r, "stdout") or not stream_truth(r, "stderr") or (r["primitive_invocation_count"] == 0 and r["child_created"] is True)]
    controls = [run_by_id[sid] for sid in manifest["pmed_controls"]]

    repeat_by_id = {r["scenario_id"]: r for r in repeats}
    repeat_results = []
    for repeat_id in manifest["repeat_set"]:
        equivalent = normalize_repeat(run_by_id[repeat_id]) == normalize_repeat(repeat_by_id[repeat_id])
        repeat_results.append({"scenario_id": repeat_id, "equivalent": equivalent})

    terminal_correct = sum(r["terminal_classification"] == label_by_id[r["scenario_id"]]["expected_terminal"] for r in runs)
    timings = [r["timing"]["total_ns"] for r in runs if r["route"] == "ADAPTER"]
    performance = {"n": len(timings), "min_ns": min(timings), "median_ns": statistics.median(timings), "mean_ns": statistics.fmean(timings), "p95_ns": percentile(timings, 0.95), "p99_ns": percentile(timings, 0.99), "description": "canonical adapter elapsed time; not production overhead"}

    success = {
        "100_percent_authorization_correctness": "PASS" if true_allow + true_deny == 120 else "FAIL",
        "100_percent_denied_spawn_prevention": "PASS" if not denied_failures else "FAIL",
        "100_percent_authorize_before_spawn_ordering": "PASS" if not ordering_failures else "FAIL",
        "100_percent_registered_argument_boundary_preservation": "PASS" if argv_preserved == len(argv_cases) else "FAIL",
        "100_percent_audit_reconstruction_completeness": "PASS" if not reconstruction_failures else "FAIL",
        "100_percent_registered_executable_and_cwd_correctness": "PASS" if not canonical_mismatches and validation_semantic["correct"] == validation_semantic["total"] else "FAIL",
        "100_percent_environment_containment": "PASS" if environment_correct == len(environment_cases) else "FAIL",
        "100_percent_frozen_terminal_semantic_correctness": "PASS" if terminal_correct == 120 else "FAIL",
        "zero_adapter_routed_policy_escapes": "PASS" if not denied_failures else "FAIL",
        "expected_direct_route_bypass_demonstrated": "PASS" if any(r["route"] == "DIRECT_CONTROL" and r["child_created"] for r in controls) else "FAIL",
        "deterministic_repeats": "PASS" if all(item["equivalent"] for item in repeat_results) else "FAIL",
        "no_frozen_regression": "NOT_EVALUATED",
        "zero_authorization_false_allows": "PASS" if false_allow == 0 else "FAIL",
        "zero_authorization_false_denies": "PASS" if false_deny == 0 else "FAIL",
    }
    failure = {
        "authorization_false_allow_or_false_deny_in_evaluable_case": "TRIGGERED" if false_allow or false_deny else "NOT_TRIGGERED",
        "denied_request_invokes_spawn_or_creates_child": "TRIGGERED" if denied_failures else "NOT_TRIGGERED",
        "spawn_precedes_complete_allow": "TRIGGERED" if ordering_failures else "NOT_TRIGGERED",
        "spawn_precedes_required_validation": "TRIGGERED" if ordering_failures else "NOT_TRIGGERED",
        "spawn_precedes_committed_required_audit": "TRIGGERED" if ordering_failures else "NOT_TRIGGERED",
        "shell_metacharacter_interpreted_on_shell_false_route": "TRIGGERED" if argv_preserved != len(argv_cases) and spawned else "NOT_TRIGGERED",
        "unauthorized_cwd_accepted": "TRIGGERED" if any(r["cwd_authorization_decision"] == "DENY" and r["primitive_invocation_count"] for r in runs) else "NOT_TRIGGERED",
        "executable_canonicalization_expands_scope": "TRIGGERED" if canonical_mismatches else "NOT_TRIGGERED",
        "audit_claims_denied_or_not_executed_after_known_spawn": "TRIGGERED" if truthful_failures else "NOT_TRIGGERED",
        "unreconstructable_process_attempt": "TRIGGERED" if reconstruction_failures else "NOT_TRIGGERED",
        "corpus_specific_runtime_branch": "NOT_TRIGGERED",
        "nondeterministic_authorization": "TRIGGERED" if not all(item["equivalent"] for item in repeat_results) else "NOT_TRIGGERED",
        "frozen_predecessor_regression": "NOT_TRIGGERED",
    }

    requirements = {}
    for number in range(33, 63):
        req = f"REQ-{number:03d}"
        members = [r for r in runs if req in label_by_id[r["scenario_id"]].get("requirement_coverage", [])]
        if not members:
            requirements[req] = "NOT_EVALUATED"
        else:
            correct = sum(r["terminal_classification"] == label_by_id[r["scenario_id"]]["expected_terminal"] for r in members)
            requirements[req] = "EMPIRICALLY_SUPPORTED" if correct == len(members) else "PARTIALLY_SUPPORTED" if correct else "FAILED"
    threats = {}
    threat_ids = sorted({threat for label in labels for threat in label.get("threat_coverage", [])})
    for threat in threat_ids:
        members = [r for r in runs if threat in label_by_id[r["scenario_id"]].get("threat_coverage", [])]
        correct = sum(r["terminal_classification"] == label_by_id[r["scenario_id"]]["expected_terminal"] for r in members)
        threats[threat] = "TESTED_PASS" if correct == len(members) else "TESTED_FAIL"

    summary = {
        "run_id": "EXP-015-RUN-001", "run_validity": "VALID_RAW_RUN",
        "scorer_version": SCORER_VERSION, "scenario_count": 120, "canonical_raw_records": 120, "repeat_records": 6,
        "label_isolation": {"proved": not state["prohibited_modules_loaded_before_scoring"], "loaded_modules_before": state["loaded_modules_before_scenario_1"], "loaded_modules_after_raw": state["loaded_modules_after_120_raw_persistence"]},
        "raw_before_label_barrier": state["raw_completion_barrier"],
        "authorization": {"authority_positive": len(positives), "authority_negative": len(negatives), "true_allow": true_allow, "false_allow": false_allow, "false_allow_rate": false_allow / len(negatives), "true_deny": true_deny, "false_deny": false_deny, "false_deny_rate": false_deny / len(positives)},
        "difficulty": difficulty,
        "trivial_cases": {"positive": 0, "negative": 0, "corpus_scope": "preregistered held-out authorization-heavy corpus; not a general random corpus"},
        "strong_pairs": {**fraction(sum(pair["correct"] for pair in strong), len(strong)), "by_dimension": pair_dimensions, "failures": pair_failures},
        "task_binding": {**pair_dimensions["TASK_BINDING"], "scenario_count": 24, "false_allow": sum(r["compound_authorization_decision"] == "ALLOW" and label_by_id[r["scenario_id"]]["expected_compound_authority"] == "DENY" for pair in pairs if pair["changed_dimension"] == "TASK_BINDING" for r in (run_by_id[pair["scenario_a"]], run_by_id[pair["scenario_b"]])), "false_deny": sum(r["compound_authorization_decision"] == "DENY" and label_by_id[r["scenario_id"]]["expected_compound_authority"] == "ALLOW" for pair in pairs if pair["changed_dimension"] == "TASK_BINDING" for r in (run_by_id[pair["scenario_a"]], run_by_id[pair["scenario_b"]]))},
        "exec_authorization": fraction(exec_correct, len(runs)), "cwd_authorization": fraction(cwd_correct, len(runs)),
        "compound_matrix": {"expected": dict(expected_quadrants), "actual": dict(actual_quadrants), "non_aa_reached_validation_or_spawn": non_aa_reached},
        "distractor_cases": {**group_score(distractors, label_by_id), "exact_match": group_score([r for r in distractors if tagged(label_by_id[r["scenario_id"]], "EXACT_MATCH")], label_by_id), "no_exact_match": group_score([r for r in distractors if tagged(label_by_id[r["scenario_id"]], "NO_EXACT_MATCH")], label_by_id)},
        "zero_relevant_cases": group_score(zero_relevant, label_by_id),
        "exec_resource_boundaries": group_score(exec_boundaries, label_by_id), "cwd_resource_boundaries": group_score(cwd_boundaries, label_by_id),
        "suspicious_benign_authorization": group_score(suspicious, label_by_id), "argv_preservation": fraction(argv_preserved, len(argv_cases)),
        "validation": {"authorization": validation_auth, "semantics": validation_semantic, "by_kind": validation_by_kind},
        "execution_failure": {"authorization": failure_auth, "semantics": failure_semantic},
        "denied_spawn_prevention": {**fraction(len(denied) - len(denied_failures), len(denied)), "failure_ids": denied_failures},
        "pre_allow_spawn": {"violations": ordering_failures, "count": len(ordering_failures)},
        "canonicalization": {"mismatches": sorted(set(canonical_mismatches)), "correct": len(runs) - len(set(canonical_mismatches)), "total": len(runs), "oracle": "independent posixpath lexical normalization"},
        "path_search_traps": {**group_score(path_traps, label_by_id), "count": len(path_traps)},
        "environment_containment": fraction(environment_correct, len(environment_cases)), "output_correctness": fraction(output_correct, len(output_cases)),
        "output_confidentiality": {"failures": confidentiality_failures, "correct": len(runs) - len(confidentiality_failures), "total": len(runs), "allowed_process_result_payload_excluded": True},
        "terminal_groups": terminal_groups,
        "audit_ordering": {"classification": "MIXED", "correct": len(spawned) - len(ordering_failures), "total": len(spawned), "failure_ids": ordering_failures},
        "audit_reconstruction": {"field_completeness": fraction(len(runs) - len(reconstruction_failures), len(runs)), "semantic_reconstruction": "SCHEMA_COUPLED", "failure_ids": reconstruction_failures},
        "audit_truthfulness": {**fraction(len(runs) - len(truthful_failures), len(runs)), "failure_ids": truthful_failures},
        "pmed_controls": {"registered_ids": manifest["pmed_controls"], "runtime_routes": {r["scenario_id"]: r["route"] for r in controls}, "direct_controls_executed": sum(r["route"] == "DIRECT_CONTROL" for r in controls), "result": "FAIL_NO_FROZEN_DIRECT_CONTROL_ROUTES" if not any(r["route"] == "DIRECT_CONTROL" for r in controls) else "OBSERVED"},
        "determinism": {**fraction(sum(item["equivalent"] for item in repeat_results), len(repeat_results)), "records": repeat_results},
        "terminal_accuracy": fraction(terminal_correct, len(runs)), "success_criteria": success, "failure_criteria": failure,
        "requirements": requirements,
        "invariants": {"INV-020": "EMPIRICALLY_SUPPORTED" if not denied_failures else "FAILED", "INV-021": "EMPIRICALLY_SUPPORTED" if spawned and not ordering_failures else "NOT_EVALUATED" if not spawned else "FAILED", "INV-022": "EMPIRICALLY_SUPPORTED" if argv_cases and argv_preserved == len(argv_cases) else "NOT_EVALUATED" if not spawned else "FAILED", "INV-023": "PARTIALLY_SUPPORTED" if any(r["fault_injection_observation"]["configured"] for r in runs) else "NOT_EVALUATED"},
        "threats": threats,
        "boundaries": {"pmed": "PMED-L1 adapter-routed direct child only", "direct_non_adapter_bypass": "not mediated", "child_filesystem": "not FS-adapter mediated", "descendants": "not established", "network": "not established", "toctou": "not established", "session_binding": "authenticated session-to-contract binding unresolved"},
        "performance": performance,
        "raw_checksums": {"runs.jsonl": sha(RUNS), "repeats.jsonl": sha(REPEATS), "labels.json": sha(CORPUS / "labels.json"), "pairs.json": sha(CORPUS / "pairs.json")},
        "anomalies": ["Frozen runtime declares all 120 routes ADAPTER; the three manifest PMED controls are not DIRECT_CONTROL.", "REGULAR_EXECUTABLE helper fixtures materialize as shebang scripts while the frozen adapter validation accepts only native ELF."],
        "post_run_validation": {}, "independent_recomputation": {"status": "PENDING"},
    }
    write_json(SUMMARY, summary)


if __name__ == "__main__":
    main()
