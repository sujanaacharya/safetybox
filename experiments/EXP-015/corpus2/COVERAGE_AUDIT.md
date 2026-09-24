# Coverage audit

| Area | Coverage |
| --- | --- |
| Authority | 60 allow / 60 deny; all exec/cwd quadrants |
| Task binding | 12 strong matched/mismatched pairs |
| Validation | 16 authority-positive fixture rejects: all executable and cwd kinds |
| Failure | 12 explicit terminal/fault recipes |
| argv | 40 literal-data cases, including empty, Unicode, quoting, metacharacters, URLs and paths |
| Environment/output | parent sentinels; stdout, stderr, both, empty/capture fault |
| Canonicalization | near-prefix boundaries; dot/dot-dot are schema-rejected and not runtime scenarios |
| PATH traps | declared sibling helper object without bare/relative execution |
| Requirements | REQ-033--062 mapped as held-out, expected-boundary, or not-evaluated at run scoring |
| Invariants | INV-020--023 covered by denials, ordering/fault, argv, and audit recipes |
| Threats | TOCTOU/descendants/network not established; privilege/resource exhaustion prohibited |

Success/failure criteria remain computable from labels plus raw records: authority,
spawn, ordering, argv, validation, environment, audit, direct controls, and
determinism. No runner-side hidden state is required.
