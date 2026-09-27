"""Human-readable policy loading and task-bound capability construction."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from safetybox.gateway.canonical import digest, normalize_path
from safetybox.gateway.models import Authority, freeze_value


@dataclass(frozen=True, slots=True)
class GatewayPolicy:
    version: str
    principal: str
    agent: str
    task: str
    issuer: str
    capabilities: tuple[Authority, ...]
    denied: tuple[Mapping[str, Any], ...]
    approval_required: tuple[Mapping[str, Any], ...]
    flags: tuple[Mapping[str, Any], ...]
    mcp_servers: Mapping[str, tuple[str, ...]]
    policy_digest: str

    @classmethod
    def load(cls, path: str | Path) -> GatewayPolicy:
        policy_path = Path(path)
        raw = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Policy must be a mapping")
        return cls.from_mapping(raw, base_dir=policy_path.parent)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any], *, base_dir: Path) -> GatewayPolicy:
        required = ("version", "principal", "agent", "task", "issuer")
        if any(not isinstance(raw.get(key), str) or not raw[key] for key in required):
            raise ValueError(f"Policy requires non-empty strings: {', '.join(required)}")
        normalized = dict(raw)
        repo_root = normalize_path(base_dir / str(raw.get("repository", ".")))
        normalized["repository"] = repo_root
        issued_at = datetime.now(UTC)
        capabilities: list[Authority] = []
        for index, item in enumerate(_rules(raw.get("allow", []), "allow")):
            resource = _expand_resource(str(item["resource"]), repo_root)
            expires = item.get("expires_at")
            constraints = _normalize_constraints(dict(item.get("constraints", {})), repo_root)
            capabilities.append(
                Authority(
                    capability_id=str(item.get("id", f"cap-{index + 1}")),
                    principal=str(raw["principal"]),
                    agent=str(raw["agent"]),
                    task=str(raw["task"]),
                    action=str(item["action"]),
                    resource=resource,
                    constraints=constraints,
                    issuer=str(raw["issuer"]),
                    issued_at=issued_at,
                    expires_at=(datetime.fromisoformat(str(expires)) if expires else None),
                )
            )
        capability_ids = [capability.capability_id for capability in capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("Capability IDs must be unique within a policy")
        raw_servers = raw.get("mcp_servers", {})
        if not isinstance(raw_servers, dict):
            raise ValueError("mcp_servers must be a mapping")
        mcp_servers: dict[str, tuple[str, ...]] = {}
        for name, command in raw_servers.items():
            if (
                not isinstance(name, str)
                or not name
                or not isinstance(command, list)
                or not command
                or any(not isinstance(part, str) or not part for part in command)
            ):
                raise ValueError("Each MCP server requires a name and non-empty command list")
            mcp_servers[name] = tuple(command)
        policy_hash = digest(normalized)
        return cls(
            version=str(raw["version"]),
            principal=str(raw["principal"]),
            agent=str(raw["agent"]),
            task=str(raw["task"]),
            issuer=str(raw["issuer"]),
            capabilities=tuple(capabilities),
            denied=tuple(
                freeze_value(_normalize_rule(item, repo_root))
                for item in _rules(raw.get("deny", []), "deny")
            ),
            approval_required=tuple(
                freeze_value(_normalize_rule(item, repo_root))
                for item in _rules(raw.get("approval_required", []), "approval_required")
            ),
            flags=tuple(
                freeze_value(_normalize_rule(item, repo_root))
                for item in _rules(raw.get("flag", []), "flag")
            ),
            mcp_servers=freeze_value(mcp_servers),
            policy_digest=policy_hash,
        )


def _rules(value: Any, name: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{name} must be a list of mappings")
    return value


def _expand_resource(resource: str, repo_root: str) -> str:
    if resource == "repo":
        return repo_root
    if resource.startswith("repo/"):
        suffix = resource[5:]
        wildcard = suffix.endswith("/**")
        if wildcard:
            suffix = suffix[:-3]
        expanded = normalize_path(Path(repo_root) / suffix)
        return f"{expanded}/**" if wildcard else expanded
    if resource.startswith("~/") or resource.startswith("/"):
        wildcard = resource.endswith("/**")
        value = resource[:-3] if wildcard else resource
        expanded = normalize_path(value)
        return f"{expanded}/**" if wildcard else expanded
    return resource


def _normalize_rule(item: Mapping[str, Any], repo_root: str) -> Mapping[str, Any]:
    result = dict(item)
    if "resource" in result:
        result["resource"] = _expand_resource(str(result["resource"]), repo_root)
    return result


def _normalize_constraints(constraints: dict[str, Any], repo_root: str) -> dict[str, Any]:
    for key in ("cwd", "executable"):
        value = constraints.get(key)
        if isinstance(value, str) and (value == "repo" or value.startswith("repo/")):
            constraints[key] = _expand_resource(value, repo_root)
    return constraints
