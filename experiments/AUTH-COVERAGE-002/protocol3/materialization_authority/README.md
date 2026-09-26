# Generator@3 materialization authority root

These JSON artifacts are the Protocol@3-provisioned, single-use authority root
for `AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1`. They are data, not outputs of the
Generator@3 materialization API. Their approved digests are compiled into the
verifier, and real materialization additionally requires each artifact's bytes
to be present unchanged in Git `HEAD`.

The public Python API has no real-authority issuance operation. The only
factory in `authority.py` requires explicit `SYNTHETIC` protocol, generator,
and attempt identities and rejects the real attempt. Synthetic artifacts are
test evidence only.

Gate A is deliberately absent at Generator@3 freeze. A future independent
Gate-A audit may add `gate-a-evidence.json` and `gate-a-approval.json` here.
Real HELD_OUT verification requires both files to be byte-identical to their
Git `HEAD` objects, requires the exact Protocol@3 decision, verifies DEV and
VALIDATION sealed-manifest digests, and recomputes the evidence digest. Gate A
cannot authorize production, and Gate B cannot authorize materialization.

Threat model: Git/object/digest reconciliation detects accidental changes and
ordinary direct-Python substitution. It is scientific-governance integrity,
not protection against an administrator who rewrites the repository, Git
history, verifier, and state together.
