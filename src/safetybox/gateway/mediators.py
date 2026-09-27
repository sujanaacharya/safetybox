"""Filesystem, process, HTTP(S), and MCP effect mediators."""

from __future__ import annotations

import http.client
import ipaddress
import json
import shutil
import socket
import ssl
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from safetybox.gateway.canonical import canonical_json, normalize_path, normalize_url
from safetybox.gateway.models import Action, EffectResult

if TYPE_CHECKING:
    from safetybox.gateway.core import Gateway


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, address: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self._address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self._address, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, address: str, timeout: float) -> None:
        self._ssl_context = ssl.create_default_context()
        super().__init__(host, port, timeout=timeout, context=self._ssl_context)
        self._address = address

    def connect(self) -> None:
        raw_socket = socket.create_connection((self._address, self.port), self.timeout)
        self.sock = self._ssl_context.wrap_socket(raw_socket, server_hostname=self.host)


class _Mediator:
    name = "mediator"

    def __init__(self, gateway: Gateway) -> None:
        self.gateway = gateway

    def _execute(self, action: Action, operation: Any) -> EffectResult:
        authorization = self.gateway.authorize(action)
        if not authorization.authorized:
            return EffectResult(authorization, False)
        self.gateway.authority.consume(authorization)
        self.gateway.audit.event(
            "execution_started", action, action_digest=authorization.action_digest, forwarded=True
        )
        try:
            value, result_class = operation()
        except Exception as error:
            effect_id = self.gateway.audit.receipt(
                action, authorization, self.name, f"EXECUTION_FAILED:{type(error).__name__}"
            )
            self.gateway.audit.event(
                "execution_failed",
                action,
                action_digest=authorization.action_digest,
                effect_id=effect_id,
                error_class=type(error).__name__,
            )
            raise
        effect_id = self.gateway.audit.receipt(action, authorization, self.name, result_class)
        self.gateway.audit.event(
            "effect_observed",
            action,
            action_digest=authorization.action_digest,
            effect_id=effect_id,
            result_class=result_class,
        )
        return EffectResult(authorization, True, value, effect_id, result_class)


class FilesystemMediator(_Mediator):
    name = "filesystem"

    def request(
        self,
        operation: Literal["read", "write", "create", "delete", "stat"],
        path: str | Path,
        *,
        data: bytes | None = None,
    ) -> EffectResult:
        resource = normalize_path(path)
        action_name = f"filesystem.{operation}"
        arguments: dict[str, Any] = {}
        if data is not None:
            arguments["data"] = data
        action = self._action(action_name, resource, arguments)

        def effect() -> tuple[Any, str]:
            target = Path(resource)
            if operation == "read":
                return target.read_bytes(), "READ_COMPLETE"
            if operation == "write":
                if data is None:
                    raise ValueError("write requires data")
                target.write_bytes(data)
                return None, "WRITE_COMPLETE"
            if operation == "create":
                if data is None:
                    raise ValueError("create requires data")
                with target.open("xb") as stream:
                    stream.write(data)
                return None, "CREATE_COMPLETE"
            if operation == "delete":
                target.unlink()
                return None, "DELETE_COMPLETE"
            stat = target.stat()
            return {"size": stat.st_size, "mode": stat.st_mode}, "STAT_COMPLETE"

        return self._execute(action, effect)

    def _action(self, operation: str, resource: str, arguments: Mapping[str, Any]) -> Action:
        return Action(
            self.gateway.policy.principal,
            self.gateway.policy.agent,
            self.gateway.policy.task,
            operation,
            resource,
            arguments,
        )


