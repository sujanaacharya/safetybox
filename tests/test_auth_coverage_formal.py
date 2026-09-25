"""Development evidence for the AUTH-COVERAGE-001 formal model."""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "experiments" / "AUTH-COVERAGE-001" / "formal"
sys.path.insert(0, str(FORMAL))

from authorization_model import (  # noqa: E402
    SPECIFICATION_ID,
    Capability,
    Component,
    Contract,
    Decision,
    DelegationAuthority,
    Request,
    Tool,
    authority_is_attenuation,
    authorize,
    decision_projection,
    explanation_complete,
    resource_matches,
    validate_delegation_chain,
)
from exhaustive_verify import (  # noqa: E402
    VERIFIER_ID,
    run_exhaustive_verification,
)


def filesystem_request(
    *, task: str = "task-a", action: str = "filesystem.read", resource: str = "/work/a"
) -> Request:
    return Request(
        "opaque-request",
        "subject-a",
        "session-a",
        task,
        Tool.FILESYSTEM,
        (Component("filesystem", action, resource),),
    )


def contract(*capabilities: Capability, task: str = "task-a") -> Contract:
    return Contract("contract-a", task, capabilities)


def process_request(*, task: str = "task-a") -> Request:
    return Request(
        "opaque-process",
        "subject-a",
        "session-a",
        task,
        Tool.PROCESS,
        (
            Component("exec", "process.exec", "/bin/tool"),
            Component("cwd", "process.cwd", "/work/a"),
        ),
        argv=("password", "rm -rf", "/etc/passwd"),
    )


