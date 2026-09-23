# Baselines

No baseline performance has been measured or claimed.

| ID | Baseline | Purpose and boundary |
|---|---|---|
| B0 | No safety layer | Agent requests go to the controlled test tool without SafetyBox decisions; environmental sandbox remains to protect researchers. |
| B1 | Static allow/deny list | Tool/action list without task-resource constraints, trajectory state, or semantic judge. |
| B2 | SafetyBox deterministic enforcement | Proposed task contract, scoped capabilities, deterministic policies, and stateful controls as enabled by condition. |
| B3 | LLM-only safety monitor | Optional future judge deciding from a defined request/context prompt; does not represent the deterministic core and is not implemented in M0. |
| B4 | Deterministic + LLM hybrid | B2 retains hard authority boundaries; an LLM supplies only a defined auxiliary semantic signal. |

## Comparison requirements

- Use identical task/scenario inputs and tool environment where possible.
- Define which context each baseline receives and account for unequal observability.
- Hold model/provider settings fixed or model them as factors.
- Include monitor failures, timeouts, abstentions, retries, and unavailable decisions.
- Measure actual prevented execution separately from classifications.
- Record B3/B4 prompt/version, tokens, latency, price basis, and output parsing.
- Do not allow B3 or B4 to silently receive outcome labels unavailable at decision time.

B0 must run only in an isolated simulator or sandbox; “no safety layer” is an experimental comparator, not authorization for real harmful effects.
