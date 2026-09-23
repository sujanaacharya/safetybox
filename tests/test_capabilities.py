"""Unit tests for M2's deliberately narrow resource matcher."""

from __future__ import annotations

import pytest

from safetybox import resource_matches


@pytest.mark.parametrize(
    "resource",
    ["/workspace/project/a.txt", "/workspace/project/src/a.py"],
)
def test_path_subtree_scope_allows_nested_canonical_paths(resource: str) -> None:
    assert resource_matches("/workspace/project/**", resource) is True


@pytest.mark.parametrize(
    "resource",
    [
        "/workspace/project",
        "/workspace/project-secret/a.txt",
        "/workspace/projects/a.txt",
        "/workspace/projec/a.txt",
    ],
)
def test_path_subtree_scope_rejects_root_and_boundary_confusion(resource: str) -> None:
    assert resource_matches("/workspace/project/**", resource) is False


def test_logical_resources_require_exact_match() -> None:
    assert resource_matches("db:analytics", "db:analytics") is True
    assert resource_matches("db:analytics", "db:analytics-archive") is False
