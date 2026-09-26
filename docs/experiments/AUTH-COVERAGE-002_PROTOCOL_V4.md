# AUTH-COVERAGE-002 Protocol@4 preregistration

Identity: `AUTH-COVERAGE-002-PROTOCOL@4`. Protocol@4 supersedes only Protocol@3's
defective audit-substrate binding. It does not reopen or continue
`AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1`, which is permanently blocked.

Protocol@4 binds `AUTH-COVERAGE-002-SUBSTRATE@2` and reserves the new identity
`AUTH-COVERAGE-002-CORPUS@4-ATTEMPT-1`. Its initial canonical counts are DEV 0,
VALIDATION 0, and HELD_OUT 0. It creates no authority artifact and authorizes no
production evaluation.

The quantitative gate source remains the byte-identical Protocol@2/Protocol@3 table at
SHA-256 `a311763dbe8dfa656daf3cc25d1c6d4cc850755d1a4af4691c74b756ddbc0204`.
`SCIENTIFIC_THRESHOLD_CHANGE = 0` and `BENCHMARK_SEMANTIC_CHANGE = 0`. Gate A still
controls the one HELD_OUT materialization, and Gate B still controls the one production
execution after HELD_OUT sealing and final review.

The preserved Attempt-1 DEV and VALIDATION records are observed historical material.
The Protocol@4 contamination registry requires zero exact semantic-instance and canonical
input overlap for every future canonical split. The old Protocol@3 authority artifacts are
ineligible for any Protocol@4 use.

Generator@3 cannot be reused as an executable canonical generator. Its frozen code and
contract hard-bind Protocol@3, commit `6959866f9ddb298e9cf5153544dc8a4551a83265`,
`AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1`, the Protocol@3 authority digest registry, and
the Protocol@3 materialization root. Therefore Protocol@4 requires a future Generator@4.
Generator@4 may change only these version/authority/root bindings and add enforcement of
the Protocol@4 historical-contamination registry; Generator@3 benchmark semantics must
remain unchanged.
