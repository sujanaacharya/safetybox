# EXP-014 Filesystem Adapter Technical Diligence Notes

**Scope:** technical review of the pre-corpus implementation freeze. This is not a
security certification, production-readiness statement, experiment result, or valuation
document.

The frozen architecture document retains its preregistration-time wording and byte
identity at `7baf20293caa83d3fff6a200174c4f8840918607`. This document, the development
validation report, requirement traceability, and
[`EXP-014_PRE_CORPUS_FREEZE_AUDIT.md`](EXP-014_PRE_CORPUS_FREEZE_AUDIT.md) are the additive
actual-state overlay; they do not revise the protocol.

1. **Is the adapter modular?** Yes at source level. Filesystem models, lexical
   canonicalization, mapping, validation, primitives, audit bridging, state observation,
   and orchestration are separate small modules. The component is still in-process.
2. **Is the trust boundary quickly understandable?** The adapter module and architecture
   document state untrusted request → lexical identity → M2/M1 authorization → physical
   validation → committed execution-start evidence → primitive. Direct routes are named
   bypasses.
3. **Are policy and filesystem behavior separated?** Yes. Policy consumes canonical
   logical resources through the existing `Authorizer`; the mapper and validator consume
   host paths. No filesystem-specific allowlist was added.
4. **Are errors explicit?** Public results use the five frozen categories and stable
   filesystem error codes. Underlying exceptions are chained for local diagnosis but
   arbitrary OS messages and host paths are not returned.
5. **Are versions exposed?** Yes: `FS-ADAPTER@1`, `FS-CANONICALIZATION@1`,
   `FS-AUDIT-ENVELOPE@1`, and `EXP014-STATE-DIGEST@1` appear in the public package and
   evidence.
6. **Is configuration explicit?** Host root, authorizer, policy reference, recorder, and
   optional primitive boundary are constructor dependencies. There is no root or policy
   singleton.
7. **Are side-effect paths tested?** Every requested operation has a real success path;
   all mutating denials compare independent state digests; failure tests cover no-effect,
   possible partial effect, and completion-audit loss. Finite tests do not prove every OS
   crash or race interleaving.
8. **Are limitations documented?** Yes. TOCTOU, direct-route bypass, link-count limits,
   Linux/local-filesystem assumptions, non-durable audit, sequential evaluation, and no
   production claim are explicit.
9. **Can it later sit behind an SDK/gateway?** The typed `FilesystemRequest` and
   `FilesystemResult` plus dependency injection form a usable internal boundary. A real
   gateway would still need authenticated identity, serialization/version negotiation,
   resource quotas, durable audit, cancellation, concurrency control, and interception.
10. **Is benchmark/test logic absent from production source?** Production behavior has no
    corpus ID, scenario ID, label, expected outcome, or development fixture branch.
    `EXP014` appears only in the mandated state-digest identifier and stable security error
    terminology.
11. **Can an external reviewer reproduce development validation?** Yes with the declared
    development environment and repository commands. The report records contaminated
    fixture families, and tests create only temporary roots.
12. **Is there a path to stronger mediation?** Yes, but it is not implemented. The next
    technical step after the frozen evaluation would be descriptor-relative Linux
    operations (`openat`/`openat2`-class controls), identity revalidation, durable audit,
    concurrency/race testing, then declared interception coverage. Those would support
    later FMED research; this adapter makes no FMED-L2/3/4 claim.

## Technical asset gate

| Dimension | Result | Rationale |
|---|---|---|
| Modularity | `PASS` | The adapter can be extracted without an experimental runner. |
| Testability | `PASS` | Root, authorizer, audit recorder/sink, and primitive boundary are injected. |
| Explainability | `PASS` | Canonical resources, subdecisions, rules, stages, and sequence links are attributable. |
| Failure honesty | `PASS` | Possible or known effects are never represented as denial, nonexecution, or rollback. |
| Claim discipline | `PASS` | FMED-L1 bypasses, RTM-0 status, and the lack of held-out evidence are explicit. |
| Reuse | `PASS_WITH_LIMITATION` | The typed API can sit behind later integrations, which still need identity, transport, quotas, concurrency, and interception. |
| Portability boundary | `PASS_WITH_LIMITATION` | Linux/local/case-sensitive assumptions are explicit; other filesystems are untested. |
| Security reviewability | `PASS_WITH_LIMITATION` | Sensitive stages are separated and small; `FilesystemAdapter.execute` remains a comparatively large orchestration function. |

## Self-critical findings

- The validation/operation gap permits name-to-object races; the implementation must not
  be deployed as a sandbox.
- The audit recorder is single-process mutable state and explicitly not safe for
  concurrent writers. EXP-014 v1 evaluates sequential deterministic mediation.
- `st_nlink == 1` is only a momentary observation and cannot prove unique reachability.
- State hashing is evidence instrumentation with I/O cost and its own observation races.
- A terminal audit failure necessarily leaves incomplete durable reconstruction even
  though the returned result truthfully reports `FAIL_INDETERMINATE`.
- Python callers retaining direct filesystem APIs can bypass the adapter by design.
- Development coverage is high but is contaminated unit/development evidence; only the
  future frozen corpus can evaluate the preregistered success criteria.
