# Capability Model

## Concept

A tool name is not sufficient authority. A capability binds an **actor**, **action**, **resource**, **scope**, **constraints**, **duration**, and **conditions**. It is derived from an authenticated task contract and current session state, is attenuable and revocable, and cannot exceed `maximum_privilege`.

```text
Capability = actor × action × resource × scope × constraints × duration × conditions
```

Examples of constraints include byte/row limits, command arguments, rate, working directory, allowed destination, data classification, approval state, and required sandbox. Conditions may refer only to defined observable state.

## Conceptual examples

```yaml
action: filesystem.read
actor: session-agent
resource: /workspace/project/**
constraints:
  denied:
    - ~/.ssh/**
    - ~/.aws/**
    - /etc/shadow
  follow_symlinks_outside_scope: false
duration: task-session
```

```yaml
action: network.connect
resource: internet
scope:
  allowed_domains: [api.example.com]
  allowed_ports: [443]
constraints:
  denied_by_default: true
  maximum_request_bytes: 100000
```

```yaml
action: shell.execute
scope:
  executables: [pytest, python]
constraints:
  dangerous_patterns: [sudo, chmod, "curl | sh"]
  working_directory: /workspace/project
  network: disabled
```

Pattern checks are defense-in-depth, not a complete shell security model; structured executable/argument mediation and OS isolation are preferable.

## Lifecycle and semantics

- **Grant:** created only by an authorized principal or contract loader and recorded as `CAPABILITY_GRANTED`.
- **Use:** request must match action and resource after canonicalization and satisfy every constraint.
- **Attenuation:** a child or degraded capability can only narrow authority.
- **Revocation/expiry:** takes effect atomically for new authorizations and emits `CAPABILITY_REVOKED`.
- **Delegation:** denied unless explicitly modeled; delegated authority cannot exceed the delegator or task ceiling.
- **Expansion:** requires an external authorized amendment and approval; never occurs silently.

Open design issues include canonical resource identity, TOCTOU resistance, symbolic-link and DNS rebinding behavior, capability token replay, and authority composition.

## Implemented and tested in M2

M2 implements immutable `Capability(action, resource)` values without constraints, duration, actor binding, delegation, attenuation, or revocation. A capability authorizes exactly one action and one of two resource forms:

- An exact string resource, such as `db:analytics`, matches only the identical request resource.
- A path subtree scope ending in `/**`, such as `/workspace/project/**`, matches only canonical absolute-path descendants such as `/workspace/project/src/a.py`. It does not match the root itself, `/workspace/project-secret/a.py`, or non-canonical paths containing empty, `.` or `..` segments.

The matcher performs no filesystem access or path resolution. It does not address symlinks, hard links, real-filesystem traversal, mount aliases, case-folding differences, TOCTOU/races, open file descriptors, OS-level direct access, or adapter bypass. Those protections require later adapter and deployment work.
