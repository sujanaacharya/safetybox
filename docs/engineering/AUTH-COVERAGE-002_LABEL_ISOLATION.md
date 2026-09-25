# AUTH-COVERAGE-002 label isolation

The planned physical package split is:

```text
runtime/ dev/ validation/ heldout-runtime/
analysis/ labels/ families/ pairs/ difficulty/
```

The canonical execution package contains exactly the frozen run manifest, runtime binding,
corpus binding, and scenario array—no additional innocuously named artifact is permitted.
Recursive, case-insensitive validation rejects symlinks, analysis path names, label files,
and prohibited JSON keys; strict scenario parsing rejects unknown fields at every nested
level. After preflight, an audit gate permits ordinary reads only of those exact runtime
files and frozen implementation artifacts, and writes only to the isolated result files
and exact governance-ledger paths. A fresh
process installs an import finder denying scorer, oracle, and label namespaces before the
runner is imported. The canonical CLI requires fresh output paths and is the only registered
held-out entry point. Ordinary pytest lacks its process attestation and is refused before
reservation or `STARTED`.

Development negative tests demonstrate that `labels.json` is physically absent, traversal
to an adjacent analysis directory fails, and scoring imports fail in the execution process.
The runner never imports `auth_coverage_metrics` or `auth_coverage_scoring`. Conversely, the
fresh scorer has no production-authorizer entry point and verifies `SEALED_RAW` before it
loads labels.

Python process attestation is cooperative research governance, not an OS sandbox. The
strong boundary is the separately assembled runtime-only directory plus frozen digests;
a privileged operator who deliberately replaces code and packages is outside the claim.
