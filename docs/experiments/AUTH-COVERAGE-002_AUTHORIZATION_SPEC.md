# AUTH-COVERAGE-002 normative authorization specification

**Identity:** `AUTH-COVERAGE-002-AUTHORIZATION-SPEC@1`  
**Status:** frozen before canonical corpus generation

## Domain

A **Subject** is an audit actor string and grants no authority. A **Task** is an opaque,
case-sensitive task string. An **Action** is an exact, case-sensitive operation string. A
**Resource** is either an exact nonempty logical identifier or a canonical absolute path:
it begins with `/`, is not `/`, and contains no empty, `.` or `..` segment. A
**Capability** is one indivisible `(action, scope)` value. A **TaskContract** is a task,
description, and mathematical set of capabilities. A **ToolClass** is `FILESYSTEM` or
`PROCESS`. A **CompoundRequirement** is an ordered nonempty set of uniquely named atomic
components. A **Decision** is `ALLOW` or `DENY`.

Filesystem requests have exactly one primary component. Process requests have two ordered
components: primary `exec` and additional `cwd`. Every component carries the same request
task, subject/session provenance, and arbitrary non-authoritative arguments/context.

## Matching

`TaskMatch := request.task == contract.task`.

`ActionMatch(c, x) := c.action == x.action`.

An exact capability scope matches only a code-point-identical resource. A path scope
`P/**` is valid only when `P` is a canonical absolute path; it matches canonical strict
descendants beginning `P/`, but not `P`, a prefix lookalike, any noncanonical path, or a
Unicode/case variant. There is no Unicode normalization, case folding, filesystem I/O,
symlink, hard-link, mount, existence, or executable lookup.

`Applicable(c, x) := ActionMatch(c, x) AND ResourceMatch(c.scope, x.resource)`.

`AuthorizeComponent(x) := ALLOW` iff the complete structure is valid, `TaskMatch`, and at
least one single capability is applicable. The action half of one capability and resource
half of another never compose. Extra irrelevant capabilities do nothing. An empty set
denies. Duplicate capability values collapse to one and do not alter authorization.

`AuthorizeCompound := ALLOW` iff every required component allows. Separate applicable
capabilities may cover separate components. The compound quadrants are AA→ALLOW and
AD/DA/DD→DENY. If multiple values cover a component, the lexicographically smallest
`(resource, action)` is selected only for deterministic explanation; selection does not
create authority.

Invalid request/contract/component shapes, empty authority-bearing strings, invalid path
scopes, repeated component names, or unsupported tools fail closed under the separate
`INVALID_STRUCTURE_CONTROL` family. They are excluded from primary valid-input accuracy.

## Non-authority

Scenario/request/contract identifiers, actor, session, description, argv, arbitrary
metadata, apparent suspiciousness or innocence, AI/context fixtures, family, difficulty,
tool name alone, capability count, and generation provenance cannot grant or revoke
authority. Contract identity is provenance only. Physical existence is irrelevant.

## Required explanation relation

For each component the normative record contains decision, rule, reason code, task,
action, resource, matched capability or null, and authority source. Rules are
`AUTH.INVALID_STRUCTURE`, `AUTH.TASK_MISMATCH`, `AUTH.NO_ACTION_CAPABILITY`,
`AUTH.RESOURCE_OUT_OF_SCOPE`, and `AUTH.EXPLICIT_CAPABILITY`. Top-level rules are
`AUTH.ALL_COMPONENTS_ALLOWED` and `AUTH.ANY_COMPONENT_DENIED`.

## Invariants

The relation is deterministic, task-isolated, exact-action-bound, exact/scope-resource-
bound, non-synthesizing, conjunctive for compounds, invariant to irrelevant capability
addition and order, invariant to opaque IDs and non-authoritative context, and fail-closed
for invalid structures.
