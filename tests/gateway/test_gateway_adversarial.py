from __future__ import annotations

import sys
from collections.abc import Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from safetybox.gateway.canonical import action_digest, normalize_path
from safetybox.gateway.core import Gateway
from safetybox.gateway.demo import run_demo
from safetybox.gateway.models import Action, Decision
from safetybox.gateway.policy import GatewayPolicy

APPROVAL_TOKEN = "independent-operator-secret"


def policy_for(repo: Path, extra: dict[str, object] | None = None) -> GatewayPolicy:
    raw: dict[str, object] = {
        "version": "test-v1",
        "principal": "developer",
        "agent": "coding-agent",
        "task": "fix-login",
        "issuer": "test-operator",
        "repository": str(repo),
        "allow": [
            {"id": "read", "action": "filesystem.read", "resource": "repo/**"},
            {"id": "write-src", "action": "filesystem.write", "resource": "repo/src/**"},
            {
                "id": "exact-python",
                "action": "process.execute",
                "resource": Path(normalize_path(sys.executable)).name,
                "constraints": {
                    "argv": ["-c", "print('tests passed')"],
                    "cwd": normalize_path(repo),
                    "env": {},
                    "executable": normalize_path(sys.executable),
                },
            },
            {"id": "echo", "action": "mcp.call", "resource": "demo/echo"},
        ],
        "deny": [
            {"resource": "~/.ssh/**"},
            {"resource": "~/.aws/**"},
            {"resource": "repo/.env"},
        ],
        "approval_required": [
            {"action": "network.request"},
            {"action": "filesystem.write"},
        ],
        "flag": [],
        "mcp_servers": {
            "demo": [
                sys.executable,
                str(Path(__file__).parents[2] / "examples/mcp_echo_server.py"),
            ]
        },
    }
    if extra:
        raw.update(extra)
    return GatewayPolicy.from_mapping(raw, base_dir=repo.parent)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "login.py").write_text("BUG = True\n")
    (root / ".env").write_text("SECRET=yes\n")
    return root


@pytest.fixture
def gateway(repo: Path, tmp_path: Path) -> Gateway:
    return Gateway(
        policy_for(repo),
        audit_directory=tmp_path / "audit",
        approval_token=APPROVAL_TOKEN,
    )


def test_legitimate_coding_agent_path(gateway: Gateway, repo: Path) -> None:
    read = gateway.filesystem.request("read", repo / "src/login.py")
    assert read.executed and read.value == b"BUG = True\n"
    write = gateway.filesystem.request("write", repo / "src/login.py", data=b"BUG = False\n")
    assert write.executed
    test = gateway.process.execute(sys.executable, ["-c", "print('tests passed')"], cwd=repo)
    assert test.executed and test.value["returncode"] == 0
    assert repo.joinpath("src/login.py").read_text() == "BUG = False\n"
    assert gateway.audit.verify()
    assert len(gateway.audit.receipts.records) == 3


def test_end_to_end_login_bug_demo(tmp_path: Path) -> None:
    result = run_demo(tmp_path)
    assert result["tests_passed"]
    assert result["ssh_denied"]
    assert result["outside_not_executed"]
    assert result["approval_mutation_rejected"]
    assert result["approved_exact_action_executed"]
    assert result["audit_chain_valid"]


@pytest.mark.parametrize("relative", ["../outside", "src/../../outside", "./../outside"])
def test_path_traversal_and_relative_tricks_denied(
    gateway: Gateway, repo: Path, relative: str
) -> None:
    result = gateway.filesystem.request("write", repo / relative, data=b"x")
    assert result.authorization.decision is Decision.REQUIRE_APPROVAL
    assert not result.executed


def test_symlink_escape_denied(gateway: Gateway, repo: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "src/link").symlink_to(outside, target_is_directory=True)
    result = gateway.filesystem.request("write", repo / "src/link/pwned", data=b"x")
    assert result.authorization.decision is Decision.REQUIRE_APPROVAL
    assert not (outside / "pwned").exists()


def test_sensitive_files_explicitly_denied(gateway: Gateway, repo: Path) -> None:
    assert gateway.filesystem.request("read", repo / ".env").authorization.decision is Decision.DENY
    assert (
        gateway.filesystem.request("read", Path.home() / ".ssh/id_rsa").authorization.decision
        is Decision.DENY
    )
    assert (
        gateway.filesystem.request("read", Path.home() / ".aws/credentials").authorization.decision
        is Decision.DENY
    )


