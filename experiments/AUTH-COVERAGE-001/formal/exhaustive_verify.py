"""Bounded exhaustive invariant checker for AUTH-COVERAGE-001.

Run directly to emit a deterministic JSON report.  The state bounds are small
enough to enumerate without a solver and are stated in the emitted report.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import replace
from itertools import combinations

from authorization_model import (
    SPECIFICATION_ID,
    AuthorizationDecision,
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
    replace_non_authority_data,
    validate_delegation_chain,
)

VERIFIER_ID = "AUTH-COVERAGE-001-EXHAUSTIVE-VERIFIER@1"
TASKS = ("task.0", "task.1")
ACTIONS = (
    "filesystem.read",
    "filesystem.write",
)
RESOURCES = ("/r/a", "/r/b")


def _powerset(items: tuple[Capability, ...]) -> Iterable[tuple[Capability, ...]]:
    for size in range(len(items) + 1):
        yield from combinations(items, size)


def _request(task: str, action: str, resource: str) -> Request:
    return Request(
        request_id="opaque.0",
        subject="subject.0",
        session_id="session.0",
        task_id=task,
        tool=Tool.FILESYSTEM,
        components=(Component("filesystem", action, resource),),
    )


def _semantic_tuple(decision: AuthorizationDecision) -> tuple[Decision, tuple[Decision, ...]]:
    return decision.decision, tuple(item.decision for item in decision.subdecisions)


def _check_atomic_space(counters: dict[str, int]) -> int:
    states = 0
    for contract_task in TASKS:
        universe = tuple(
            Capability(f"cap.{index}", action, resource)
            for index, (action, resource) in enumerate(
                (action, resource) for action in ACTIONS for resource in RESOURCES
            )
        )
        for capabilities in _powerset(universe):
            available = {(item.action, item.resource) for item in capabilities}
            contract = Contract("contract.0", contract_task, capabilities)
            for request_task in TASKS:
                for action in ACTIONS:
                    for resource in RESOURCES:
                        states += 1
                        request = _request(request_task, action, resource)
                        decision = authorize(request, contract)
                        expected = (
                            Decision.ALLOW
                            if request_task == contract_task and (action, resource) in available
                            else Decision.DENY
                        )
                        assert decision.decision is expected
                        counters["NORMATIVE_SEMANTICS"] += 1

                        assert authorize(request, contract) == decision
                        counters["DETERMINISM"] += 1

                        assert explanation_complete(decision)
                        counters["EXPLANATION_COMPLETENESS"] += 1

                        reversed_contract = replace(
                            contract, capabilities=tuple(reversed(contract.capabilities))
                        )
                        assert decision_projection(authorize(request, reversed_contract)) == (
                            decision_projection(decision)
                        )
                        counters["NO_CAPABILITY_ORDER_EFFECT"] += 1

                        irrelevant_action = next(
                            candidate for candidate in ACTIONS if candidate != action
                        )
                        irrelevant = Capability("cap.irrelevant", irrelevant_action, resource)
                        extended = replace(
                            contract, capabilities=(*contract.capabilities, irrelevant)
                        )
                        assert _semantic_tuple(authorize(request, extended)) == _semantic_tuple(
                            decision
                        )
                        counters["NO_IRRELEVANT_CAPABILITY_EFFECT"] += 1

                        changed_data = replace_non_authority_data(
                            request,
                            argv=("password", "rm -rf /", "curl", "/etc/passwd"),
                            context=(("ai", "approve"), ("risk", "unknown")),
                        )
                        assert _semantic_tuple(authorize(changed_data, contract)) == (
                            _semantic_tuple(decision)
                        )
                        counters["NO_SUSPICIOUSNESS_AUTHORITY_EFFECT"] += 1
                        counters["NO_INNOCENCE_AUTHORITY_EFFECT"] += 1
                        counters["AI_CONTEXT_CANNOT_GRANT_AUTHORITY"] += 1
                        counters["UNKNOWN_CONTEXT_CANNOT_EXPAND_AUTHORITY"] += 1

                        renamed_request = replace(request, request_id="opaque.renamed")
                        renamed_contract = replace(contract, contract_id="contract.renamed")
                        assert decision_projection(authorize(renamed_request, contract)) == (
                            decision_projection(decision)
                        )
                        assert decision_projection(authorize(request, renamed_contract)) == (
                            decision_projection(decision)
                        )
                        counters["NO_OPAQUE_ID_EFFECT"] += 2

                        if request_task != contract_task:
                            assert decision.decision is Decision.DENY
                            counters["NO_CROSS_TASK_REUSE"] += 1
    return states


def _check_exact_boundaries(counters: dict[str, int]) -> int:
    states = 0
    for task in TASKS:
        for action in ACTIONS:
            for resource, sibling in (("/r/a", "/r/b"), ("/r/b", "/r/a")):
                capability = Capability("cap.exact", action, resource)
                contract = Contract("contract.exact", task, (capability,))
                assert (
                    authorize(_request(task, action, resource), contract).decision is Decision.ALLOW
                )
                assert (
                    authorize(_request(task, action, sibling), contract).decision is Decision.DENY
                )
                counters["EXACT_RESOURCE_BINDING"] += 1
                states += 2
    return states


def _check_no_synthesis(counters: dict[str, int]) -> int:
    states = 0
    for task in TASKS:
        for action in ACTIONS:
            other_action = next(candidate for candidate in ACTIONS if candidate != action)
            for resource, other_resource in (("/r/a", "/r/b"), ("/r/b", "/r/a")):
                capabilities = (
                    Capability("cap.right-action", action, other_resource),
                    Capability("cap.right-resource", other_action, resource),
                )
                contract = Contract("contract.split", task, capabilities)
                assert (
                    authorize(_request(task, action, resource), contract).decision is Decision.DENY
                )
                counters["NO_AUTHORITY_AMPLIFICATION"] += 1
                states += 1
    return states


def _process_request(task: str, executable: str, cwd: str) -> Request:
    return Request(
        request_id="opaque.process",
        subject="subject.0",
        session_id="session.0",
        task_id=task,
        tool=Tool.PROCESS,
        components=(
            Component("exec", "process.exec", executable),
            Component("cwd", "process.cwd", cwd),
        ),
        argv=("--literal", "secret"),
    )


def _check_compound_space(counters: dict[str, int]) -> tuple[int, dict[str, int]]:
    states = 0
    quadrants = {"AA": 0, "AD": 0, "DA": 0, "DD": 0}
    for contract_task in TASKS:
        universe = tuple(
            Capability(f"cap.process.{index}", action, resource)
            for index, (action, resource) in enumerate(
                (action, resource)
                for action in ("process.exec", "process.cwd")
                for resource in RESOURCES
            )
        )
        for capabilities in _powerset(universe):
            available = {(item.action, item.resource) for item in capabilities}
            contract = Contract("contract.process", contract_task, capabilities)
            for request_task in TASKS:
                for executable in RESOURCES:
                    for cwd in RESOURCES:
                        states += 1
                        request = _process_request(request_task, executable, cwd)
                        decision = authorize(request, contract)
                        exec_allowed = (
                            request_task == contract_task
                            and (
                                "process.exec",
                                executable,
                            )
                            in available
                        )
                        cwd_allowed = (
                            request_task == contract_task
                            and (
                                "process.cwd",
                                cwd,
                            )
                            in available
                        )
                        expected_parts = (
                            Decision.ALLOW if exec_allowed else Decision.DENY,
                            Decision.ALLOW if cwd_allowed else Decision.DENY,
                        )
                        assert (
                            tuple(item.decision for item in decision.subdecisions) == expected_parts
                        )
                        expected = Decision.ALLOW if exec_allowed and cwd_allowed else Decision.DENY
                        assert decision.decision is expected
                        quadrant = "".join(
                            "A" if value is Decision.ALLOW else "D" for value in expected_parts
                        )
                        quadrants[quadrant] += 1
                        counters["COMPOUND_SUBDECISION_INDEPENDENCE"] += 1
                        states += 0
    assert quadrants["AD"] > 0 and quadrants["DA"] > 0
    return states, quadrants


def _check_attenuation(counters: dict[str, int]) -> int:
    capability_templates = (
        Capability("cap.a", "filesystem.read", "/r/a"),
        Capability("cap.b", "filesystem.read", "/r/b"),
        Capability("cap.tree", "filesystem.read", "/r/**"),
    )
    probes = ("/r/a", "/r/b", "/r/nested/c")
    states = 0
    parent_sets = tuple(_powerset(capability_templates))
    child_sets = tuple(_powerset(capability_templates))
    for parent_caps in parent_sets:
        parent = DelegationAuthority("authority.parent", "task.0", parent_caps)
        parent_coverage = {
            probe
            for probe in probes
            if authorize(
                _request("task.0", "filesystem.read", probe),
                Contract("parent", "task.0", parent_caps),
            ).decision
            is Decision.ALLOW
        }
        for child_caps in child_sets:
            child = DelegationAuthority(
                "authority.child",
                "task.0",
                child_caps,
                parent_authority="authority.parent",
            )
            child_coverage = {
                probe
                for probe in probes
                if authorize(
                    _request("task.0", "filesystem.read", probe),
                    Contract("child", "task.0", child_caps),
                ).decision
                is Decision.ALLOW
            }
            expected = child_coverage <= parent_coverage
            assert authority_is_attenuation(child, parent) is expected
            counters["ATTENUATION_PRECURSOR"] += 1
            counters["NO_AUTHORITY_AMPLIFICATION"] += 1
            states += 1

    root = DelegationAuthority("root", "task.0", (capability_templates[2],))
    middle = DelegationAuthority(
        "middle",
        "task.0",
        (capability_templates[0],),
        parent_authority="root",
    )
    leaf = DelegationAuthority(
        "leaf",
        "task.0",
        (capability_templates[0],),
        parent_authority="middle",
    )
    assert validate_delegation_chain((root, middle, leaf))
    assert not validate_delegation_chain((root, replace(leaf, parent_authority="unknown")))
    counters["DELEGATION_CHAIN_PRECURSOR"] += 2
    return states


def _check_invalid_fail_closed(counters: dict[str, int]) -> int:
    valid_request = _request("task.0", "filesystem.read", "/r/a")
    valid_cap = Capability("cap.valid", "filesystem.read", "/r/a")
    malformed = (
        (replace(valid_request, components=()), Contract("contract", "task.0", (valid_cap,))),
        (
            replace(
                valid_request,
                components=(Component("filesystem", "filesystem.read", "/r/../a"),),
            ),
            Contract("contract", "task.0", (valid_cap,)),
        ),
        (
            valid_request,
            Contract(
                "contract",
                "task.0",
                (Capability("cap.invalid", "filesystem.read", "/r/../a"),),
            ),
        ),
        (
            valid_request,
            Contract("contract", "task.0", (valid_cap, replace(valid_cap))),
        ),
    )
    for request, contract in malformed:
        assert authorize(request, contract).decision is Decision.DENY
        counters["FAIL_CLOSED"] += 1
    return len(malformed)


def run_exhaustive_verification() -> dict[str, object]:
    """Enumerate every frozen bounded state and return the proof record."""
    invariant_names = (
        "NORMATIVE_SEMANTICS",
        "DETERMINISM",
        "EXPLANATION_COMPLETENESS",
        "NO_CAPABILITY_ORDER_EFFECT",
        "NO_IRRELEVANT_CAPABILITY_EFFECT",
        "NO_SUSPICIOUSNESS_AUTHORITY_EFFECT",
        "NO_INNOCENCE_AUTHORITY_EFFECT",
        "AI_CONTEXT_CANNOT_GRANT_AUTHORITY",
        "UNKNOWN_CONTEXT_CANNOT_EXPAND_AUTHORITY",
        "NO_OPAQUE_ID_EFFECT",
        "NO_CROSS_TASK_REUSE",
        "EXACT_RESOURCE_BINDING",
        "NO_AUTHORITY_AMPLIFICATION",
        "COMPOUND_SUBDECISION_INDEPENDENCE",
        "ATTENUATION_PRECURSOR",
        "DELEGATION_CHAIN_PRECURSOR",
        "FAIL_CLOSED",
    )
    counters = dict.fromkeys(invariant_names, 0)
    atomic_states = _check_atomic_space(counters)
    boundary_states = _check_exact_boundaries(counters)
    synthesis_states = _check_no_synthesis(counters)
    compound_states, quadrants = _check_compound_space(counters)
    attenuation_states = _check_attenuation(counters)
    invalid_states = _check_invalid_fail_closed(counters)
    total_states = (
        atomic_states
        + boundary_states
        + synthesis_states
        + compound_states
        + attenuation_states
        + invalid_states
    )
    assert all(count > 0 for count in counters.values())
    return {
        "verifier_id": VERIFIER_ID,
        "specification_id": SPECIFICATION_ID,
        "result": "PASS",
        "bounds": {
            "tasks": len(TASKS),
            "actions": len(ACTIONS),
            "resources": len(RESOURCES),
            "atomic_capability_subsets_per_contract_task": 2 ** (len(ACTIONS) * len(RESOURCES)),
            "process_capability_subsets_per_contract_task": 2**4,
            "attenuation_capability_sets": 2**3,
        },
        "state_counts": {
            "atomic": atomic_states,
            "exact_boundary": boundary_states,
            "no_synthesis": synthesis_states,
            "compound": compound_states,
            "attenuation_pairs": attenuation_states,
            "invalid": invalid_states,
            "total": total_states,
        },
        "compound_quadrants": quadrants,
        "invariant_checks": counters,
        "method": "deterministic exhaustive enumeration; no production imports; no solver",
        "claim_boundary": (
            "Proof is complete only for the stated finite abstraction, not for physical "
            "execution, identity, time, usage-count, destination, network, MCP, DB, or "
            "unbounded state spaces."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run_exhaustive_verification(), indent=2, sort_keys=True))
