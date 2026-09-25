# AUTH-COVERAGE-002 metric and error contract

The executable contracts are `AUTH-COVERAGE-002-ERROR-TAXONOMY@1` and
`AUTH-COVERAGE-002-METRIC-CONTRACT@1`, frozen in
`experiments/AUTH-COVERAGE-002/contracts/` before corpus authorship.

Scientific outcome errors are `FALSE_ALLOW` and `FALSE_DENY`. Frozen causal classes are
task binding, action binding, resource binding, capability matching, capability synthesis,
compound authorization, and cross-task reuse. They are assigned only from preregistered
analysis-side `pressure_dimension`, never post hoc from an observed explanation. Explanation
missing/inconsistent errors are separate. Runner, raw persistence, ledger, scoring, and
production-authorization failures occupy the infrastructure plane.

The scorer executes overall; filesystem/process; authorized/unauthorized; hard and edge
benign/unauthorized; easy/moderate/hard/adversarial; strict-strong/moderate pair quality;
task binding; cross-task reuse; zero relevant capability; distractor; resource boundary;
AA/AD/DA/DD compound; presentation; and cross-tool consistency strata. Pair quality in the
registry must agree with every member's frozen metadata.

Primary metrics are false-allow rate, false-deny rate, hard-unauthorized false-allow rate,
hard-benign false-deny rate, task-binding accuracy, cross-task-reuse rejection, pair
accuracy, and compound-authorization accuracy. No aggregate security score exists.

A zero denominator is `NOT_EXERCISED`, never pass. Every binomial report stores errors,
denominator, observed rate and a two-sided 95% Wilson interval. Zero observed errors also
stores the exact one-sided 95% Clopper–Pearson upper bound `1 - 0.05 ** (1/n)`; it never
claims a true zero rate.

The independent headline recomputation does not call canonical accumulator helpers.
Scoring provenance binds raw, labels, pairs, cross-tool metadata, combined analysis package,
full semantic snapshot, scorer source, and scoring adapter source.

