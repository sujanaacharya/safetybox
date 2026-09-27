"""Tiny MCP-compatible JSON-RPC stdio server used by the v0.1 integration test."""

from __future__ import annotations

import json
import sys


def main() -> None:
    for line in sys.stdin:
        request = json.loads(line)
        params = request.get("params", {})
        if request.get("method") == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "safetybox-echo", "version": "0.1.0"},
                },
            }
        elif request.get("method") == "notifications/initialized":
            continue
        elif request.get("method") == "tools/call" and params.get("name") == "echo":
            result = {
                "content": [
                    {"type": "text", "text": str(params.get("arguments", {}).get("text", ""))}
                ]
            }
            response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32601, "message": "Method not found"},
            }
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
