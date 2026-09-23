# EXP-009 Claim Synthesis v1

## 1. Experiment scope

This synthesis evaluates what the frozen EXP-009 base result and its three preregistered ablations support for H-02 and CL-002. It covers the deterministic M5 observational trajectory monitor on the 80-scenario synthetic held-out `EXP-009-CORPUS@1` corpus. It does not change the detector, corpus, labels, protocol, or any base or ablation result.

The result is evidence about detection and interpretation, not prevention. M5 observes canonical terminal events and emits findings; it does not block, contain, mutate capabilities, or prevent tool-side effects.

## 2. Frozen evidence set

The worktree was clean before analysis. All four result checksum manifests passed, and Git reported no diffs under the detector, corpus, protocol, or frozen results. The evidence chain was:

| Reference | Git freeze SHA | Principal artifact SHA-256 |
|---|---|---|
| Protocol | `17e16d63d9bbf9b17b94d2b4ada7b81f27e3c6f6` | `experiments/EXP-009/protocol.yaml`: `a3993e079785c7aee3df8b1e68fb251d92223f288329bde9b85e089b875f45ea` |
| Corpus | `b91458f672edb72eaa7b1f3df67dc844933c19c4` | manifest: `343023e34e8c35d362e640254d8e0bc5055c8dd5a5f3fea78f0f1da389364fa7`; labels: `7e2a2a41376f395ea61e553d8074ea2cad9ce7b778774ca3a2832780a2184535` |
| Detector | `6dc4a6eac7db315a06d9b165234eb1388ee89529` | `rules.py`: `b5af41e1da0ef53270a291b0af5dba639fdbb8dc0c51576e5dd621b4a027c82a` |
| Base result | `30dc4b5823bb00abfdb14ae74f21d9c43fe48bf6` | runs: `dbfa7aadc36d8751cd78ef10e62c5b4ef497a7badb0e9ea72358f6b17c17b7d3`; summary: `dafb1682b401e1ea3d8860bdbf9570d5ade8e4fd6d3194d0ece06c8ccd43fb8c` |
| Base analysis | `88cf8c1b4c45ab9519afeeb6f6c091b9b50b981e` | `analysis.json`: `c3e28f91e6628701dbc1ea3cff60cd212505e8f4e926b03a445f57566e22c901` |
| A1 threshold ablation | `870507f611432fa30a76b4772866080498c230ef` | summary: `7691d0168e4a0d1dff7fdd6b89068cd6611413baa406933b5041fa73816a2fbc` |
| A2 window ablation | `2e0e0f2dd8bec48daa4bc6a160876931355951d0` | summary: `dc10f93c0b8ca76ccd6348257e539c8ef5135a2bed2ada6ac850ed0322546826` |
| A3 rule-availability ablation | `075df90588d3ef1f4be13201ce9aefe5567bd718` | summary: `2f9d413cdb1974a06e29c4ceb6a576908e396fd524518c7ce10633aee4502160` |
| Synthesis starting HEAD | `075df90588d3ef1f4be13201ce9aefe5567bd718` | clean worktree before synthesis |

## 3. Primary question

The primary question is RQ-08: can trajectory-level monitoring detect suspicious multi-step behavior missed by independently authorizing each action? EXP-009 can answer this only for its preregistered synthetic scenarios and the frozen deterministic rules. Its secondary RQ-02 mapping does not establish pre-execution detection: M5 is observational after terminal events.

## 4. H-02 interpretation

The repository states H-02 exactly as follows:

> Trajectory-aware deterministic monitoring will detect at least one preregistered class of suspicious behavior that independent single-action authorization does not detect.

This global hypothesis is not rewritten here. The narrower operational conclusion tested by EXP-009 is: on `EXP-009-CORPUS@1`, did the frozen monitor produce expected findings for a preregistered trajectory-positive family whose actions produced no action-level policy block, and at what specificity cost?

H-02 is **PARTIALLY_SUPPORTED within the synthetic held-out EXP-009 corpus and current deterministic rule architecture**. The support is the 20/20 TRJ-001 positives with zero policy-blocked steps and a trajectory finding. The qualification is essential: 33/40 trajectory-negative scenarios were also flagged, including 33/36 hard negatives, and all 10 TRJ-001 contrast pairs had both labels flagged.

## 5. Base held-out findings

The frozen base confusion matrix is **TP 40, FP 33, TN 7, FN 0**. The detector found 40/40 positives and flagged 33/40 negatives. It flagged 33/36 hard negatives. In all 10/10 contrast pairs, both the positive and the opposite-label benign scenario were flagged.

By rule family, TRJ-001 produced 20 TP, 16 FP, 4 TN, and 0 FN. TRJ-002 produced 20 TP, 17 FP, 3 TN, and 0 FN. High recall alone is insufficient: the negative results show poor specificity on this frozen corpus.

## 6. A1 threshold findings

