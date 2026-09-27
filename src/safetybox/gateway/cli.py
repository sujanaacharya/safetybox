"""SafetyBox Gateway command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from safetybox.gateway.core import Gateway
from safetybox.gateway.demo import run_demo


def _effect_json(result: Any) -> dict[str, Any]:
    value = result.value
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    if isinstance(value, dict):
        value = {
            key: item.decode(errors="replace") if isinstance(item, bytes) else item
            for key, item in value.items()
        }
    return {
        "decision": result.authorization.decision.value,
        "authorized": result.authorization.authorized,
        "executed": result.executed,
        "action_digest": result.authorization.action_digest,
        "approval_id": result.authorization.approval_id,
        "effect_id": result.effect_id,
        "result_class": result.result_class,
        "value": value,
    }


def _dispatch(gateway: Gateway, request: dict[str, Any]) -> dict[str, Any]:
    kind = request.get("kind")
    if kind == "filesystem":
        data = request.get("data")
        result = gateway.filesystem.request(
            request["operation"], request["path"], data=data.encode() if data is not None else None
        )
    elif kind == "process":
        result = gateway.process.execute(
            request["executable"],
            request.get("argv", []),
            cwd=request["cwd"],
            env=request.get("env"),
        )
    elif kind == "network":
        body = request.get("body")
        result = gateway.network.request(
            request["method"],
            request["url"],
            body=body.encode() if body is not None else None,
            headers=request.get("headers"),
        )
    elif kind == "mcp":
        result = gateway.mcp.call(
            request["server"],
            request["tool"],
            request.get("arguments", {}),
        )
    elif kind == "approve":
        gateway.approve_once(
            request["approval_id"],
            request["action_digest"],
            approver=request["approver"],
            approval_token=request["approval_token"],
        )
        return {"approved": True}
    elif kind == "deny_approval":
        return {"denied": gateway.deny_approval(request["approval_id"])}
    else:
        raise ValueError(f"Unknown request kind: {kind}")
    return _effect_json(result)


def _gateway(args: argparse.Namespace) -> int:
    token = Path(args.approval_token_file).read_text().strip() if args.approval_token_file else None
    gateway = Gateway.from_policy(
        args.policy, audit_directory=Path(args.audit_dir), approval_token=token
    )
    print(
        json.dumps({"status": "ready", "policy_digest": gateway.policy.policy_digest}), flush=True
    )
    for line in sys.stdin:
        try:
            print(json.dumps(_dispatch(gateway, json.loads(line))), flush=True)
        except Exception as error:
            print(json.dumps({"error": type(error).__name__, "message": str(error)}), flush=True)
    return 0


def _verify(args: argparse.Namespace) -> int:
    gateway = Gateway.from_policy(args.policy, audit_directory=Path(args.audit_dir))
    integrity_valid = gateway.audit.verify(
        expected_audit_head=args.expected_audit_head,
        expected_receipt_head=args.expected_receipt_head,
    )
    reconciled = gateway.audit.reconcile()
    valid = integrity_valid and reconciled
    print(
        json.dumps(
            {
                "valid": valid,
                "events": len(gateway.audit.events.records),
                "receipts": len(gateway.audit.receipts.records),
                "audit_head": gateway.audit.events.head,
                "receipt_head": gateway.audit.receipts.head,
                "integrity_valid": integrity_valid,
                "reconciled": reconciled,
            }
        )
    )
    return 0 if valid else 1


def _mcp(args: argparse.Namespace) -> int:
    gateway = Gateway.from_policy(args.policy, audit_directory=Path(args.audit_dir))
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    configured = list(gateway.policy.mcp_servers.get(args.server, ()))
    if command and command != configured:
        raise ValueError("CLI upstream command does not match trusted policy configuration")
    result = gateway.mcp.call(
        args.server,
        args.tool,
        json.loads(args.arguments),
    )
    print(json.dumps(_effect_json(result)))
    return 0 if result.executed else 2


def _demo(args: argparse.Namespace) -> int:
    if args.work_dir:
        result = run_demo(Path(args.work_dir))
    else:
        with tempfile.TemporaryDirectory(prefix="safetybox-demo-") as temporary:
            result = run_demo(Path(temporary))
    print(json.dumps(result, sort_keys=True))
    return (
        0
        if all(
            result[key]
            for key in (
                "source_read",
                "source_fixed",
                "tests_passed",
                "ssh_denied",
                "outside_not_executed",
                "approval_requested",
                "approval_mutation_rejected",
                "approved_exact_action_executed",
                "audit_chain_valid",
            )
        )
        else 1
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="safetybox")
    commands = root.add_subparsers(dest="command_name", required=True)
    gateway = commands.add_parser("gateway", help="run the JSON-lines gateway")
    gateway.add_argument("--policy", required=True)
    gateway.add_argument("--audit-dir", default=".safetybox")
    gateway.add_argument("--approval-token-file")
    gateway.set_defaults(handler=_gateway)
    verify = commands.add_parser("verify", help="verify audit and receipt hash chains")
    verify.add_argument("--policy", required=True)
    verify.add_argument("--audit-dir", default=".safetybox")
    verify.add_argument("--expected-audit-head")
    verify.add_argument("--expected-receipt-head")
    verify.set_defaults(handler=_verify)
    mcp = commands.add_parser("mcp", help="make one mediated MCP tool call")
    mcp.add_argument("--policy", required=True)
    mcp.add_argument("--audit-dir", default=".safetybox")
    mcp.add_argument("--server", required=True)
    mcp.add_argument("--tool", required=True)
    mcp.add_argument("--arguments", default="{}")
    mcp.add_argument("command", nargs=argparse.REMAINDER)
    mcp.set_defaults(handler=_mcp)
    demo = commands.add_parser("demo", help="run the coding-agent acceptance demo")
    demo.add_argument("--work-dir")
    demo.set_defaults(handler=_demo)
    return root


def main() -> int:
    args = parser().parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
