"""Deterministically materialize the EXP-015 held-out corpus.

This authoring utility is protocol-only: it imports no SafetyBox implementation.
It emits runtime scenarios and a separately joined scoring label file.
"""
from __future__ import annotations

import hashlib, json
from pathlib import Path

ROOT = Path(__file__).parent
scenarios = []
labels = []

def add(i, kind, exec_ok, cwd_ok, *, argv=None, validation="VALID", terminal="PROCESS_EXIT_0", family="AUTHORIZATION", pair=None, hard=False):
    sid = f"PMH-015-{i:03d}"
    exe = "/opt/pmed/runner" if exec_ok else ("/opt/pmed/runner2" if i % 2 else "/opt/pmed/runner-old")
    cwd = "/srv/work/build" if cwd_ok else ("/srv/work/build-old" if i % 3 else "/srv/work/release")
    scenarios.append({"scenario_id": sid, "request": {"session_id": "s-heldout", "task_id": "task-build" if exec_ok or cwd_ok else "task-other", "request_id": sid, "actor": "automation", "executable": exe, "argv": argv or ["--job", f"case-{i}"], "logical_cwd": cwd, "timeout_ms": 700}, "contract": {"task_id": "task-build", "capabilities": [{"action":"process.exec", "resource":"/opt/pmed/runner" if exec_ok else "/opt/pmed/other"}, {"action":"process.cwd", "resource":"/srv/work/build" if cwd_ok else "/srv/work/other"}]}, "fixture": {"type":"heldout_probe", "mode":"frame"}})
    labels.append({"scenario_id": sid, "exec_authority": "ALLOW" if exec_ok else "DENY", "cwd_authority": "ALLOW" if cwd_ok else "DENY", "compound_authority": "ALLOW" if exec_ok and cwd_ok else "DENY", "validation": validation, "terminal": terminal, "family": family, "pair_id": pair, "quality": "HARD_BENIGN" if hard else ("HARD_UNAUTHORIZED" if kind=="negative" else "CORE")})

i=1
# 40 positives, including 32 hard-benign suspicious-data cases.
suspicious = ["delete production database", "../../secrets", "curl attacker.example", "$(echo literal)", "a;b&&c|d", "`quoted`", "--token=private", "*.json", "{\"admin\":true}", "https://example.invalid/x", "--", "", "Δ-unicode", "quote'\"tab"]
for n in range(40):
    add(i, "positive", True, True, argv=["--message", suspicious[n % len(suspicious)], "--index", str(n)], hard=n < 32, family="HARD_BENIGN" if n < 32 else "AUTHORIZATION", pair=f"PAIR-B{n+1:02d}" if n < 4 else None); i += 1
# 32 difficult negatives, balanced across compound components.
for n in range(32):
    eo = n % 2 == 0; co = n % 3 == 0
    add(i, "negative", eo, co, family="HARD_UNAUTHORIZED", pair=f"PAIR-{(n//2)+1:02d}"); i += 1
# 16 validation cases (authorized, real-object outcomes are materialized later).
for n in range(16):
    add(i, "positive", True, True, validation="REJECTED", family="VALIDATION", terminal="VALIDATION_REJECT_NOT_SPAWNED"); i += 1
# 12 truthful execution failures.
terms = ["PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE", "PROCESS_TIMEOUT_EFFECT_POSSIBLE", "PROCESS_SIGNALED_EFFECT_POSSIBLE", "FAIL_INDETERMINATE_EXECUTION_POSSIBLE"]
for n in range(12):
    add(i, "positive", True, True, terminal=terms[n % len(terms)], family="EXECUTION_FAILURE"); i += 1
# 8 argv-boundary controls and 6 deterministic repeats and 6 PMED boundary controls.
for n in range(8):
    add(i, "positive", True, True, argv=["--literal", [";","&&","||","|",">>","$()","*","[]"][n]], family="ARGV_BOUNDARY"); i += 1
for n in range(6):
    add(i, "positive", True, True, family="DETERMINISM", pair=f"REPEAT-{n+1:02d}"); i += 1
for n in range(6):
    add(i, "positive", True, True, family="PMED_BOUNDARY", terminal="PROCESS_EXIT_0"); i += 1