class ProcessMediator(_Mediator):
    name = "process"

    def execute(
        self,
        executable: str,
        argv: Sequence[str],
        *,
        cwd: str | Path,
        env: Mapping[str, str] | None = None,
        timeout: float = 60,
    ) -> EffectResult:
        argv_snapshot = tuple(argv)
        if any(not isinstance(item, str) for item in argv_snapshot):
            raise TypeError("Process argv must contain only strings")
        resolved = shutil.which(executable)
        if resolved is None:
            raise ValueError(f"Executable not found: {executable}")
        canonical_executable = normalize_path(resolved)
        canonical_cwd = normalize_path(cwd)
        supplied_env = dict(env or {})
        if any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in supplied_env.items()
        ):
            raise TypeError("Process environment keys and values must be strings")
        resource = Path(canonical_executable).name
        arguments = {
            "executable": canonical_executable,
            "argv": list(argv_snapshot),
            "cwd": canonical_cwd,
            "env": supplied_env,
            "timeout_seconds": repr(timeout),
        }
        action = Action(
            self.gateway.policy.principal,
            self.gateway.policy.agent,
            self.gateway.policy.task,
            "process.execute",
            resource,
            arguments,
        )

        def effect() -> tuple[Any, str]:
            completed = subprocess.run(
                [canonical_executable, *argv_snapshot],
                cwd=canonical_cwd,
                env=supplied_env,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            result = {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
            return result, "PROCESS_EXIT_0" if completed.returncode == 0 else "PROCESS_EXIT_NONZERO"

        return self._execute(action, effect)


class NetworkMediator(_Mediator):
    name = "network"

    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float = 10,
    ) -> EffectResult:
        scheme, host, port, path = normalize_url(url)
        method = method.upper()
        header_snapshot = dict(headers or {})
        if any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in header_snapshot.items()
        ):
            raise TypeError("HTTP header names and values must be strings")
        if any(key.lower() == "host" for key in header_snapshot):
            raise ValueError("Caller-supplied Host headers are forbidden")
        body_snapshot = None if body is None else bytes(body)
        resource = f"{scheme}://{host}:{port}{path}"
        arguments = {
            "method": method,
            "headers": header_snapshot,
            "body": body_snapshot,
            "timeout_seconds": repr(timeout),
        }
        action = Action(
            self.gateway.policy.principal,
            self.gateway.policy.agent,
            self.gateway.policy.task,
            "network.request",
            resource,
            arguments,
        )

        def effect() -> tuple[Any, str]:
            addresses = self._validated_addresses(host)
            connection = self._open_connection(scheme, host, port, addresses[0], timeout)
            try:
                connection.request(method, path, body=body_snapshot, headers=header_snapshot)
                response = connection.getresponse()
                payload = response.read()
                if 300 <= response.status < 400:
                    raise PermissionError(
                        "Redirects are not followed; authorize the destination separately"
                    )
                return {
                    "status": response.status,
                    "headers": dict(response.getheaders()),
                    "body": payload,
                }, f"HTTP_{response.status}"
            finally:
                connection.close()

        return self._execute(action, effect)

    @staticmethod
    def _validated_addresses(host: str) -> tuple[str, ...]:
        addresses = tuple(
            sorted(
                {
                    str(item[4][0])
                    for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
                }
            )
        )
        if not addresses:
            raise OSError("Destination host did not resolve")
        if any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise PermissionError("Non-global destination addresses are blocked")
        return addresses

    @staticmethod
    def _open_connection(
        scheme: str, host: str, port: int, address: str, timeout: float
    ) -> http.client.HTTPConnection:
        if scheme == "https":
            return _PinnedHTTPSConnection(host, port, address, timeout)
        return _PinnedHTTPConnection(host, port, address, timeout)


class McpMediator(_Mediator):
    name = "mcp"

    def call(
        self,
        server: str,
        tool: str,
        arguments: Mapping[str, Any],
        *,
        timeout: float = 10,
    ) -> EffectResult:
        if not server or "/" in server or not tool or "/" in tool:
            raise ValueError("MCP server and tool names must be non-empty single path segments")
        if server not in self.gateway.policy.mcp_servers:
            raise ValueError(f"Unknown policy-configured MCP server: {server}")
        upstream_command = self.gateway.policy.mcp_servers[server]
        argument_snapshot = json.loads(canonical_json(dict(arguments)))
        resource = f"{server}/{tool}"
        normalized_arguments = {
            "tool_arguments": argument_snapshot,
            "upstream_command": list(upstream_command),
            "timeout_seconds": repr(timeout),
        }
        action = Action(
            self.gateway.policy.principal,
            self.gateway.policy.agent,
            self.gateway.policy.task,
            "mcp.call",
            resource,
            normalized_arguments,
        )

        def effect() -> tuple[Any, str]:
            messages = [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "safetybox", "version": "0.1.0"},
                    },
                },
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": tool, "arguments": argument_snapshot},
                },
            ]
            request_bytes = "".join(
                json.dumps(message, separators=(",", ":")) + "\n" for message in messages
            ).encode()
            completed = subprocess.run(
                list(upstream_command),
                input=request_bytes,
                capture_output=True,
                env={},
                timeout=timeout,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError("Upstream MCP server failed")
            responses = [json.loads(line) for line in completed.stdout.splitlines()]
            initialized = next((item for item in responses if item.get("id") == 1), None)
            response = next((item for item in responses if item.get("id") == 2), None)
            if initialized is None or "error" in initialized:
                raise RuntimeError("Upstream MCP initialization failed")
            if response is None or "error" in response:
                raise RuntimeError("Invalid or error MCP response")
            return response["result"], "MCP_RESULT"

        return self._execute(action, effect)
