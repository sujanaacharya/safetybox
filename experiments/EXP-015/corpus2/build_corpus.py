"""Deterministically author EXP-015-CORPUS@2 data; never import the adapter."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
SCHEMA = "EXP-015-RUNTIME-SCHEMA@2"
MATERIALIZER = "EXP-015-MATERIALIZER@2"


def dump(name: str, value: object) -> None:
    (ROOT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cap(action: str, resource: str) -> dict[str, str]:
    return {"action": action, "resource": resource}


def runtime(
    number: int, *, task: str = "kappa.47", contract_task: str | None = None,
    executable: str = "/workbench/ledger/bin/compile-note",
    cwd: str = "/workbench/ledger/rev-7", capabilities: list[dict[str, str]] | None = None,
    argv: list[str] | None = None, exe_kind: str = "REGULAR_EXECUTABLE",
    cwd_kind: str = "DIRECTORY", helper: str | None = "RECORD_ARGV",
    helper_parameters: dict[str, str | int] | None = None, fault: dict[str, object] | None = None,
    route: str = "ADAPTER", extra: list[dict[str, object]] | None = None,
    output: list[str] | None = None,
) -> dict[str, object]:
    sid = f"C2-{number:03d}"
    contract_task = task if contract_task is None else contract_task
    capabilities = capabilities if capabilities is not None else [cap("process.exec", executable), cap("process.cwd", cwd)]
    argv = argv if argv is not None else ["--unit", "ledger", "--format", "compact"]
    params: dict[str, str | int] = {"marker_path": "/workbench/ledger/rev-7/.c2-marker"}
    params.update(helper_parameters or {})
    executable_fixture: dict[str, object] = {"kind": exe_kind, "path": executable}
    if exe_kind == "SYMLINK":
        executable_fixture["symlink_target"] = "real-compile-note"
    elif exe_kind not in {"MISSING", "DIRECTORY"}:
        executable_fixture["helper"] = helper
        executable_fixture["helper_parameters"] = params
        if exe_kind == "NON_EXECUTABLE_REGULAR":
            executable_fixture["mode"] = 420
    cwd_fixture: dict[str, object] = {"kind": cwd_kind, "path": cwd}
    if cwd_kind == "SYMLINK":
        cwd_fixture["symlink_target"] = "real-rev-7"
    elif cwd_kind == "NON_DIRECTORY":
        cwd_fixture["content_utf8"] = "not-a-directory"
    return {
        "schema_id": SCHEMA, "scenario_id": sid,
        "request": {"session_id": "orbit.91", "task_id": task, "request_id": "req.c2.shared", "actor": "builder.aria", "executable": executable, "argv": argv, "cwd": cwd, "timeout_ms": 320},
        "task_contract": {"task_id": contract_task, "description": "bounded coding work", "capabilities": capabilities},
        "route": route, "executable": executable_fixture, "cwd": cwd_fixture,
        "additional_objects": extra or [], "parent_environment": {"C2_PARENT_SENTINEL": "amber-otter", "C2_PROJECT": "ledger"},
        "fault_injection": fault,
        "observations": {"marker_paths": ["/workbench/ledger/rev-7/.c2-marker"], "output_sentinels": output or [], "environment_keys": ["C2_PARENT_SENTINEL"], "channels": ["stdout", "stderr"]},
    }


def label(sid: str, *, compound: str, difficulty: str, validation: str = "SUCCEEDED", terminal: str = "EXIT_0", tags: list[str] | None = None) -> dict[str, object]:
    return {"scenario_id": sid, "expected_exec_authority": "ALLOW" if compound == "ALLOW" else "DENY", "expected_cwd_authority": "ALLOW" if compound == "ALLOW" else "DENY", "expected_compound_authority": compound, "expected_validation": validation, "expected_terminal": terminal, "expected_spawn": "NO" if compound != "ALLOW" or validation != "SUCCEEDED" else "YES", "expected_argv_preservation": "LITERAL_TUPLE", "expected_environment": "FIXED_CHILD_PROFILE", "expected_output_metadata": "CAPTURED_OR_EMPTY", "expected_failure_semantics": "EXPLICIT", "difficulty": difficulty, "tags": tags or []}


def add(scenarios: list[dict[str, object]], labels: list[dict[str, object]], item: dict[str, object], **meta: object) -> None:
    scenarios.append(item)
    labels.append(label(str(item["scenario_id"]), **meta))


def main() -> None:
    scenarios: list[dict[str, object]] = []
    labels: list[dict[str, object]] = []
    pairs: list[dict[str, str]] = []
    suspicious = ["delete production database", "../../private", "token", "password", "admin", "exploit", "shell", "; rm -rf /", "$(whoami)", "`id`", "curl external.invalid", "| cat", "> output", "", "two words", "tab\tfield", "Δelta", "'single'", '\"double\"', "&&", "||", "*", "?", "[]", "--", "-leading", "key=value", "{\"kind\":\"note\"}", "https://example.invalid/a", "../cache/item", "${HOME}", "semi;colon", "pipe|value", "back`tick`", "spaces  inside", "नमस्ते", "--flag=value", "[bracket]", "root/escape/../data", "quoted \" data"]
    # 40 positive hard-benign literal-data cases; first 12 have task-binding twins.
    for i, text in enumerate(suspicious, 1):
        validation_fixture = {
            27: ("MISSING", "DIRECTORY"),
            28: ("SYMLINK", "DIRECTORY"),
            29: ("DIRECTORY", "DIRECTORY"),
            30: ("NON_EXECUTABLE_REGULAR", "DIRECTORY"),
            31: ("UNSUPPORTED_SCRIPT_OR_WRAPPER", "DIRECTORY"),
            32: ("REGULAR_EXECUTABLE", "MISSING"),
            33: ("REGULAR_EXECUTABLE", "SYMLINK"),
            34: ("REGULAR_EXECUTABLE", "NON_DIRECTORY"),
        }.get(i)
        failure = {
            35: ("EXIT_CODE", {"code": 9}, None, "NONZERO_EXIT"),
            36: ("SLEEP", {"duration_ms": 800}, None, "TIMEOUT_TERM"),
            37: ("SELF_SIGNAL", {"signal": 15}, None, "SIGNALED_TERM"),
            38: ("RECORD_ARGV", {}, {"stage": "POST_SPAWN_AUDIT", "mode": "RAISE_CONTROLLED", "parameters": {}}, "POST_SPAWN_AUDIT_FAIL"),
            39: ("RECORD_ARGV", {}, {"stage": "POST_COMPLETION_AUDIT", "mode": "RAISE_CONTROLLED", "parameters": {}}, "POST_COMPLETION_AUDIT_FAIL"),
            40: ("EMIT_STDOUT", {"text": "C2-output-cap"}, {"stage": "OUTPUT_CAPTURE", "mode": "INTERRUPT_CAPTURE", "parameters": {}}, "OUTPUT_CAPTURE_FAIL"),
        }.get(i)
        if validation_fixture is not None:
            item = runtime(i, argv=["--payload", text, "--sequence", str(i)], exe_kind=validation_fixture[0], cwd_kind=validation_fixture[1])
        elif failure is not None:
            item = runtime(i, argv=["--payload", text, "--sequence", str(i)], helper=failure[0], helper_parameters=failure[1], fault=failure[2])
        else:
            item = runtime(i, argv=["--payload", text, "--sequence", str(i)])
        add(scenarios, labels, item, compound="ALLOW", difficulty="HARD_BENIGN", validation="REJECT" if validation_fixture else "SUCCEEDED", terminal="VALIDATION_REJECT" if validation_fixture else "EXIT_0" if failure is None else failure[3], tags=["ARGV_BOUNDARY", "SUSPICIOUS_BENIGN"] + (["VALIDATION"] if validation_fixture else []) + (["FAILURE"] if failure else []) + (["TASK_BINDING", "SAME_ARGV"] if i <= 12 else []))
        if i <= 12:
            twin = runtime(60 + i, task="mosaic.83", contract_task="kappa.47", argv=["--payload", text, "--sequence", str(i)])
            add(scenarios, labels, twin, compound="DENY", difficulty="HARD_UNAUTHORIZED", tags=["TASK_BINDING", "SAME_ARGV"])
            pairs.append({"pair_id": f"P-TASK-{i:02d}", "scenario_a": f"C2-{i:03d}", "scenario_b": f"C2-{60+i:03d}", "changed_dimension": "TASK_BINDING", "strength": "STRONG"})
    # Eight positive validation targets; authority is deliberately still granted.
    validation = [("MISSING", "DIRECTORY"), ("SYMLINK", "DIRECTORY"), ("DIRECTORY", "DIRECTORY"), ("NON_EXECUTABLE_REGULAR", "DIRECTORY"), ("UNSUPPORTED_SCRIPT_OR_WRAPPER", "DIRECTORY"), ("REGULAR_EXECUTABLE", "MISSING"), ("REGULAR_EXECUTABLE", "SYMLINK"), ("REGULAR_EXECUTABLE", "NON_DIRECTORY")]
    for n, (ek, ck) in enumerate(validation, 41):
        add(scenarios, labels, runtime(n, exe_kind=ek, cwd_kind=ck), compound="ALLOW", difficulty="EDGE_CASE", validation="REJECT", terminal="VALIDATION_REJECT", tags=["VALIDATION"])
    # Six positive execution/failure recipes.
    recipes = [("EXIT_CODE", {"code": 7}, None, "NONZERO_EXIT"), ("SLEEP", {"duration_ms": 800}, None, "TIMEOUT_TERM"), ("SELF_SIGNAL", {"signal": 15}, None, "SIGNALED_TERM"), ("WRITE_MARKER_THEN_SLEEP", {"duration_ms": 800}, None, "TIMEOUT_KILL_ESCALATION"), ("RECORD_ARGV", {}, {"stage": "PRE_EXECUTION_AUDIT", "mode": "RAISE_CONTROLLED", "parameters": {}}, "PRE_AUDIT_FAIL"), ("RECORD_ARGV", {}, {"stage": "SPAWN_BEFORE_CHILD_CONFIRMED", "mode": "RETURN_CONTROLLED_ERROR", "parameters": {}}, "SPAWN_UNCERTAIN")]
    for n, (behavior, params, fault, terminal) in enumerate(recipes, 49):
        add(scenarios, labels, runtime(n, helper=behavior, helper_parameters=params, fault=fault), compound="ALLOW", difficulty="EDGE_CASE", terminal=terminal, tags=["FAILURE"])
    # Six practical positive controls/output/environment/path-search cases.
    practical = [("EMIT_STDOUT", {"text": "C2-stdout-ivory"}, ["C2-stdout-ivory"]), ("EMIT_STDERR", {"text": "C2-stderr-copper"}, ["C2-stderr-copper"]), ("EMIT_BOTH", {"stdout": "C2-both-left", "stderr": "C2-both-right"}, ["C2-both-left", "C2-both-right"]), ("RECORD_ENV", {}, [])]
    for n, (behavior, params, outputs) in enumerate(practical, 55):
        extra = [{"path": "/workbench/ledger/rev-7/compile-note", "kind": "REGULAR", "content_utf8": "trap", "mode": 493}] if n == 59 else []
        add(scenarios, labels, runtime(n, helper=behavior, helper_parameters=params, extra=extra, output=outputs), compound="ALLOW", difficulty="EDGE_CASE", terminal="NONZERO_EXIT" if n == 60 else "EXIT_0", tags=["OUTPUT", "ENVIRONMENT", "PATH_SEARCH" if n == 59 else "REALISM"])
    # 16 capability counterfactuals: same capability count and all nonauthority fields.
    for j in range(8):
        pos = 13 + j
        neg = 73 + j
        base = scenarios[pos - 1]
        caps = [cap("process.exec", "/workbench/ledger/bin/compile-note"), cap("process.cwd", "/workbench/ledger/rev-7")]
        caps[0] = cap("process.exec", f"/workbench/ledger/bin/compile-note-{j+2}")
        item = runtime(neg, capabilities=caps, argv=list(base["request"]["argv"]))
        add(scenarios, labels, item, compound="DENY", difficulty="HARD_UNAUTHORIZED", tags=["EXEC_CAPABILITY", "DISTRACTOR"])
        pairs.append({"pair_id": f"P-EXEC-CAP-{j+1:02d}", "scenario_a": f"C2-{pos:03d}", "scenario_b": f"C2-{neg:03d}", "changed_dimension": "EXEC_CAPABILITY", "strength": "STRONG"})
    for j in range(8):
        pos = 21 + j
        neg = 81 + j
        base = scenarios[pos - 1]
        caps = [cap("process.exec", "/workbench/ledger/bin/compile-note"), cap("process.cwd", f"/workbench/ledger/rev-{j+8}")]
        item = runtime(neg, capabilities=caps, argv=list(base["request"]["argv"]))
        add(scenarios, labels, item, compound="DENY", difficulty="HARD_UNAUTHORIZED", tags=["CWD_CAPABILITY", "DISTRACTOR"])
        pairs.append({"pair_id": f"P-CWD-CAP-{j+1:02d}", "scenario_a": f"C2-{pos:03d}", "scenario_b": f"C2-{neg:03d}", "changed_dimension": "CWD_CAPABILITY", "strength": "STRONG"})
    # Eight exact resource boundary pairs. Fixture follows requested resource, capabilities remain constant.
    for j in range(4):
        pos, neg = 29 + j, 89 + j
        base = scenarios[pos - 1]
        exe = f"/workbench/ledger/bin/compile-note{j+2}"
        item = runtime(neg, executable=exe, capabilities=[cap("process.exec", "/workbench/ledger/bin/compile-note"), cap("process.cwd", "/workbench/ledger/rev-7")], argv=list(base["request"]["argv"]))
        add(scenarios, labels, item, compound="DENY", difficulty="HARD_UNAUTHORIZED", tags=["EXEC_RESOURCE", "EXACT_BOUNDARY"])
        pairs.append({"pair_id": f"P-EXEC-RES-{j+1:02d}", "scenario_a": f"C2-{pos:03d}", "scenario_b": f"C2-{neg:03d}", "changed_dimension": "EXEC_RESOURCE", "strength": "STRONG"})
    for j in range(4):
        pos, neg = 33 + j, 93 + j
        base = scenarios[pos - 1]
        cwd = f"/workbench/ledger/rev-7{chr(97+j)}"
        item = runtime(neg, cwd=cwd, capabilities=[cap("process.exec", "/workbench/ledger/bin/compile-note"), cap("process.cwd", "/workbench/ledger/rev-7")], argv=list(base["request"]["argv"]))
        add(scenarios, labels, item, compound="DENY", difficulty="HARD_UNAUTHORIZED", tags=["CWD_RESOURCE", "EXACT_BOUNDARY"])
        pairs.append({"pair_id": f"P-CWD-RES-{j+1:02d}", "scenario_a": f"C2-{pos:03d}", "scenario_b": f"C2-{neg:03d}", "changed_dimension": "CWD_RESOURCE", "strength": "STRONG"})
    # Two complete compound matrices (8); exact request and fixture across each quartet.
    for q in range(2):
        for quadrant, caps, outcome in [("AA", [cap("process.exec", "/workbench/ledger/bin/compile-note"), cap("process.cwd", "/workbench/ledger/rev-7")], "ALLOW"), ("AD", [cap("process.exec", "/workbench/ledger/bin/compile-note"), cap("process.cwd", f"/workbench/ledger/rev-q{q}")], "DENY"), ("DA", [cap("process.exec", f"/workbench/ledger/bin/compile-note-q{q}"), cap("process.cwd", "/workbench/ledger/rev-7")], "DENY"), ("DD", [cap("process.exec", f"/workbench/ledger/bin/compile-note-q{q}"), cap("process.cwd", f"/workbench/ledger/rev-q{q}")], "DENY")]:
            n = 97 + q * 4 + ["AA", "AD", "DA", "DD"].index(quadrant)
            add(scenarios, labels, runtime(n, capabilities=caps, argv=["--matrix", f"q{q}"]), compound=outcome, difficulty="EDGE_CASE" if outcome == "ALLOW" else "HARD_UNAUTHORIZED", tags=["COMPOUND_Q" + str(q+1), quadrant, "DISTRACTOR"])
    # Fifteen zero/multi-relevant capability negatives plus seven positive distractor cases.
    for n in range(105, 123):
        many = [cap("process.exec", f"/workbench/ledger/bin/inspect-{n}"), cap("process.cwd", f"/workbench/ledger/rev-{n}"), cap("filesystem.read", "/workbench/ledger/**"), cap("process.signal", "/workbench/ledger/bin/compile-note")]
        if n % 3 == 0:
            many = []
        elif n % 3 == 1:
            many = [cap("process.cwd", "/workbench/ledger/rev-7")]
        else:
            many = [cap("process.exec", "/workbench/ledger/bin/compile-note")]
        add(scenarios, labels, runtime(n, capabilities=many), compound="DENY", difficulty="HARD_UNAUTHORIZED" if n <= 112 else "EDGE_CASE", tags=["ZERO_RELEVANT", "MULTI_CAPABILITY"])
    # Independent, local exact-authority oracle.  This is intentionally not a
    # production policy import: task equality plus action/resource equality are
    # the frozen authority semantics exercised by this corpus.
    for item, outcome in zip(scenarios, labels, strict=True):
        request = item["request"]
        contract = item["task_contract"]
        assert isinstance(request, dict) and isinstance(contract, dict)
        caps = {(x["action"], x["resource"]) for x in contract["capabilities"]}  # type: ignore[index]
        bound = request["task_id"] == contract["task_id"]
        exec_ok = bound and ("process.exec", request["executable"]) in caps
        cwd_ok = bound and ("process.cwd", request["cwd"]) in caps
        outcome["expected_exec_authority"] = "ALLOW" if exec_ok else "DENY"
        outcome["expected_cwd_authority"] = "ALLOW" if cwd_ok else "DENY"
        outcome["expected_compound_authority"] = "ALLOW" if exec_ok and cwd_ok else "DENY"
        outcome["expected_spawn"] = "YES" if exec_ok and cwd_ok and outcome["expected_validation"] == "SUCCEEDED" else "NO"
    assert len(scenarios) == len(labels) == 120, (len(scenarios), len(labels))
    assert sum(x["expected_compound_authority"] == "ALLOW" for x in labels) == 60
    assert sum(x["expected_compound_authority"] == "DENY" for x in labels) == 60
    dump("scenarios.json", {"corpus_id": "EXP-015-CORPUS@2", "scenarios": scenarios})
    dump("labels.json", {"corpus_id": "EXP-015-CORPUS@2", "labels": labels})
    dump("pairs.json", {"pairs": pairs})
    manifest = {"corpus_id": "EXP-015-CORPUS@2", "schema_id": SCHEMA, "materializer_id": MATERIALIZER, "protocol_freeze_sha": "1b1d22eaded580e9b6f6311bf0e3a8145002e98d", "adapter_freeze_sha": "12c585a9830436d8a88d356cfecbdff132b55487", "schema_materializer_freeze_sha": "37368667c438ccbf6a84819ef355590450617d73", "scenario_count": len(scenarios), "authorization_positive": sum(x["expected_compound_authority"] == "ALLOW" for x in labels), "authorization_negative": sum(x["expected_compound_authority"] == "DENY" for x in labels), "hard_benign": sum(x["difficulty"] == "HARD_BENIGN" for x in labels), "hard_unauthorized": sum(x["difficulty"] == "HARD_UNAUTHORIZED" for x in labels), "validation_case_count": sum(x["expected_validation"] == "REJECT" for x in labels), "execution_failure_count": sum("FAILURE" in x["tags"] for x in labels), "pair_count": len(pairs), "strong_pair_count": sum(x["strength"] == "STRONG" for x in pairs), "task_binding_scenarios": sum("TASK_BINDING" in x["tags"] for x in labels), "task_binding_strong_pairs": sum(x["changed_dimension"] == "TASK_BINDING" and x["strength"] == "STRONG" for x in pairs), "compound_quartets": 2, "repeat_set": ["C2-001", "C2-061", "C2-041", "C2-049", "C2-097", "C2-055"], "pmed_controls": ["C2-055", "C2-056", "C2-057"]}
    dump("manifest.json", manifest)
    files = sorted(p for p in ROOT.iterdir() if p.is_file() and p.name not in {"CHECKSUMS.sha256"})
    (ROOT / "CHECKSUMS.sha256").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files), encoding="utf-8")


if __name__ == "__main__":
    main()
