# Protocol@4 materialization authority root

This directory is the Git-provisioned authority root for
`AUTH-COVERAGE-002-CORPUS@4-ATTEMPT-1`. The registry contains exactly one DEV,
one VALIDATION, and one future HELD_OUT artifact. DEV and VALIDATION are
`PROVISIONED_NOT_CONSUMED`. HELD_OUT is `NOT_AUTHORIZED_FOR_USE` until a future
Git-provisioned `AUTHORIZED_TO_MATERIALIZE_HELDOUT_ONCE` Gate-A decision binds
the sealed DEV and VALIDATION packages and its evidence digest.

The artifacts are governance data, not Generator@4 output. Generator@4 has no
real-authority issuance API. It accepts real artifacts only from these fixed
paths, only when their digests are registry members, and only when the bytes are
identical to Git `HEAD`. The synthetic factory rejects the real attempt.

This package authorizes no materialization by itself. The separate
`pre-materialization-decision.json` authorizes one future DEV and VALIDATION
materialization after this package is committed and pushed. It never authorizes
HELD_OUT or production.