def test_resource_substitution_changes_digest(gateway: Gateway, repo: Path) -> None:
    (repo / "src/other.py").write_text("OTHER = True\n")
    first = gateway.filesystem.request("read", repo / "src/login.py")
    second = gateway.filesystem.request("read", repo / "src/other.py")
    assert first.authorization.action_digest != second.authorization.action_digest


@pytest.mark.parametrize(
    "field,value", [("task", "other"), ("agent", "other"), ("subject", "other")]
)
def test_identity_substitution_denied(gateway: Gateway, repo: Path, field: str, value: str) -> None:
    values = {
        "subject": "developer",
        "agent": "coding-agent",
        "task": "fix-login",
        "operation": "filesystem.read",
        "resource": normalize_path(repo / "src/login.py"),
    }
    values[field] = value
    result = gateway.authorize(Action(**values))
    assert result.decision is Decision.DENY


def test_capability_and_policy_substitution_change_digest(gateway: Gateway, repo: Path) -> None:
    action = Action(
        "developer",
        "coding-agent",
        "fix-login",
        "filesystem.read",
        normalize_path(repo / "src/login.py"),
    )
    base = dict(
        subject=action.subject,
        agent=action.agent,
        task=action.task,
        operation=action.operation,
        resource=action.resource,
        arguments=action.arguments,
    )
    one = action_digest(**base, capability_id="cap-a", policy_digest="policy-a")
    assert one != action_digest(**base, capability_id="cap-b", policy_digest="policy-a")
    assert one != action_digest(**base, capability_id="cap-a", policy_digest="policy-b")


def test_policy_authority_is_deeply_immutable(gateway: Gateway) -> None:
    constraints = gateway.policy.capabilities[2].constraints
    with pytest.raises(TypeError):
        constraints["argv"] = ("-c", "malicious")  # type: ignore[index]
    argv = constraints["argv"]
    assert isinstance(argv, tuple)
    with pytest.raises(AttributeError):
        argv.append("malicious")  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        gateway.policy.mcp_servers["demo"] = ("attacker",)  # type: ignore[index]


def test_duplicate_capability_ids_rejected(repo: Path) -> None:
    with pytest.raises(ValueError, match="unique"):
        policy_for(
            repo,
            {
                "allow": [
                    {"id": "duplicate", "action": "filesystem.read", "resource": "repo/**"},
                    {"id": "duplicate", "action": "filesystem.write", "resource": "repo/**"},
                ]
            },
        )


def test_exact_approval_single_use_and_mutation(gateway: Gateway, tmp_path: Path) -> None:
    target = tmp_path / "approved.txt"
    requested = gateway.filesystem.request("write", target, data=b"approved")
    assert requested.authorization.decision is Decision.REQUIRE_APPROVAL
    gateway.approve_once(
        requested.authorization.approval_id or "",
        requested.authorization.action_digest,
        approver="operator",
        approval_token=APPROVAL_TOKEN,
    )
    mutated = gateway.filesystem.request("write", target, data=b"mutated")
    assert mutated.authorization.decision is Decision.REQUIRE_APPROVAL
    assert not target.exists()
    exact = gateway.filesystem.request("write", target, data=b"approved")
    assert exact.executed and target.read_bytes() == b"approved"
    replay = gateway.filesystem.request("write", target, data=b"approved")
    assert replay.authorization.decision is Decision.REQUIRE_APPROVAL
    assert not replay.executed


def test_wrong_approval_digest_rejected(gateway: Gateway, tmp_path: Path) -> None:
    requested = gateway.filesystem.request("write", tmp_path / "x", data=b"x")
    with pytest.raises(ValueError):
        gateway.approve_once(
            requested.authorization.approval_id or "",
            "0" * 64,
            approver="operator",
            approval_token=APPROVAL_TOKEN,
        )
    gateway.approve_once(
        requested.authorization.approval_id or "",
        requested.authorization.action_digest,
        approver="operator",
        approval_token=APPROVAL_TOKEN,
    )


def test_policy_version_mutation_invalidates_approval(repo: Path, tmp_path: Path) -> None:
    first = Gateway(policy_for(repo), approval_token=APPROVAL_TOKEN)
    requested = first.filesystem.request("write", tmp_path / "x", data=b"x")
    first.approve_once(
        requested.authorization.approval_id or "",
        requested.authorization.action_digest,
        approver="operator",
        approval_token=APPROVAL_TOKEN,
    )
    second_policy = replace(first.policy, policy_digest="changed-policy-digest")
    second = Gateway(second_policy, approval_token=APPROVAL_TOKEN)
    second.authority.approvals.update(first.authority.approvals)
    retried = second.filesystem.request("write", tmp_path / "x", data=b"x")
    assert retried.authorization.decision is Decision.REQUIRE_APPROVAL
    assert not retried.executed