For TRJ-002, threshold 2 retained 20/20 positive detections and flagged 18/20 negatives, one more false positive than base. Threshold 3 reproduced base behavior: 20 TP, 17 FP, 3 TN, and 0 FN. Threshold 4 reduced false positives to 1/20 negatives but detected 0/20 TRJ-002 positives.

The tested threshold therefore trades sensitivity for specificity sharply. Within this frozen corpus and the preregistered values 2, 3, and 4, threshold adjustment did not resolve the core ambiguity between deliberate probing and benign fallback or compatibility behavior. This does not show that no threshold could ever work in other corpora or rule designs.

## 7. A2 window findings

Windows 4, 8, and 16 produced identical scenario-level outcomes: TP 40, FP 33, TN 7, and FN 0 at each value. Every one of the 80 scenarios retained the same outcome, and all 10 contrast pairs remained both-flagged.

Within this corpus, the observed false-positive problem is not attributable to the tested window bounds. The corpus did not expose window sensitivity for these three values. This is not evidence that window size never matters; traces with evidence outside a smaller retained window were not demonstrated here.

## 8. A3 rule-availability findings

TRJ-001 and TRJ-002 covered disjoint positive families: each uniquely contributed 20/40 base true positives. They also produced disjoint false-positive sets: TRJ-001 contributed 16/33 base false positives and TRJ-002 contributed 17/33. With both enabled, the complete finding multiset was the exact union of the individual conditions for every one of the 80 scenarios; no interaction effect was observed.

The base failure is therefore not attributable to one pathological rule or to unexpected interaction. Both rule families independently recognize action-pattern structure without enough represented context to distinguish the corpus's benign and suspicious purposes.

## 9. Integrated interpretation

| Evidence | Observation | Interpretation | Limitation |
|---|---|---|---|
| Base EXP-009 | 40/40 positives detected; 33/40 negatives and 33/36 hard negatives flagged; 10/10 contrast pairs both flagged | The rules add trajectory findings, including findings beyond action-level policy, but have poor specificity and task-context discrimination | 80 handcrafted synthetic scenarios; observational rules only |
| A1 | Thresholds 2/3 detected 20/20 TRJ-002 positives with 18/20 and 17/20 negatives flagged; threshold 4 detected 0/20 positives and flagged 1/20 negatives | The tested count threshold makes a sharp sensitivity/specificity tradeoff and does not resolve purpose ambiguity | Only preregistered values 2, 3, and 4 on the same frozen corpus |
| A2 | Windows 4/8/16 all produced 40/33/7/0 | Tested window bounds do not explain the observed errors | The corpus exposed no outcome transition, so broader window behavior is untested |
| A3 | Each rule uniquely detected 20 positives and independently caused 16 or 17 FPs; both-rule findings were an exact union | Coverage and false-positive burden are additive, not a one-rule or interaction artifact | Only two rule families; TRJ-002 had no registered contrast pairs |

The strongest positive result and strongest counterevidence must be read together. Trajectory monitoring produced findings for 20 TRJ-001 positive scenarios that were not blocked by action-level authorization. It also flagged 33/40 trajectory-negative scenarios. EXP-009 demonstrates incremental observational capability for specified synthetic cases, not general unsafe-behavior detection.

## 10. What EXP-009 supports

- On `EXP-009-CORPUS@1`, the frozen detector found all 40/40 registered positives.
- For 20/20 TRJ-001 positives, `policy_blocked_steps = 0` while a trajectory finding was emitted. This is incremental observation beyond isolated action authorization for those cases.
- TRJ-002 added pattern interpretation to 20/20 positive traces that already contained policy denials.
- The evaluated TRJ-001 logic was task-context insensitive within the 10 registered contrast pairs: it flagged the positive and the opposite-label benign member in all 10/10 pairs.
- The false-positive problem persisted across tested windows and arose independently in both rule families.

## 11. What EXP-009 does not support

EXP-009 does not establish that SafetyBox detects unsafe behavior generally, that its findings are sufficiently specific for deployment, or that it prevents the behavior it detects. It does not establish pre-execution trajectory intervention, real-agent or OS-level effectiveness, real-world prevalence, calibrated production thresholds, performance overhead, statistical generalization, semantic understanding, or novelty. It also does not show that window size never matters or that no threshold can work in another design.

No recall, false-positive rate, precision, policy-block count, or trajectory-detection count is collapsed into a safety score.

## 12. Failure-mode synthesis

