# EXP-015 Process Adapter Technical Diligence Notes

**Scope:** pre-corpus engineering review of `PROC-ADAPTER@1`. This is not a security
certification, experiment result, production-readiness claim, or implementation freeze.

## Pre-implementation policy-integrity gate

The immediate pre-design baseline is `d1053c26cdfad781894f57ecedefb07a39d84ca7`.
Comparing that tree to the frozen preregistration commit
`1b1d22eaded580e9b6f6311bf0e3a8145002e98d` found **no modification under `src/`,
`tests/`, or `pyproject.toml`**. Therefore there is no production-source file or symbol to
classify and no existing production caller changed during preregistration.

The reported policy-engine modification was reviewed separately because of its name:

| File | Symbol/section | Exact semantic effect | Runtime changed | Authorization changed | Existing callers changed | Needed for registration/design | Pre-freeze implementation | Classification |
|---|---|---|---|---|---|---|---|---|
| `docs/architecture/POLICY_ENGINE.md` | `Authority and behavior separation` | States that trusted authority, behavior findings, AI output, and future reviewed authority transitions are separate planes. | No | No | No | Yes | No | `DOCUMENTATION_ONLY` |

No `TYPE/REGISTRY_ONLY_NO_RUNTIME_CHANGE`, `ADDITIVE_NONBEHAVIORAL`,
`RUNTIME_BEHAVIOR_CHANGE`, or `AUTHORIZATION_BEHAVIOR_CHANGE` source change existed in
the baseline-to-freeze diff. No subprocess implementation existed. The critical gate
therefore passed before any implementation edit in this worktree.

## Assessment

1. **Modularity.** Typed models, canonicalization, validation, primitive execution,
   audit bridging, versions, errors, and orchestration have separate production modules.
2. **Authorization-core reuse.** `CompoundActionAuthorizer` is a generic ordered
   composition extension. It delegates both `process.exec` and `process.cwd` ordinary
   requests to the injected authoritative `TaskContractPolicy`; it owns no permissions.
   `ReferenceMonitor` remains the sole allow-to-execution gate.
3. **Policy separation.** The process package contains no executable allowlist, fixture
   name, label, risk score, AI decision, or argument-content policy. Exact executable
   authority comes from exact capabilities in the development contract.
4. **Validation separation.** Host inspection starts only in the reference monitor's
   post-allow lifecycle hook. Missing, symlinked, wrong-type, non-executable, and script
   objects are tool validation outcomes, not authorization denials.
5. **Typed API.** `ProcessRequest`, `ProcessResult`, terminal/category enums, and the
   immutable envelope provide a stable in-process boundary. Raw `OSError` text is not a
   semantic API.
6. **Primitive seam.** `RealProcessPrimitive.spawn_and_wait` contains the only production
   `Popen` call added for PMED-L1 and exposes invocation snapshots, child state, token,
   PID, wait, termination, and bounded output evidence.
7. **Failure honesty.** Known no-child failure is distinct from validation, nonzero exit,
   timeout, signal, and unknown post-invocation state. A real `Popen` `OSError` is
   conservatively indeterminate because the API does not prove that no fork occurred.
   Post-spawn audit loss is indeterminate; no rollback is asserted.
8. **Audit explainability.** Each component retains session, task, action, canonical
   resource, matched/absent capability, rule, contract reference, component identity,
   decision, and deterministic reason. Raw argv/output/environment are excluded.
9. **Future SDK/MCP reuse.** Dependency injection and typed values are suitable for an
   internal SDK boundary. An external integration still needs authenticated identity,
   serialization/version negotiation, durable audit, quotas, cancellation, concurrency,
   and interception coverage.
10. **PMED-L1 bypass.** Direct Python/native/shell routes bypass the adapter. The safe
    direct-`Popen` development control demonstrates that boundary explicitly.
11. **Process tree.** Only the direct child is mediated. Descendant creation,
    daemonization, process groups, namespaces, cgroups, and syscall confinement are not
    implemented.
12. **Session binding.** Task mismatch is enforced by `TaskContract.task_id`; session is
    preserved in component requests and audit. Authenticated contract-to-session binding
    remains an unresolved schema/deployment gap.
13. **TOCTOU.** Component `lstat`, mode/format inspection, and later pathname `Popen` do
    not bind one inode across the gap. This is explicit and not described as race-proof.
14. **Cross-platform scope.** Native-format validation currently requires ELF, and
    timeout/signal claims are Linux/POSIX only. No Windows equivalence is claimed.
15. **Concurrency.** There is no process-global request state, but the canonical audit
    recorder and primitive observations are not claimed safe for concurrent writers.
    Development is sequential.

## Static review findings

Production process creation added by EXP-015 is confined to
`src/safetybox/process/primitive.py`. It passes a tuple, an explicit executable,
`shell=False`, fixed environment, closed stdin, captured byte streams, and `close_fds`.
The adapter never imports `subprocess`, reconstructs a command string, calls a shell, or
searches `PATH`.

Pre-existing production matches outside the process package are not changed:

- references to `exec` in interfaces/documentation mean method names or conceptual tool
  execution, not OS process creation;
- no pre-existing `os.system`, `subprocess.run`, `subprocess.Popen`, `posix_spawn`, or
  `os.exec*` production route was found at review time; and
- filesystem code uses `os.open` for file operations, which is unrelated to process
  creation and remains governed by FMED-L1's separate boundary.

Development-only `subprocess.run` compiles the native helper into pytest temporary
storage, and development-only direct `Popen` demonstrates `EXPECTED_PMED_L1_BYPASS`.
The helper accepts only path-free marker basenames, performs bounded writes/output/sleep,
and has no network, shell, child-process, privilege, or arbitrary-command operation.

## Self-critical limitations

- An allowed native executable can interpret powerful arguments; exact argv boundaries
  do not authorize or make those semantics safe.
- Fixed environment and no `PATH` prevent inheritance ambiguity, not child syscall access.
- An authorized child can access filesystem and network directly and can create
  descendants. No network test or external call was made.
- Incremental capture bounds retained bytes, but output rate, CPU, memory, and process
  count are not OS-confined resources.
- Path replacement races and direct-route bypass mean this adapter is not a sandbox.
- In-memory audit can fail and is neither durable nor tamper-evident.
- High coverage, 0/10 development false allows, and 0/31 development false denies are
  contaminated engineering evidence only; held-out correctness remains unknown.