@pytest.mark.parametrize(
    "executable,argv",
    [
        ("sh", ["-c", "echo pwned"]),
        ("bash", ["-c", "echo pwned"]),
        (sys.executable, ["-c", "print('changed')"]),
    ],
)
def test_shell_interpreter_and_argv_substitution_denied(
    gateway: Gateway, repo: Path, executable: str, argv: list[str]
) -> None:
    result = gateway.process.execute(executable, argv, cwd=repo)
    assert result.authorization.decision is Decision.DENY
    assert not result.executed


def test_cwd_and_env_substitution_denied(gateway: Gateway, repo: Path, tmp_path: Path) -> None:
    cwd = gateway.process.execute(sys.executable, ["-c", "print('tests passed')"], cwd=tmp_path)
    env = gateway.process.execute(
        sys.executable, ["-c", "print('tests passed')"], cwd=repo, env={"PYTHONPATH": "/tmp"}
    )
    assert cwd.authorization.decision is Decision.DENY
    assert env.authorization.decision is Decision.DENY


def test_process_argv_is_snapshotted_once(gateway: Gateway, repo: Path, tmp_path: Path) -> None:
    marker = tmp_path / "argv-toctou-marker"

    class StatefulArgv:
        calls = 0

        def __iter__(self):  # type: ignore[no-untyped-def]
            self.calls += 1
            if self.calls == 1:
                return iter(["-c", "print('tests passed')"])
            return iter(["-c", f"open({str(marker)!r}, 'w').write('bypass')"])

    result = gateway.process.execute(sys.executable, StatefulArgv(), cwd=repo)
    assert result.executed
    assert not marker.exists()
    assert result.value["stdout"] == b"tests passed\n"


def test_host_scheme_port_and_method_change_digest(gateway: Gateway) -> None:
    actions = [
        Action(
            "developer",
            "coding-agent",
            "fix-login",
            "network.request",
            resource,
            {"method": method},
        )
        for resource, method in [
            ("https://example.com:443/x", "GET"),
            ("https://example.org:443/x", "GET"),
            ("http://example.com:80/x", "GET"),
            ("https://example.com:444/x", "GET"),
            ("https://example.com:443/x", "POST"),
        ]
    ]
    digests = {gateway.authorize(action).action_digest for action in actions}
    assert len(digests) == len(actions)


def test_url_userinfo_rejected_before_authorization(gateway: Gateway) -> None:
    with pytest.raises(ValueError, match="userinfo"):
        gateway.network.request("GET", "https://example.com@evil.example/path")


def test_network_host_override_rejected(gateway: Gateway) -> None:
    with pytest.raises(ValueError, match="Host"):
        gateway.network.request("GET", "https://example.com/path", headers={"Host": "evil.example"})