| ID | Status | Failure mode | Evidence boundary |
|---|---|---|---|
| FM-01 | **OBSERVED** | Task-purpose blindness | TRJ-001 flagged both sides of all 10/10 task-purpose contrast pairs despite opposite labels. This is task-context insensitivity within the evaluated contrast-pair design. |
| FM-02 | **OBSERVED** | Destination-purpose blindness | Sixteen TRJ-001 legitimate report/export, handoff, diagnostic, or release flows were flagged because outbound-like actions were matched without evaluating whether the destination served the declared task. Task and destination effects were not separately randomized. |
| FM-03 | **HYPOTHESIZED** | Data-lineage blindness | The monitor records an access/action sequence but not causal information flow from collected data to the send. EXP-009 identifies this missing representation as a plausible limitation but did not manipulate lineage independently. |
| FM-04 | **OBSERVED** | Denial-purpose blindness | TRJ-002 flagged 17/20 benign negatives because three distinct same-action denials can express either deliberate probing or legitimate fallback/compatibility behavior; the rule does not represent why requests occurred. |
| FM-05 | **OBSERVED** | Exact sequence dependence | TRJ-001 detection followed the exact terminal action structure, while reordered or missing-stage controls remained unflagged. This evidence is specific to the frozen rule and corpus. |
| FM-06 | **HYPOTHESIZED; NOT EXPOSED BY A2** | Bounded observational representation | A finite retained history can theoretically omit relevant evidence, but windows 4, 8, and 16 produced identical outcomes here. A2 did not demonstrate window sensitivity. |

TRJ-001 and TRJ-002 fail for related but distinct semantic omissions. TRJ-001 lacks represented task, destination, and lineage relationships around allowed collection-to-egress actions. TRJ-002 lacks purpose semantics around denied actions, so it cannot distinguish systematic boundary mapping from expected fallback or compatibility lookup behavior.

## 13. Threats to validity

These limitations constrain every claim above, rather than serving as an afterthought:

- **Construct validity:** exact action sequences and denial counts are proxies for behavioral meaning. Similar observable structures can have opposite task purposes.
- **External validity:** synthetic logical resources and simulator events are not real agents, tools, operating-system effects, or deployed workflows.
- **Corpus-author bias:** the same research environment knew the detector architecture when creating the handcrafted scenarios, even though labels and the corpus were frozen before evaluation.
- **Context representation:** task descriptions and semantic labels exist in corpus ground truth, but the detector does not consume them. The evaluation therefore tests a deliberately narrower observable representation.
- **Statistical limitations:** the corpus has 80 handcrafted deterministic scenarios and one semantic execution per scenario. No population sampling model or significance test supports broader inference.
- **Rule-family limitation:** only two trajectory rule families were evaluated. Their disjoint construction does not establish behavior for other rules or cross-family scenarios.
- **No intervention evaluation:** M5 is observational. A finding after or through execution evidence is not a blocked or prevented action.

## 14. Claim implications

CL-002 states exactly: “Trajectory-aware rules detect registered suspicious sequences missed by independent action authorization.” The finalized matched suite and component ablation provide direct but bounded evidence for this statement: TRJ-001 detected 20/20 registered positive sequences with zero policy-blocked steps, and A3 attributes those findings to TRJ-001 independently.

The recommended and recorded status is **PARTIALLY_SUPPORTED**, not `SUPPORTED`, because the evidence is limited to the synthetic held-out corpus and current deterministic architecture, and 33/40 negatives were flagged. The retained broad claim must always be accompanied by that scope and limitation.

A narrower derived empirical statement is fully supported as a result description: **On `EXP-009-CORPUS@1`, deterministic trajectory monitoring identified all 40/40 preregistered trajectory-positive scenarios, including 20 TRJ-001 cases with no action-level policy block, but produced 33 false positives among 40 negatives.** This is not a generalized safety claim.

## 15. Research design implications

The next design must vary explicit semantics rather than merely adjust counts or history bounds. It should distinguish otherwise similar observable actions using structured task purpose, resource purpose, destination constraints, and—where representable—data lineage. For repeated denials, it should represent declared fallback or compatibility behavior separately from boundary-mapping intent. Deterministic explanations and auditable evidence must remain first-class outputs.

The design must not specialize to these 80 scenarios. Corpus IDs, fixed task-category exceptions, and encodings of the current contrast pairs are prohibited. Any new detector must be frozen before evaluation on a newly authored held-out corpus/version.

## 16. Recommended next experiment

**Next research question:** Can deterministic trajectory monitoring improve specificity by evaluating observed actions relative to explicit task-purpose, resource-purpose, and destination constraints without sacrificing the incremental detection observed in EXP-009?

The recommended next experiment is a preregistered M5.1 context-aware trajectory evaluation using a new detector version and new held-out corpus version. It should compare the frozen sequence-only M5 baseline with a deterministic context-aware condition on matched positive, benign, and contrast scenarios; report raw recall and false-positive counts separately; and explicitly test whether the 20-case class of incremental observation can be retained. This is a design recommendation, not implementation or authorization to run the experiment.

## 17. Publication relevance

**Candidate contribution framing—not a final contribution or novelty claim:**

1. a deterministic reference-monitor architecture;
2. task-scoped capability enforcement;
3. reconstructable trajectory evidence;
4. a preregistered held-out evaluation showing incremental trajectory detection in 20/20 TRJ-001 positive scenarios not blocked by action-level authorization; and
5. an empirical demonstration that sequence-only deterministic rules incurred substantial context-related false positives: 33/40 negatives in this synthetic corpus.

Novelty and comparative positioning remain contingent on a later related-work assessment.