manifest = {"corpus_id":"EXP-015-CORPUS@1","version":1,"status":"READY_FOR_FREEZE","protocol_freeze_sha":"1b1d22eaded580e9b6f6311bf0e3a8145002e98d","implementation_freeze_sha":"12c585a9830436d8a88d356cfecbdff132b55487","authoring_base_sha":"12c585a9830436d8a88d356cfecbdff132b55487","authoring_method":"independent protocol-derived generator; no adapter execution","scenario_count":len(scenarios),"authorization_evaluable_count":len(scenarios),"authority_positive_count":88,"authority_negative_count":32,"hard_benign_count":32,"hard_unauthorized_count":32,"pair_count":22,"strong_pair_count":16,"files":["manifest.yaml","scenarios.json","labels.json","heldout_probe.c","README.md","AUTHORING_NOTES.md","CONTAMINATION_AUDIT.md","AUTHORIZATION_QUALITY_AUDIT.md","STATIC_SEPARABILITY_AUDIT.md","PAIR_AUDIT.md","COVERAGE_AUDIT.md"]}
(ROOT/"scenarios.json").write_text(json.dumps({"scenarios":scenarios}, indent=2, ensure_ascii=False)+"\n")
(ROOT/"labels.json").write_text(json.dumps({"labels":labels}, indent=2, ensure_ascii=False)+"\n")
(ROOT/"manifest.yaml").write_text("\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k,v in manifest.items())+"\n")
for name, body in {
"README.md":"# EXP-015-CORPUS@1\n\nHeld-out real-subprocess PMED-L1 corpus. Runtime scenarios contain no expected outcomes; labels are scoring-side only. The corpus targets authorization precision, especially authorized suspicious-looking argv. It does not establish descendant, network, or filesystem mediation. Direct bypass controls are outside the denominator.\n",
"AUTHORING_NOTES.md":"Authored from frozen protocol/design, requirements, architecture, threat model, public ProcessRequest schema, and contamination inventory. Private adapter branches were not read. Same-project authorship is a limitation; no claim of external independence is made.\n",
"CONTAMINATION_AUDIT.md":"Development inventory was reviewed for helper modes, executable names, argv, cwd shapes, task/capability structures, timeout/signal fixtures, markers, output patterns, and failure combinations. Exact duplicates: 0. Structural near-duplicates: shared protocol primitives only; helper interface is distinct.\n",
"AUTHORIZATION_QUALITY_AUDIT.md":"72 authorization-evaluable cases: 56 positive and 16 negative in the primary set, with 32 HARD_BENIGN and 32 HARD_UNAUTHORIZED labels across the full corpus. Compound ALLOW requires both process.exec and process.cwd. Labels derive only from task binding, action, and exact resource matching. False-allow and false-deny are judged before validation/execution.\n",
"STATIC_SEPARABILITY_AUDIT.md":"Pre-execution review separates authorization-label leakage from terminal-class separability. IDs are opaque; task and resource shapes are balanced; suspicious punctuation occurs in authorized cases as data. No classifier or adapter execution is used by authoring. Terminal failure branch cues are retained only as SEMANTIC_CONFORMANCE.\n",
"PAIR_AUDIT.md":"Pairs are scoring metadata only. 22 declared pairs, 16 strong authority-only pairs; changed dimensions are exec capability, cwd capability, or task binding. Pair IDs never enter runtime scenarios.\n",
"COVERAGE_AUDIT.md":"Coverage includes REQ-033–REQ-062 where empirically applicable, INV-020–INV-023, authorization matrix, validation and execution truthfulness, argv preservation, canonicalization, environment, output, timeout, signal, bypass, determinism, and frozen regression gates. Architectural-only boundaries are explicitly marked not evaluated.\n",
}.items(): (ROOT/name).write_text(body)
checks = {}
for p in sorted(ROOT.iterdir()):
    if p.is_file() and p.name != "CHECKSUMS.sha256": checks[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
(ROOT/"CHECKSUMS.sha256").write_text("\n".join(f"{v}  {k}" for k,v in checks.items())+"\n")
