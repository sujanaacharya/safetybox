"""End-to-end coding-agent acceptance demonstration."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from safetybox.gateway.canonical import normalize_path
from safetybox.gateway.core import Gateway
from safetybox.gateway.models import Decision
from safetybox.gateway.policy import GatewayPolicy


def run_demo(work_directory: Path) -> dict[str, Any]:
    """Fix a login bug through the gateway and return acceptance evidence.

    Copying the immutable fixture is trusted demo setup, not an agent effect.
    Every action after setup is routed through the Gateway.
    """
    source = Path(__file__).parents[3] / "examples" / "login_bug_repo"
    repository = work_directory / "login-repository"
    shutil.copytree(source, repository)
    test_runner = normalize_path(Path(__file__).parents[3] / ".venv" / "bin" / "pytest")
    policy = GatewayPolicy.from_mapping(
        {
            "version": "demo-v0.1",
            "principal": "demo-developer",
            "agent": "coding-agent",
            "task": "fix-login-bug",
            "issuer": "demo-operator",
            "repository": str(repository),
            "allow": [
                {"id": "read-repo", "action": "filesystem.read", "resource": "repo/**"},
                {
                    "id": "write-auth-source",
                    "action": "filesystem.write",
                    "resource": "repo/src/**",
                },
                {
                    "id": "run-tests",
                    "action": "process.execute",
                    "resource": Path(test_runner).name,
                    "constraints": {
                        "executable": test_runner,
                        "argv": ["-q"],
                        "cwd": normalize_path(repository),
                        "env": {},
                    },
                },
            ],
            "deny": [
                {"resource": "~/.ssh/**"},
                {"resource": "~/.aws/**"},
                {"resource": "repo/.env"},
            ],
            "approval_required": [{"action": "filesystem.write"}],
            "flag": [],
        },
        base_dir=work_directory,
    )
    approval_token = "demo-operator-secret"
    gateway = Gateway(
        policy,
        audit_directory=work_directory / "audit",
        approval_token=approval_token,
    )

    source_path = repository / "src" / "login.py"
    observed = gateway.filesystem.request("read", source_path)
    fixed_source = observed.value.replace(
        b"record.password is password", b"record.password == password"
    )
    fixed = gateway.filesystem.request("write", source_path, data=fixed_source)
    tested = gateway.process.execute(test_runner, ["-q"], cwd=repository)

    ssh_denial = gateway.filesystem.request("read", Path.home() / ".ssh" / "id_rsa")
    outside_denial = gateway.filesystem.request(
        "write", work_directory / "outside.txt", data=b"blocked"
    )

    notes = repository / "acceptance.txt"
    requested = gateway.filesystem.request("write", notes, data=b"approved once\n")
    gateway.approve_once(
        requested.authorization.approval_id or "",
        requested.authorization.action_digest,
        approver="demo-operator",
        approval_token=approval_token,
    )
    mutation = gateway.filesystem.request("write", notes, data=b"mutated\n")
    approved = gateway.filesystem.request("write", notes, data=b"approved once\n")

    return {
        "source_read": observed.executed,
        "source_fixed": fixed.executed,
        "tests_passed": tested.executed and tested.value["returncode"] == 0,
        "test_stdout": tested.value["stdout"].decode(errors="replace"),
        "ssh_denied": ssh_denial.authorization.decision is Decision.DENY,
        "outside_not_executed": not outside_denial.executed,
        "approval_requested": requested.authorization.decision is Decision.REQUIRE_APPROVAL,
        "approval_mutation_rejected": not mutation.executed,
        "approved_exact_action_executed": approved.executed,
        "audit_chain_valid": gateway.audit.verify(),
        "effect_receipts": len(gateway.audit.receipts.records),
        "repository": str(repository),
    }
