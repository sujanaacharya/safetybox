"""Focused tests for the intentionally small M1 static policy."""

from __future__ import annotations

from safetybox import ActionRequest, Decision, StaticPolicy


def test_static_policy_allows_only_explicit_action_resource_pair() -> None:
    policy = StaticPolicy({("document.read", "report.txt")})
    allowed = ActionRequest("1", "s", "t", "a", "document.read", "report.txt")
    different_resource = ActionRequest("2", "s", "t", "a", "document.read", "other.txt")

    assert policy.authorize(allowed).decision is Decision.ALLOW
    assert policy.authorize(different_resource).decision is Decision.DENY