def test_formal_model_has_no_production_import() -> None:
    for filename in ("authorization_model.py", "exhaustive_verify.py"):
        tree = ast.parse((FORMAL / filename).read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported.update(
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        )
        assert not any(name == "safetybox" or name.startswith("safetybox.") for name in imported)


def test_exact_and_subtree_resource_semantics() -> None:
    assert resource_matches("/work/a", "/work/a")
    assert not resource_matches("/work/a", "/work/a/child")
    assert resource_matches("/work/**", "/work/a")
    assert resource_matches("/work/**", "/work/a/child")
    assert not resource_matches("/work/**", "/work")
    assert not resource_matches("/work/**", "/workish/a")
    assert not resource_matches("/work/**", "/work/../secret")


def test_task_binding_belongs_to_contract_not_capability_or_contract_identity() -> None:
    capability = Capability("cap-read", "filesystem.read", "/work/a")
    matching = contract(capability)
    renamed = replace(matching, contract_id="unrelated-provenance-name")

    allowed = authorize(filesystem_request(), matching)
    assert allowed.decision is Decision.ALLOW
    assert decision_projection(authorize(filesystem_request(), renamed)) == decision_projection(
        allowed
    )
    assert authorize(filesystem_request(task="task-b"), matching).decision is Decision.DENY
    assert (
        authorize(filesystem_request(task="task-b"), contract(capability, task="task-b")).decision
        is Decision.ALLOW
    )


def test_partial_capabilities_do_not_synthesize_atomic_authority() -> None:
    authority = contract(
        Capability("right-action", "filesystem.read", "/work/b"),
        Capability("right-resource", "filesystem.write", "/work/a"),
    )
    result = authorize(filesystem_request(), authority)
    assert result.decision is Decision.DENY
    assert result.subdecisions[0].rule == "AUTH.NO_MATCHING_CAPABILITY"


def test_process_compound_retains_all_four_subdecision_quadrants() -> None:
    exec_cap = Capability("exec", "process.exec", "/bin/tool")
    cwd_cap = Capability("cwd", "process.cwd", "/work/a")
    expected = {
        (): (Decision.DENY, Decision.DENY, Decision.DENY),
        (exec_cap,): (Decision.DENY, Decision.ALLOW, Decision.DENY),
        (cwd_cap,): (Decision.DENY, Decision.DENY, Decision.ALLOW),
        (exec_cap, cwd_cap): (Decision.ALLOW, Decision.ALLOW, Decision.ALLOW),
    }
    for capabilities, decisions in expected.items():
        result = authorize(process_request(), contract(*capabilities))
        assert (result.decision, *(item.decision for item in result.subdecisions)) == decisions


def test_generic_kernel_subtree_matching_also_applies_to_process_actions() -> None:
    authority = contract(
        Capability("exec-tree", "process.exec", "/bin/**"),
        Capability("cwd-tree", "process.cwd", "/work/**"),
    )
    assert authorize(process_request(), authority).decision is Decision.ALLOW


def test_argv_and_context_cannot_change_authority() -> None:
    authority = contract(Capability("exec", "process.exec", "/bin/tool"))
    alarming = process_request()
    innocent = replace(alarming, argv=("--help",), context=(("ai", "allow"),))
    assert decision_projection(authorize(alarming, authority)) == decision_projection(
        authorize(innocent, authority)
    )
    assert authorize(alarming, authority).decision is Decision.DENY


def test_explanation_completeness_is_mechanical() -> None:
    allowed = authorize(
        filesystem_request(),
        contract(Capability("cap-read", "filesystem.read", "/work/a")),
    )
    denied = authorize(filesystem_request(), contract())
    assert explanation_complete(allowed)
    assert explanation_complete(denied)
    assert set(denied.subdecisions[0].explanation()) == {
        "subject",
        "session",
        "task",
        "action",
        "resource",
        "capability",
        "rule",
        "authority_source",
        "component",
        "decision",
        "reason",
    }


def test_malformed_authority_fails_closed() -> None:
    duplicated = contract(
        Capability("duplicate", "filesystem.read", "/work/a"),
        Capability("duplicate", "filesystem.read", "/work/a"),
    )
    malformed_path = replace(
        filesystem_request(),
        components=(Component("filesystem", "filesystem.read", "/work/../secret"),),
    )
    assert authorize(filesystem_request(), duplicated).decision is Decision.DENY
    assert authorize(malformed_path, contract()).decision is Decision.DENY
    assert (
        authorize(replace(filesystem_request(), components=()), contract()).decision
        is Decision.DENY
    )


def test_delegation_precursor_accepts_only_attenuation() -> None:
    parent = DelegationAuthority(
        "parent",
        "task-a",
        (Capability("parent-tree", "filesystem.read", "/work/**"),),
    )
    child = DelegationAuthority(
        "child",
        "task-a",
        (Capability("child-exact", "filesystem.read", "/work/a"),),
        parent_authority="parent",
    )
    broader = replace(
        child,
        capabilities=(Capability("child-broad", "filesystem.read", "/**"),),
    )
    assert authority_is_attenuation(child, parent)
    assert not authority_is_attenuation(broader, parent)
    assert validate_delegation_chain((parent, child))
    assert not validate_delegation_chain((parent, replace(child, task_id="task-b")))


def test_bounded_exhaustive_verification_frozen_result() -> None:
    report = run_exhaustive_verification()
    frozen = json.loads((FORMAL / "exhaustive_results.json").read_text(encoding="utf-8"))
    assert report == frozen
    assert report["verifier_id"] == VERIFIER_ID
    assert report["specification_id"] == SPECIFICATION_ID
    assert report["result"] == "PASS"
    assert report["state_counts"] == {
        "atomic": 256,
        "exact_boundary": 16,
        "no_synthesis": 8,
        "compound": 256,
        "attenuation_pairs": 64,
        "invalid": 4,
        "total": 604,
    }
    assert report["compound_quadrants"] == {"AA": 32, "AD": 32, "DA": 32, "DD": 160}
    checks = report["invariant_checks"]
    assert isinstance(checks, dict)
    assert all(isinstance(count, int) and count > 0 for count in checks.values())


def test_formal_documents_bind_artifact_identities_and_limits() -> None:
    spec = (ROOT / "docs/experiments/AUTH-COVERAGE-001_AUTHORIZATION_SPEC.md").read_text()
    invariants = (ROOT / "docs/engineering/AUTH-COVERAGE-001_INVARIANTS.md").read_text()
    exhaustive = (
        ROOT / "docs/engineering/AUTH-COVERAGE-001_EXHAUSTIVE_VERIFICATION.md"
    ).read_text()
    assert SPECIFICATION_ID in spec
    assert "physical validation" in spec
    assert "same-team" in spec.lower()
    assert "NO_AUTHORITY_AMPLIFICATION" in invariants
    assert VERIFIER_ID in exhaustive
    assert "604" in exhaustive
    assert "not held-out production evidence" in exhaustive