def test_network_redirect_is_not_followed(
    gateway: Gateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    requested = gateway.network.request("GET", "https://example.com/redirect")
    gateway.approve_once(
        requested.authorization.approval_id or "",
        requested.authorization.action_digest,
        approver="operator",
        approval_token=APPROVAL_TOKEN,
    )

    class Response:
        status = 302

        @staticmethod
        def read() -> bytes:
            return b""

        @staticmethod
        def getheaders() -> list[tuple[str, str]]:
            return [("Location", "https://evil.example/")]

    class Connection:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def request(self, *_args: object, **_kwargs: object) -> None:
            pass

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            pass

    monkeypatch.setattr(gateway.network, "_validated_addresses", lambda _host: ("203.0.113.1",))
    monkeypatch.setattr(
        gateway.network,
        "_open_connection",
        lambda _scheme, _host, _port, _address, _timeout: Connection(),
    )
    with pytest.raises(PermissionError, match="Redirects"):
        gateway.network.request("GET", "https://example.com/redirect")
    assert (
        gateway.audit.receipts.records[-1].payload["observed_effect"].startswith("EXECUTION_FAILED")
    )


def test_mcp_real_server_and_argument_mutation(gateway: Gateway) -> None:
    first = gateway.mcp.call("demo", "echo", {"text": "hello"})
    second = gateway.mcp.call("demo", "echo", {"text": "changed"})
    assert first.executed and first.value["content"][0]["text"] == "hello"
    assert first.authorization.action_digest != second.authorization.action_digest


def test_mcp_arguments_are_snapshotted_and_server_identity_is_trusted(gateway: Gateway) -> None:
    class StatefulArguments(Mapping[str, str]):
        calls = 0

        def __iter__(self) -> Iterator[str]:
            self.calls += 1
            return iter(("text",))

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> str:
            if key != "text":
                raise KeyError(key)
            return "approved" if self.calls == 1 else "mutated"

    result = gateway.mcp.call("demo", "echo", StatefulArguments())
    assert result.executed
    assert result.value["content"][0]["text"] == "approved"
    with pytest.raises(ValueError, match="Unknown"):
        gateway.mcp.call("attacker", "echo", {"text": "x"})
    with pytest.raises(ValueError, match="single path segments"):
        gateway.mcp.call("demo", "nested/tool", {"text": "x"})


def test_agent_cannot_self_approve_without_operator_credential(
    gateway: Gateway, tmp_path: Path
) -> None:
    requested = gateway.filesystem.request("write", tmp_path / "x", data=b"x")
    with pytest.raises(PermissionError, match="credentials"):
        gateway.approve_once(
            requested.authorization.approval_id or "",
            requested.authorization.action_digest,
            approver="self-claimed-operator",
            approval_token="attacker-controlled",
        )
    assert not (tmp_path / "x").exists()


def test_mcp_argument_mutation_after_approval(repo: Path) -> None:
    policy = policy_for(
        repo,
        {
            "allow": [],
            "approval_required": [{"action": "mcp.call"}],
        },
    )
    gateway = Gateway(policy, approval_token=APPROVAL_TOKEN)
    requested = gateway.mcp.call("demo", "echo", {"text": "approved"})
    gateway.approve_once(
        requested.authorization.approval_id or "",
        requested.authorization.action_digest,
        approver="operator",
        approval_token=APPROVAL_TOKEN,
    )
    mutated = gateway.mcp.call("demo", "echo", {"text": "changed"})
    assert mutated.authorization.decision is Decision.REQUIRE_APPROVAL
    exact = gateway.mcp.call("demo", "echo", {"text": "approved"})
    assert exact.executed


def test_expired_authority_denied(repo: Path) -> None:
    policy = policy_for(repo)
    expired = replace(policy.capabilities[0], expires_at=datetime.now(UTC) - timedelta(seconds=1))
    gateway = Gateway(replace(policy, capabilities=(expired, *policy.capabilities[1:])))
    result = gateway.filesystem.request("read", repo / "src/login.py")
    assert result.authorization.decision is Decision.DENY


def test_direct_api_bypass_is_outside_boundary(gateway: Gateway, repo: Path) -> None:
    target = repo.parent / "direct-bypass.txt"
    target.write_text("ordinary API bypasses library gateway")
    assert target.exists()
    mediated = gateway.filesystem.request("write", target, data=b"blocked")
    assert not mediated.executed


def test_audit_distinguishes_denial_from_effect_and_detects_tamper(
    gateway: Gateway, repo: Path
) -> None:
    denied = gateway.filesystem.request("read", repo / ".env")
    assert not denied.executed
    event_types = [record.payload["type"] for record in gateway.audit.events.records]
    assert event_types[-2:] == ["requested", "denied"]
    assert not gateway.audit.receipts.records
    gateway.audit.events.records[0].payload["resource"] = "tampered"
    assert not gateway.audit.verify()


def test_truncation_detected_with_retained_chain_head(gateway: Gateway, repo: Path) -> None:
    gateway.filesystem.request("read", repo / "src/login.py")
    gateway.filesystem.request("read", repo / "src/login.py")
    expected = gateway.audit.receipts.head
    gateway.audit.receipts.records.pop()
    assert not gateway.audit.receipts.verify(expected)


def test_concurrent_effects_preserve_audit_and_receipt_chains(gateway: Gateway, repo: Path) -> None:
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda _index: gateway.filesystem.request("read", repo / "src/login.py"),
                range(50),
            )
        )
    assert all(result.executed for result in results)
    assert gateway.audit.verify()
    assert gateway.audit.reconcile()
    assert all(
        record.payload["previous_receipt_hash"] == record.previous_hash
        for record in gateway.audit.receipts.records
    )
