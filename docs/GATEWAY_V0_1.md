# SafetyBox Gateway v0.1

The product path is:

```text
agent -> Gateway -> AuthorityEngine -> typed mediator -> real effect
```

Install with `python -m pip install -e '.[dev]'`, then run:

```bash
safetybox gateway --policy safetybox.yaml --audit-dir .safetybox
```

The gateway accepts one JSON object per stdin line. Example:

```json
{"kind":"filesystem","operation":"read","path":"README.md"}
```

An approval response contains `approval_id` and `action_digest`. Start the
gateway with `--approval-token-file` pointing to an operator-controlled secret.
The operator may send an `approve` request containing both values, an approver,
and that credential, then repeat the exact original request once. Any mutated
request receives a distinct digest and does not match the approval. Do not make
the credential available to the agent.

One-shot MCP call against the included stdio server:

```bash
safetybox mcp --policy safetybox.yaml --server demo --tool echo \
  --arguments '{"text":"hello"}' -- /usr/bin/python3 examples/mcp_echo_server.py
```

Verify persisted audit and receipt chains and their reconciliation:

```bash
safetybox verify --policy safetybox.yaml --audit-dir .safetybox
```

The command prints both chain heads. Retain them outside the audit directory
and provide them later with `--expected-audit-head` and
`--expected-receipt-head` to detect tail truncation.

See `SAFETYBOX_SECURITY_BOUNDARY.md` before deployment.

Run the complete login-bug coding-agent acceptance path with:

```bash
safetybox demo
```

The trusted harness copies a deliberately buggy repository into a temporary
directory. After that setup, source read/write, tests, denied sensitive access,
and the exact one-shot approval path all pass through the Gateway.

The MCP integration performs the standard initialize/initialized exchange and
one policy-authorized `tools/call` against a policy-configured stdio server.
