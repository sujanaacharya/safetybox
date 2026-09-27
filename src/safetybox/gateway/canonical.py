"""Deterministic canonicalization and exact action fingerprinting."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit


def canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, bytes):
        return {"sha256": hashlib.sha256(value).hexdigest(), "length": len(value)}
    if isinstance(value, Mapping):
        return {str(key): canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [canonical_value(item) for item in value]
    raise TypeError(f"Unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def action_digest(
    *,
    subject: str,
    agent: str,
    task: str,
    operation: str,
    resource: str,
    arguments: Mapping[str, Any],
    capability_id: str,
    policy_digest: str,
) -> str:
    return digest(
        {
            "subject": subject,
            "agent": agent,
            "task": task,
            "operation": operation,
            "resource": resource,
            "arguments": arguments,
            "capability_id": capability_id,
            "policy_digest": policy_digest,
        }
    )


def normalize_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve(strict=False))


def normalize_url(url: str) -> tuple[str, str, int, str]:
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL userinfo is forbidden")
    if parsed.fragment:
        raise ValueError("URL fragments are forbidden")
    if not parsed.hostname:
        raise ValueError("URL host is required")
    scheme = parsed.scheme.lower()
    host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    port = parsed.port or (443 if scheme == "https" else 80)
    path = quote(unquote(parsed.path or "/"), safe="/%:@!$&'()*+,;=-._~")
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return scheme, host, port, path
