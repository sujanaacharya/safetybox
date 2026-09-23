# Trust Boundaries

| Boundary | Less-trusted side | More-trusted side | Required controls |
|---|---|---|---|
| User/content to agent | Prompts, retrieved data, tool output | Agent orchestration | Provenance labels; no assumption that content instructions are authorized |
| Agent to SafetyBox | Model output and tool requests | Interception and validation | Authenticated session, schema validation, canonicalization, complete mediation |
| SafetyBox control to adapter | Authorization decision | Execution adapter/sandbox | Request binding, freshness, least authority, result reporting |
| Adapter to resource | Tool parameters | OS/API/database enforcement | Native permissions, isolation, identity, operation-specific checks |
| Policy administration | Maintainer/config source | Active policy set | Authentication, review, versioning, separation from agent writes |
| Approval channel | Human/UI input | Controller state | Approver identity, scoped decision, expiry, anti-replay |
| Event producer to audit | Component observations | Ordered durable record | Trusted sequencing, integrity, backpressure, redaction |
| Experiment runtime to results | Potentially adversarial/nondeterministic runs | Final artifact store | Metadata validation, checksums, immutability, access control |

Complete mediation is a deployment property, not merely a library feature. If the agent retains direct credentials, shell access, network sockets, or an unwrapped tool path, the boundary is bypassed and relevant prevention claims do not apply.
