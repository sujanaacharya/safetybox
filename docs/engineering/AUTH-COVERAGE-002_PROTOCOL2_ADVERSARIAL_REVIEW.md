# AUTH-COVERAGE-002 Protocol@2 independent adversarial review

**Review identity:** `AUTH-COVERAGE-002-PROTOCOL2-INDEPENDENT-REVIEW@1`

**Reviewed identities:** `AUTH-COVERAGE-002-PROTOCOL@2`,
`AUTH-COVERAGE-002-GENERATOR@2`

**Reviewer process:** independent agent review, source inspection, adversarial probes, and
fresh focused test execution

**Final disposition:** `NO_BLOCKING_FINDINGS`; freeze recommended

The review occurred before either freeze commit and before any new VALIDATION or HELD_OUT
realization. Findings were classified `RESOLVED`, `BOUNDED`, or `BLOCKING`. Every initially
blocking finding below was resolved in source and regression-tested before final signoff.

## Resolved findings

- `RESOLVED`: missing, NaN, non-object, boolean, and fractional-cardinality gate evidence
  now returns `BLOCK` rather than passing or raising.
- `RESOLVED`: alternating manifest order and the incomplete threshold-only order attack
  were replaced by seeded order randomization and frozen modulo-2-through-32 attacks.
- `RESOLVED`: runtime family tags no longer establish quotas. Pair-derived semantics and
  registered branch metadata must agree, and all 84 leaves/12 parents must exist.
- `RESOLVED`: label-specific `ZERO_RELEVANT` family tags and fixed q/z denial suffixes were
  removed. Secondary target label-rate deviations are all zero.
- `RESOLVED`: task/resource/action/synthesis quota attribution counts both independently
  audited pair endpoints. Full DEV-only capacity is 600/800/600/600 respectively.
- `RESOLVED`: process generation covers AA/AD/DA/DD at 1,000/333/334/333 in the 4,000-record
  DEV-only capacity simulation.
- `RESOLVED`: structural normalization abstracts irrelevant capability namespaces,
  argument keys, token values, and string lengths. The generator supplies genuinely
  distinct depth, cardinality, relation, and argument-container shapes.
- `RESOLVED`: full DEV-only structural capacity has 4,000 hashes, largest cluster one,
  and zero simulated DEV/VALIDATION structural overlap.
- `RESOLVED`: capability pair swaps cannot grade `STRICT_STRONG`; auxiliary argument or
  contract changes grade `STRONG_AUXILIARY`; opaque ID changes remain ignorable.
- `RESOLVED`: external packs reject invalid nested types, ID mismatches, reused pair
  endpoints, non-normative explanations, invalid structure, and dual-oracle disagreement.
- `RESOLVED`: expected explanation content is derived from runtime plus the frozen oracle,
  never copied from raw output.
- `RESOLVED`: all six raw-record mutations and all seven explanation mutations are caught.
- `RESOLVED`: each of five oracle semantic faults is detected in both faulty-oracle
  directions, including component-level cwd/exec confusion.
- `RESOLVED`: non-DEV materialization uses the OS CSPRNG and exposes no injected-allocator
  interface; authoring records contain no runtime IDs.
- `RESOLVED`: whole-input categories are computed over nested runtime strings. Full
  capacity yields 1,333 benign-looking unauthorized and 667 suspicious authorized.
- `RESOLVED`: final independent focused execution passed 66 tests and `git diff --check`.

## Competing-lab criticisms and bounds

1. `BOUNDED`: the 0.555 effect boundary uses a normal/binomial approximation; the fixed
   10,000-permutation procedure supplies the preregistered inferential check.
2. `BOUNDED`: a finite adversary suite cannot prove absence of every shortcut.
3. `BOUNDED`: robustness covers five DEV seeds rather than every possible seed.
4. `BOUNDED`: structural uniqueness relies substantially on combinations of depth,
   distractor cardinality, authority relation, and argument shape.
5. `BOUNDED`: combinatorial semantic diversity is not equivalent to independently authored
   natural-language narratives.
6. `BOUNDED`: both oracles and the bounded model are same-project implementations.
7. `BOUNDED`: selected mutation detection cannot establish independence for unknown shared
   misconceptions.
8. `BOUNDED`: focused raw tests construct production-shaped outputs; broader substrate
   regression tests supply production-policy coverage.
9. `BOUNDED`: exact explanation reasons are sensitive to future wording changes; frozen
   identities force versioning if wording changes.
10. `BOUNDED`: deterministic presentation vocabularies omit synonyms and pragmatic context.
11. `BOUNDED`: external family strings are open vocabulary, while pressure dimensions and
    canonical derived metrics remain constrained.
12. `BOUNDED`: duplicate OWASP precursor entries are possible but do not affect any gate.
13. `BOUNDED`: pair cue invariance compares cue classes rather than exact wording.
14. `BOUNDED`: generator leaf identity is analysis metadata; registry completeness,
    pair-derived family checks, and checksums bound fabrication.
15. `BOUNDED`: support 40 produces noisy raw branch proportions, but balanced paired
    construction and the fixed 0.05 bound make acceptance executable.
16. `BOUNDED`: DEV unit tests may use fewer permutations for speed; the executable default
    remains 10,000 and was exercised in the canonical DEV proof.
17. `BOUNDED`: rejected @1 observations informed thresholds; this is disclosed prior
    development knowledge and cannot serve as result evidence.
18. `BOUNDED`: seeded semantics are reproducible, so isolation depends on keeping generator
    internals out of production runtime inputs.
19. `BOUNDED`: shortcut attacks intentionally do not reimplement the normative oracle.
20. `BOUNDED`: mechanical pair review is generator-independent but not organizationally
    independent of the research team.
21. `BOUNDED`: perfect DEV structural clusters can appear engineered; frozen projection and
    complete distributions make that construction auditable.
22. `BOUNDED`: dual-oracle agreement cannot disprove a shared specification error.
23. `BOUNDED`: no HELD_OUT realization exists, so all present results are development proof.
24. `BOUNDED`: CSPRNG runtime IDs intentionally prevent byte-identical future runtime
    reproduction while semantic authoring remains deterministic.

## Final decision

No `BLOCKING` finding remains. The reviewer recommends freezing both identities from the
reviewed sources. This decision authorizes neither VALIDATION/HELD_OUT creation nor
production execution.
