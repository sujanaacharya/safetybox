# SafetyBox Gateway v0.1 security boundary

## Mediated boundary and guarantee

SafetyBox v0.1 mediates effects only when a caller uses `Gateway.filesystem`,
`Gateway.process`, `Gateway.network`, or `Gateway.mcp` (including requests sent
to the `safetybox gateway` CLI). Within those entry points, a protected effect
is forwarded only after deterministic authorization binds the principal, agent,
task, operation, normalized resource, normalized arguments, capability, and
policy digest. Forwarded effects receive a hash-chained receipt; requests and
decisions are separately hash-chained audit events.

`FLAG` records suspicion but preserves an otherwise valid authorization.
`REQUIRE_APPROVAL` never executes. Approval mints a short-lived, single-use
authority expansion for the exact pending action digest.

## Not mediated

This release is a library/CLI gateway, not an OS sandbox. It does not intercept
ordinary Python APIs, shell commands, agent syscalls, child-process syscalls,
container runtime calls, or traffic sent outside the gateway. An agent with
direct filesystem, process, socket, or upstream-MCP access can bypass it. Such
access must be removed by the operator (for example with a container, separate
Unix identity, seccomp, and egress firewall) if complete mediation is required.

## Known bypass boundaries and limitations

- Filesystem confinement resolves symlinks before authorization, but pathname
  replacement between validation and use (TOCTOU) is not eliminated.
- A permitted process is not sandboxed; its descendants and filesystem/network
  effects are outside the gateway boundary. Only tightly constrained commands
  should receive process authority.
- HTTP redirects are rejected. DNS is resolved once, non-global addresses are
  rejected, and the connection is pinned to a validated address while HTTPS
  retains the original hostname for SNI/certificate validation. Proxy
  environment variables are not used by the HTTP client.
- MCP v0.1 performs initialization and one request/response `tools/call` over a
  fresh stdio subprocess. It does not proxy long-lived sessions or protect a
  directly reachable upstream.
- Hash chains reveal modification or deletion when an expected chain head is
  retained; they are not signatures and a party able to replace the full log
  and trusted head can forge a new chain.
- Process stdout and network/MCP response bodies are returned to the caller and
  are not content-safety filtered.

## Trust assumptions and operator responsibilities

The operator controls policy issuance, protects policy and audit storage,
verifies agent/task identity at the integration boundary, supplies trustworthy
executables and MCP servers, constrains direct OS access, and retains trusted
chain heads and the approval credential outside agent reach. The Python runtime,
operating system, DNS resolver, CA store, and
gateway process are trusted. Policy authors must keep capabilities narrow,
especially process argv/environment and network destinations.

SafetyBox does not claim to secure all AI agents. It enforces authority only on
effects routed through the declared gateway boundary.
