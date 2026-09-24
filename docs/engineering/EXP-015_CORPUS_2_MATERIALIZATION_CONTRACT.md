# EXP-015 Corpus@2 Materialization Contract

`materialize(runtime_scenario, temp_root) -> MaterializedScenario` validates then
creates all declared objects below a fresh root. It returns a request-shaped public DTO,
task contract DTO, host paths, route, fault configuration, observations, and parent
environment. It does not execute a child or an adapter. The future generic executor owns
the final DTO-to-public-`ProcessRequest` conversion.

The materializer imports only the standard library and corpus-side schema types. It must
never import the process package, adapter/private validators/canonicalizers, labels,
scoring, pair registry, or outcomes. This deliberately avoids the current public process
package import side effect of loading `ProcessAdapter`.

Future flow is: runtime scenario → materializer → `MaterializedScenario` → generic
executor → persisted raw record → separately loaded scoring data. ADAPTER invokes the
frozen adapter normally; DIRECT_CONTROL runs only its explicitly declared safe control.
No branch may use an ID, label, family, pair, or manifest count.

Raw records are label-free and include identity/request, lexical canonical resources,
both authorization components and compound decision, validation state, spawn and
primitive counts, child state, output metadata, exit/signal/timeout, audit events,
fault observation, marker/environment observations, and timings.

The label-isolation guard is a separate execution process: it starts with no scoring
module loaded, persists the raw record atomically, exits, then a scoring process opens
labels and the pair registry. The executor also asserts that no module whose name starts
`safetybox.experiments.exp015_corpus2_scoring` is loaded before persistence. This is a
deterministic in-process backstop, not protection against a malicious interpreter; OS
permissions and separate-process launch provide the stronger boundary.

The normalized state description records relative object path, lstat object type/mode,
symlink target or regular recipe text, cwd state, route, fault data, parent environment
key names, and observation channels. It omits root paths and IDs. Each future scenario
must materialize twice into fresh roots with equal normalized state, schema validity,
no label imports, and no hidden dispatch before corpus freeze.

The future independent authority oracle receives only contract, request task, exec
action/resource, and cwd action/resource and implements frozen lexical capability
semantics without `ProcessAdapter`, production compound authorization, or
`TaskContractPolicy`. A separate lexical canonicalization oracle independently normalizes
absolute executable/cwd paths without production canonicalization imports. Static
separability must test authorization labels against ID/task naming, names, argv length,
capability count, path depth, fixture type, timeout, and helper behavior. Semantic
conformance (validation/fault behavior) is reported separately from authorization
discrimination.
