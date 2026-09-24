# EXP-014-CORPUS@1

**Version:** 1

**Status:** `READY_FOR_FREEZE`
**Primary evaluation unit:** one scenario/session

This package is the held-out, real-filesystem corpus for EXP-014. It specifies 96
deterministic fixtures and requests for the frozen `FS-ADAPTER@1` boundary. It tests the
nine frozen operations, task/capability authorization, lexical path identity, post-allow
physical validation, symlink and hard-link rejection, rename endpoint authorization,
nondisclosure, failure truthfulness, audit ordering/reconstruction, deterministic repeats,
and the explicitly bounded FMED-L1 direct-route controls.

It does not contain adapter predictions, execution records, results, thresholds, or
accuracy metrics. It does not test process confinement, shell interception, race-resistant
TOCTOU binding, Windows/macOS semantics, remote filesystems, durable audit, real-agent
integration, or FMED-L2/3/4. The corpus must not be executed until the separately governed
one-shot run.

## Held-out and label isolation design

Authorship began at implementation freeze
`b49a5cd0ff28a38eb8314291f51c106d2df9bd7c`, after the protocol/design freeze
`7baf20293caa83d3fff6a200174c4f8840918607`. Cases were derived from the frozen protocol,
requirements, architecture, threat model, operation semantics, and the frozen development
contamination inventory. Private adapter, canonicalizer, and validation branch logic was
not consulted. Public request/result and task-contract schemas were inspected only to make
the declarative serialization type-compatible; details are in
[AUTHORING_NOTES.md](AUTHORING_NOTES.md).

Runtime inputs are in [scenarios.yaml](scenarios.yaml). Ground truth, pair membership,
families, hard-negative markers, rationales, and coverage annotations are solely in
[labels.yaml](labels.yaml). `load_scenarios()` does not open the labels file. A future
runner must materialize and execute scenarios first, persist canonical records, and only
then join labels for scoring.

## Real-filesystem fixtures and safety

Every fixture path is a logical `/workspace` path. A future runner must map each scenario
to a fresh `TemporaryDirectory` on Linux and must never interpret a rejected host-like
string as a host execution target. Files, directories, relative and mapped-absolute
symlinks, hard links, and injected dependency failures are concrete enough to materialize
through existing test/dependency boundaries. Fixture contents, names, ordering, and request
bytes are deterministic. Hard-link scenarios declare an environment requirement; inability
to create a hard link is reported as `UNSUPPORTED_ENVIRONMENT`, never scored as a pass.

## FMED-L1 controls

FMED-L1 means only calls routed through the adapter are mediated. `FSH-014-091` uses a
direct `os.open`-style route and `FSH-014-092` uses direct `pathlib` writing inside an
isolated temporary root. Their classification is `EXPECTED_FMED_L1_BYPASS`; both are
excluded from the adapter authorization-correctness denominator. They demonstrate the
claim boundary and are not adapter failures. Shell is not included because it is outside
the frozen EXP-014 execution scope.

## Loading and integrity

The typed loader is
[`src/safetybox/experiments/exp014_corpus.py`](../../../src/safetybox/experiments/exp014_corpus.py).
It validates duplicate keys, identities, operations, paths, fixture types, injections,
request shapes, label taxonomy, pair structure, and label isolation without importing or
executing the adapter. Corpus integrity tests are in
[`tests/test_exp014_corpus.py`](../../../tests/test_exp014_corpus.py).

Exact file digests are recorded in [checksums.sha256](checksums.sha256). See
[CONTAMINATION_AUDIT.md](CONTAMINATION_AUDIT.md),
[STATIC_SEPARABILITY_AUDIT.md](STATIC_SEPARABILITY_AUDIT.md), and
[COVERAGE_AUDIT.md](COVERAGE_AUDIT.md) before freeze.
