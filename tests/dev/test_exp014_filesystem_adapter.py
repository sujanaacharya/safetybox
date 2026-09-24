"""Contaminated development validation for FS-ADAPTER@1 (not held-out evidence)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from safetybox import Capability, Decision, TaskContract, TaskContractPolicy
from safetybox.audit import AuditRecorder, InMemoryAuditSink
from safetybox.events import EventType, SafetyBoxEvent
from safetybox.filesystem import (
    FILESYSTEM_ADAPTER_VERSION,
    FILESYSTEM_AUDIT_ENVELOPE_VERSION,
    FILESYSTEM_CANONICALIZATION_VERSION,
    STATE_DIGEST_VERSION,
    FilesystemAdapter,
    FilesystemOperation,
    FilesystemRequest,
    FilesystemResultCategory,
    LogicalHostMapper,
    PhysicalValidationStatus,
    RealFilesystemPrimitives,
    canonicalize_logical_path,
    digest_manifest,
)
from safetybox.filesystem.errors import CanonicalizationError, FilesystemPrimitiveError
from safetybox.filesystem.models import FilesystemStat
from safetybox.models import ActionRequest, PolicyDecision


@pytest.fixture
def isolated_root() -> Iterator[Path]:
    with TemporaryDirectory(prefix="safetybox-dev-fs-") as directory:
        root = Path(directory)
        workspace = root / "workspace"
        (workspace / "public").mkdir(parents=True)
        (workspace / "private").mkdir()
        (workspace / "output").mkdir()
        yield root


@dataclass
class SpyPrimitives(RealFilesystemPrimitives):
    probes: list[str] = field(default_factory=list)
    requested: list[str] = field(default_factory=list)
    operation_observations: list[tuple[str, ...]] = field(default_factory=list)
    sink: InMemoryAuditSink | None = None

    def lstat(self, path: Path) -> os.stat_result:
        self.probes.append("lstat")
        return super().lstat(path)

    def directory_is_empty(self, path: Path) -> bool:
        self.probes.append("directory_is_empty")
        return super().directory_is_empty(path)

    def _record(self, name: str) -> None:
        self.requested.append(name)
        if self.sink is not None:
            self.operation_observations.append(
                tuple(event.event_type.value for event in self.sink.events())
            )

    def read(self, path: Path) -> bytes:
        self._record("read")
        return super().read(path)

    def write(self, path: Path, data: bytes) -> None:
        self._record("write")
        super().write(path, data)

    def append(self, path: Path, data: bytes) -> None:
        self._record("append")
        super().append(path, data)

    def create(self, path: Path, data: bytes) -> None:
        self._record("create")
        super().create(path, data)

    def delete_file(self, path: Path) -> None:
        self._record("delete_file")
        super().delete_file(path)

    def delete_directory(self, path: Path) -> None:
        self._record("delete_directory")
        super().delete_directory(path)

    def rename(self, source: Path, destination: Path) -> None:
        self._record("rename")
        super().rename(source, destination)

    def mkdir(self, path: Path) -> None:
        self._record("mkdir")
        super().mkdir(path)

    def list_directory(self, path: Path) -> tuple[str, ...]:
        self._record("list")
        return super().list_directory(path)

    def minimized_stat(self, path: Path) -> FilesystemStat:
        self._record("stat")
        return super().minimized_stat(path)


def request(
    operation: FilesystemOperation,
    resource: str,
    *,
    destination: str | None = None,
    data: bytes | None = None,
    request_id: str = "DEV-FS-REQUEST-001",
    session_id: str = "dev-session-a",
    task_id: str = "dev-task-a",
) -> FilesystemRequest:
    return FilesystemRequest(
        session_id,
        task_id,
        request_id,
        "development-agent",
        operation,
        resource,
        destination,
        data,
    )


def adapter_for(
    root: Path,
    capabilities: list[Capability],
    *,
    primitives: RealFilesystemPrimitives | None = None,
    sink: InMemoryAuditSink | None = None,
    authorizer: object | None = None,
) -> tuple[FilesystemAdapter, InMemoryAuditSink]:
    selected_sink = InMemoryAuditSink() if sink is None else sink
    policy = (
        TaskContractPolicy(TaskContract("dev-task-a", "development only", capabilities))
        if authorizer is None
        else authorizer
    )
    return (
        FilesystemAdapter(
            mapper=LogicalHostMapper(root),
            authorizer=policy,  # type: ignore[arg-type]
            policy_reference="DEV-FS-POLICY@1",
            audit_recorder=AuditRecorder(selected_sink),
            primitives=primitives,
        ),
        selected_sink,
    )


def event_types(sink: InMemoryAuditSink) -> list[EventType]:
    return [event.event_type for event in sink.events()]


def test_versions_are_explicit_and_stable() -> None:
    assert FILESYSTEM_ADAPTER_VERSION == "FS-ADAPTER@1"
    assert FILESYSTEM_CANONICALIZATION_VERSION == "FS-CANONICALIZATION@1"
    assert FILESYSTEM_AUDIT_ENVELOPE_VERSION == "FS-AUDIT-ENVELOPE@1"
    assert STATE_DIGEST_VERSION == "EXP014-STATE-DIGEST@1"


@pytest.mark.parametrize(
    ("fixture_id", "raw", "expected"),
    [
        ("DEV-FS-LEXICAL-001", "public/a.txt", "/workspace/public/a.txt"),
        ("DEV-FS-LEXICAL-002", "/workspace/public/a.txt", "/workspace/public/a.txt"),
        ("DEV-FS-LEXICAL-003", "/workspace/public/./a.txt", "/workspace/public/a.txt"),
        ("DEV-FS-LEXICAL-004", "/workspace/public/x/../a.txt", "/workspace/public/a.txt"),
        ("DEV-FS-LEXICAL-005", "/workspace//public///a.txt", "/workspace/public/a.txt"),
        ("DEV-FS-LEXICAL-006", "/workspace/public/", "/workspace/public"),
        ("DEV-FS-LEXICAL-007", "public/e\u0301.txt", "/workspace/public/é.txt"),
        ("DEV-FS-LEXICAL-008", "/workspace", "/workspace"),
        ("DEV-FS-LEXICAL-009", "public/x/../../output/a", "/workspace/output/a"),
    ],
)
def test_pure_lexical_canonicalization(fixture_id: str, raw: str, expected: str) -> None:
    assert fixture_id.startswith("DEV-FS-LEXICAL-")
    assert canonicalize_logical_path(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "..",
        "../private/a",
        "../../etc/passwd",
        "public/../../../etc/passwd",
        "/etc/passwd",
        "/workspace2/private/a",
        "/workspace/../../private/a",
        "public/\x00secret",
    ],
)
def test_lexical_rejections_do_not_depend_on_host_state(raw: str) -> None:
    with pytest.raises(CanonicalizationError):
        canonicalize_logical_path(raw)


def test_bytes_paths_are_rejected_by_the_canonicalizer() -> None:
    with pytest.raises(CanonicalizationError, match="Unicode"):
        canonicalize_logical_path(b"public/a")  # type: ignore[arg-type]


def test_request_models_enforce_operation_specific_arguments() -> None:
    with pytest.raises(TypeError):
        request(FilesystemOperation.WRITE, "public/a")
    with pytest.raises(TypeError):
        request(FilesystemOperation.RENAME, "public/a")
    with pytest.raises(ValueError):
        request(FilesystemOperation.READ, "public/a", data=b"unexpected")


def test_mapper_rejects_ambiguous_configuration_and_noncanonical_resources(
    isolated_root: Path,
) -> None:
    with pytest.raises(ValueError, match="absolute"):
        LogicalHostMapper(Path("relative-root"))
    with pytest.raises(ValueError, match="parent traversal"):
        LogicalHostMapper(Path("/tmp/config/../escape"))
    mapper = LogicalHostMapper(isolated_root)
    for hostile in (
        "/other/resource",
        "/workspace/public/../private/secret",
        "/workspace//public/file",
        "/workspace/public/./file",
        "/workspace/../../etc/passwd",
        "/workspace/public/e\u0301.txt",
    ):
        with pytest.raises(ValueError, match="canonical"):
            mapper.to_host(hostile)


def test_adapter_requires_explicit_policy_reference(isolated_root: Path) -> None:
    with pytest.raises(ValueError, match="policy_reference"):
        FilesystemAdapter(
            mapper=LogicalHostMapper(isolated_root),
            authorizer=TaskContractPolicy(TaskContract("dev-task-a", "development")),
            policy_reference="",
        )


def test_real_successful_operations_and_audit_lifecycle(isolated_root: Path) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "read.bin").write_bytes(b"read-value")
    (public / "write.bin").write_bytes(b"old")
    (public / "append.bin").write_bytes(b"a")
    (public / "delete.bin").write_bytes(b"delete")
    (public / "empty-dir").mkdir()
    (public / "rename.bin").write_bytes(b"rename")
    (public / "z-name").write_bytes(b"")
    (public / "é-name").write_bytes(b"")
    (public / "CaseName").write_bytes(b"")
    operations = list(FilesystemOperation)
    capabilities = [Capability(operation.value, "/workspace/public/**") for operation in operations]
    capabilities.append(Capability("filesystem.list", "/workspace/public"))
    spy = SpyPrimitives()
    adapter, sink = adapter_for(isolated_root, capabilities, primitives=spy)
    spy.sink = sink

    outcomes = [
        adapter.execute(
            request(FilesystemOperation.READ, "public/read.bin", request_id="DEV-FS-OP-READ")
        ),
        adapter.execute(
            request(
                FilesystemOperation.WRITE,
                "public/write.bin",
                data=b"new",
                request_id="DEV-FS-OP-WRITE",
            )
        ),
        adapter.execute(
            request(
                FilesystemOperation.APPEND,
                "public/append.bin",
                data=b"b",
                request_id="DEV-FS-OP-APPEND",
            )
        ),
        adapter.execute(
            request(
                FilesystemOperation.CREATE,
                "public/created.bin",
                data=b"created",
                request_id="DEV-FS-OP-CREATE",
            )
        ),
        adapter.execute(
            request(
                FilesystemOperation.DELETE, "public/delete.bin", request_id="DEV-FS-OP-DELETE-FILE"
            )
        ),
        adapter.execute(
            request(
                FilesystemOperation.DELETE, "public/empty-dir", request_id="DEV-FS-OP-DELETE-DIR"
            )
        ),
        adapter.execute(
            request(
                FilesystemOperation.RENAME,
                "public/rename.bin",
                destination="public/renamed.bin",
                request_id="DEV-FS-OP-RENAME",
            )
        ),
        adapter.execute(
            request(FilesystemOperation.MKDIR, "public/made-dir", request_id="DEV-FS-OP-MKDIR")
        ),
        adapter.execute(request(FilesystemOperation.LIST, "public", request_id="DEV-FS-OP-LIST")),
        adapter.execute(
            request(FilesystemOperation.STAT, "public/read.bin", request_id="DEV-FS-OP-STAT")
        ),
    ]
    outcome_operations = (
        FilesystemOperation.READ,
        FilesystemOperation.WRITE,
        FilesystemOperation.APPEND,
        FilesystemOperation.CREATE,
        FilesystemOperation.DELETE,
        FilesystemOperation.DELETE,
        FilesystemOperation.RENAME,
        FilesystemOperation.MKDIR,
        FilesystemOperation.LIST,
        FilesystemOperation.STAT,
    )

    assert all(outcome.succeeded for outcome in outcomes)
    assert outcomes[0].value == b"read-value"
    assert (public / "write.bin").read_bytes() == b"new"
    assert (public / "append.bin").read_bytes() == b"ab"
    assert (public / "created.bin").read_bytes() == b"created"
    assert not (public / "delete.bin").exists()
    assert not (public / "empty-dir").exists()
    assert not (public / "rename.bin").exists()
    assert (public / "renamed.bin").read_bytes() == b"rename"
    assert (public / "made-dir").is_dir()
    assert isinstance(outcomes[-1].value, FilesystemStat)
    names = outcomes[-2].value
    assert isinstance(names, tuple)
    assert names == tuple(sorted(names))
    assert "CaseName" in names
    assert "é-name" in names
    assert spy.requested == [
        "read",
        "write",
        "append",
        "create",
        "delete_file",
        "delete_directory",
        "rename",
        "mkdir",
        "list",
        "stat",
    ]
    for observation in spy.operation_observations:
        assert EventType.AUTHORIZATION_ALLOWED.value in observation
        assert EventType.TARGET_VALIDATION_SUCCEEDED.value in observation
        assert observation[-1] == EventType.EXECUTION_STARTED.value
    mutating = {
        FilesystemOperation.WRITE,
        FilesystemOperation.APPEND,
        FilesystemOperation.CREATE,
        FilesystemOperation.DELETE,
        FilesystemOperation.RENAME,
        FilesystemOperation.MKDIR,
    }
    for operation, outcome in zip(outcome_operations, outcomes, strict=True):
        evidence = outcome.evidence
        request_events = [
            event for event in sink.events() if event.request_id == outcome.request_id
        ]
        assert evidence.adapter_version == FILESYSTEM_ADAPTER_VERSION
        assert evidence.envelope_version == FILESYSTEM_AUDIT_ENVELOPE_VERSION
        assert evidence.canonicalization_version == FILESYSTEM_CANONICALIZATION_VERSION
        assert evidence.state_digest_version == STATE_DIGEST_VERSION
        assert evidence.session_id == "dev-session-a"
        assert evidence.task_id == "dev-task-a"
        assert evidence.request_id == evidence.correlation_id == outcome.request_id
        assert evidence.action == operation.value
        assert evidence.requested_resource
        assert evidence.canonical_resource
        assert evidence.arguments_digest
        assert evidence.policy_reference == "DEV-FS-POLICY@1"
        assert len(evidence.authorizations) == (2 if operation is FilesystemOperation.RENAME else 1)
        assert all(item.decision is Decision.ALLOW for item in evidence.authorizations)
        assert all(item.rule_id for item in evidence.authorizations)
        assert evidence.physical_validation is PhysicalValidationStatus.SUCCEEDED
        assert evidence.execution_attempted is True
        assert evidence.execution_succeeded is True
        assert evidence.result_category is FilesystemResultCategory.ALLOW
        assert evidence.error_code is None
        assert evidence.sequence_numbers == tuple(event.sequence_number for event in request_events)
        assert all(
            event.parent_event_id == previous.event_id
            for previous, event in zip(request_events, request_events[1:], strict=False)
        )
        if operation in mutating:
            assert evidence.pre_state_digest is not None
            assert evidence.post_state_digest is not None
        else:
            assert evidence.pre_state_digest is None
            assert evidence.post_state_digest is None


@pytest.mark.parametrize(
    ("operation", "resource", "destination", "data"),
    [
        (FilesystemOperation.WRITE, "public/mutate.bin", None, b"changed"),
        (FilesystemOperation.APPEND, "public/mutate.bin", None, b"changed"),
        (FilesystemOperation.CREATE, "public/new.bin", None, b"new"),
        (FilesystemOperation.DELETE, "public/mutate.bin", None, None),
        (FilesystemOperation.RENAME, "public/mutate.bin", "public/moved.bin", None),
        (FilesystemOperation.MKDIR, "public/new-dir", None, None),
    ],
)
def test_denied_mutations_do_not_probe_invoke_or_change_state(
    isolated_root: Path,
    operation: FilesystemOperation,
    resource: str,
    destination: str | None,
    data: bytes | None,
) -> None:
    target = isolated_root / "workspace" / "public" / "mutate.bin"
    target.write_bytes(b"protected-original")
    mapper = LogicalHostMapper(isolated_root)
    scope = (
        "/workspace/public/mutate.bin",
        "/workspace/public",
        "/workspace/public/moved.bin",
        "/workspace/public/new.bin",
        "/workspace/public/new-dir",
    )
    before = digest_manifest(mapper, scope).digest
    spy = SpyPrimitives()
    adapter, sink = adapter_for(isolated_root, [], primitives=spy)

    result = adapter.execute(request(operation, resource, destination=destination, data=data))
    after = digest_manifest(mapper, scope).digest

    assert result.category is FilesystemResultCategory.DENY
    assert result.decision is Decision.DENY
    assert spy.probes == []
    assert spy.requested == []
    assert before == after
    assert EventType.EXECUTION_STARTED not in event_types(sink)
    assert EventType.TARGET_VALIDATION_STARTED not in event_types(sink)


@pytest.mark.parametrize(
    "operation", [FilesystemOperation.READ, FilesystemOperation.LIST, FilesystemOperation.STAT]
)
def test_denied_retrieval_discloses_no_protected_value(
    isolated_root: Path, operation: FilesystemOperation
) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "SENTINEL-NAME-9371").write_bytes(b"SENTINEL-BYTES-4826")
    resource = (
        "public/SENTINEL-NAME-9371" if operation is not FilesystemOperation.LIST else "public"
    )
    spy = SpyPrimitives()
    adapter, sink = adapter_for(isolated_root, [], primitives=spy)

    result = adapter.execute(request(operation, resource))
    rendered = repr((result, sink.events()))

    assert result.category is FilesystemResultCategory.DENY
    assert result.value is None
    assert spy.probes == []
    assert spy.requested == []
    assert "SENTINEL-BYTES-4826" not in rendered
    if operation is FilesystemOperation.LIST:
        assert "SENTINEL-NAME-9371" not in rendered


@pytest.mark.parametrize(
    "resource",
    ["public-report.txt", "publicity/x", "/workspace/public-report.txt", "/workspace/publicity/x"],
)
def test_component_prefix_collisions_are_denied_without_probe(
    isolated_root: Path, resource: str
) -> None:
    spy = SpyPrimitives()
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.read", "/workspace/public/**")],
        primitives=spy,
    )
    result = adapter.execute(request(FilesystemOperation.READ, resource))
    assert result.category is FilesystemResultCategory.DENY
    assert spy.probes == []
    assert spy.requested == []


@pytest.mark.parametrize(
    ("fixture_id", "link_builder"),
    [
        ("DEV-FS-SYMLINK-TERMINAL", "terminal-relative"),
        ("DEV-FS-SYMLINK-PARENT", "parent-relative"),
        ("DEV-FS-SYMLINK-ABSOLUTE", "terminal-absolute"),
        ("DEV-FS-SYMLINK-CHAIN", "chain"),
        ("DEV-FS-SYMLINK-DANGLING", "dangling"),
    ],
)
def test_symlink_categories_reject_after_allow_before_primitive(
    isolated_root: Path, fixture_id: str, link_builder: str
) -> None:
    public = isolated_root / "workspace" / "public"
    private = isolated_root / "workspace" / "private"
    (private / "secret.bin").write_bytes(b"secret")
    logical = "public/link.bin"
    if link_builder == "terminal-relative":
        (public / "link.bin").symlink_to("../private/secret.bin")
    elif link_builder == "parent-relative":
        (public / "linked-parent").symlink_to("../private", target_is_directory=True)
        logical = "public/linked-parent/secret.bin"
    elif link_builder == "terminal-absolute":
        (public / "link.bin").symlink_to(private / "secret.bin")
    elif link_builder == "chain":
        (public / "chain-a").symlink_to("chain-b")
        (public / "chain-b").symlink_to("../private/secret.bin")
        logical = "public/chain-a"
    else:
        (public / "link.bin").symlink_to("missing-target")
    spy = SpyPrimitives()
    adapter, sink = adapter_for(
        isolated_root,
        [Capability("filesystem.read", "/workspace/public/**")],
        primitives=spy,
    )

    result = adapter.execute(request(FilesystemOperation.READ, logical, request_id=fixture_id))

    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert result.decision is Decision.ALLOW
    assert result.error_code == "EXP014-TARGET-SYMLINK-REJECT"
    assert result.evidence.physical_validation is PhysicalValidationStatus.REJECTED
    assert spy.requested == []
    assert EventType.AUTHORIZATION_ALLOWED in event_types(sink)
    assert EventType.TARGET_VALIDATION_FAILED in event_types(sink)
    assert EventType.EXECUTION_STARTED not in event_types(sink)


def test_unauthorized_symlink_to_authorized_file_is_denied_without_probe(
    isolated_root: Path,
) -> None:
    public = isolated_root / "workspace" / "public"
    private = isolated_root / "workspace" / "private"
    (public / "allowed.bin").write_bytes(b"allowed")
    (private / "denied-link").symlink_to("../public/allowed.bin")
    spy = SpyPrimitives()
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.read", "/workspace/public/**")],
        primitives=spy,
    )
    result = adapter.execute(request(FilesystemOperation.READ, "private/denied-link"))
    assert result.category is FilesystemResultCategory.DENY
    assert spy.probes == []
    assert spy.requested == []


@pytest.mark.parametrize(
    "operation",
    [
        FilesystemOperation.READ,
        FilesystemOperation.WRITE,
        FilesystemOperation.APPEND,
        FilesystemOperation.DELETE,
        FilesystemOperation.STAT,
    ],
)
def test_multi_link_regular_files_reject_for_registered_operations(
    isolated_root: Path, operation: FilesystemOperation
) -> None:
    public = isolated_root / "workspace" / "public"
    target = public / "linked.bin"
    target.write_bytes(b"linked")
    try:
        os.link(target, public / "alias.bin")
    except OSError as error:
        pytest.skip(f"hard links unsupported by development filesystem: {error}")
    data = b"x" if operation in {FilesystemOperation.WRITE, FilesystemOperation.APPEND} else None
    spy = SpyPrimitives()
    adapter, _ = adapter_for(
        isolated_root,
        [Capability(operation.value, "/workspace/public/**")],
        primitives=spy,
    )
    result = adapter.execute(request(operation, "public/linked.bin", data=data))
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert result.error_code == "EXP014-TARGET-HARDLINK-REJECT"
    assert spy.requested == []


@pytest.mark.parametrize(
    ("source_allowed", "destination_allowed", "expected"),
    [
        (True, True, FilesystemResultCategory.ALLOW),
        (False, True, FilesystemResultCategory.DENY),
        (True, False, FilesystemResultCategory.DENY),
        (False, False, FilesystemResultCategory.DENY),
    ],
)
def test_rename_requires_two_recorded_decisions(
    isolated_root: Path,
    source_allowed: bool,
    destination_allowed: bool,
    expected: FilesystemResultCategory,
) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "source.bin").write_bytes(b"source")
    capabilities: list[Capability] = []
    if source_allowed:
        capabilities.append(Capability("filesystem.rename", "/workspace/public/source.bin"))
    if destination_allowed:
        capabilities.append(Capability("filesystem.rename", "/workspace/output/destination.bin"))
    spy = SpyPrimitives()
    adapter, sink = adapter_for(isolated_root, capabilities, primitives=spy)

    result = adapter.execute(
        request(
            FilesystemOperation.RENAME,
            "public/source.bin",
            destination="output/destination.bin",
        )
    )

    assert result.category is expected
    authorization_event = next(
        event
        for event in sink.events()
        if event.event_type in {EventType.AUTHORIZATION_ALLOWED, EventType.AUTHORIZATION_DENIED}
    )
    assert len(authorization_event.metadata["subdecisions"]) == 2  # type: ignore[arg-type]
    if expected is FilesystemResultCategory.ALLOW:
        assert spy.requested == ["rename"]
        assert not (public / "source.bin").exists()
    else:
        assert spy.probes == []
        assert spy.requested == []
        assert (public / "source.bin").read_bytes() == b"source"


def test_rename_destination_prefix_collision_denies_without_probe(isolated_root: Path) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "source.bin").write_bytes(b"source")
    spy = SpyPrimitives()
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.rename", "/workspace/public/**")],
        primitives=spy,
    )
    result = adapter.execute(
        request(
            FilesystemOperation.RENAME,
            "public/source.bin",
            destination="publicity/destination.bin",
        )
    )
    assert result.category is FilesystemResultCategory.DENY
    assert spy.probes == []
    assert spy.requested == []


def test_rename_source_symlink_and_destination_parent_symlink_reject(
    isolated_root: Path,
) -> None:
    public = isolated_root / "workspace" / "public"
    output = isolated_root / "workspace" / "output"
    (public / "real.bin").write_bytes(b"real")
    (public / "source-link").symlink_to("real.bin")
    (public / "destination-parent-link").symlink_to(output, target_is_directory=True)
    capabilities = [
        Capability("filesystem.rename", "/workspace/public/**"),
    ]
    spy = SpyPrimitives()
    adapter, _ = adapter_for(isolated_root, capabilities, primitives=spy)

    source_result = adapter.execute(
        request(
            FilesystemOperation.RENAME,
            "public/source-link",
            destination="public/destination.bin",
            request_id="DEV-FS-RENAME-SOURCE-SYMLINK",
        )
    )
    parent_result = adapter.execute(
        request(
            FilesystemOperation.RENAME,
            "public/real.bin",
            destination="public/destination-parent-link/destination.bin",
            request_id="DEV-FS-RENAME-PARENT-SYMLINK",
        )
    )

    assert source_result.error_code == "EXP014-TARGET-SYMLINK-REJECT"
    assert parent_result.error_code == "EXP014-TARGET-SYMLINK-REJECT"
    assert spy.requested == []
    assert (public / "real.bin").read_bytes() == b"real"


def test_rename_existing_hard_link_destination_rejects(isolated_root: Path) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "source.bin").write_bytes(b"source")
    (public / "destination.bin").write_bytes(b"destination")
    try:
        os.link(public / "destination.bin", public / "destination-alias.bin")
    except OSError as error:
        pytest.skip(f"hard links unsupported by development filesystem: {error}")
    spy = SpyPrimitives()
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.rename", "/workspace/public/**")],
        primitives=spy,
    )
    result = adapter.execute(
        request(
            FilesystemOperation.RENAME,
            "public/source.bin",
            destination="public/destination.bin",
            request_id="DEV-FS-RENAME-HARDLINK-DESTINATION",
        )
    )
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert result.error_code == "EXP014-TARGET-HARDLINK-REJECT"
    assert spy.requested == []
    assert (public / "source.bin").read_bytes() == b"source"


def test_rename_hard_link_source_rejects(isolated_root: Path) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "source.bin").write_bytes(b"source")
    try:
        os.link(public / "source.bin", public / "source-alias.bin")
    except OSError as error:
        pytest.skip(f"hard links unsupported by development filesystem: {error}")
    spy = SpyPrimitives()
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.rename", "/workspace/public/**")],
        primitives=spy,
    )
    result = adapter.execute(
        request(
            FilesystemOperation.RENAME,
            "public/source.bin",
            destination="public/destination.bin",
            request_id="DEV-FS-RENAME-HARDLINK-SOURCE",
        )
    )
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert result.error_code == "EXP014-TARGET-HARDLINK-REJECT"
    assert spy.requested == []


def test_rename_directory_semantics_are_bounded(isolated_root: Path) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "empty-source").mkdir()
    (public / "empty-destination").mkdir()
    (public / "nonempty-source").mkdir()
    (public / "nonempty-source" / "child").write_bytes(b"child")
    (public / "nonempty-destination").mkdir()
    (public / "nonempty-destination" / "child").write_bytes(b"child")
    (public / "file-destination").write_bytes(b"file")
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.rename", "/workspace/public/**")],
    )
    nonempty_source = adapter.execute(
        request(
            FilesystemOperation.RENAME,
            "public/nonempty-source",
            destination="public/new-directory",
            request_id="DEV-FS-RENAME-NONEMPTY-SOURCE",
        )
    )
    nonempty_destination = adapter.execute(
        request(
            FilesystemOperation.RENAME,
            "public/empty-source",
            destination="public/nonempty-destination",
            request_id="DEV-FS-RENAME-NONEMPTY-DESTINATION",
        )
    )
    incompatible = adapter.execute(
        request(
            FilesystemOperation.RENAME,
            "public/empty-source",
            destination="public/file-destination",
            request_id="DEV-FS-RENAME-INCOMPATIBLE",
        )
    )
    successful = adapter.execute(
        request(
            FilesystemOperation.RENAME,
            "public/empty-source",
            destination="public/empty-destination",
            request_id="DEV-FS-RENAME-EMPTY-DIRECTORY",
        )
    )
    assert nonempty_source.error_code == "FS-TOOL-RENAME-NONEMPTY-SOURCE"
    assert nonempty_destination.error_code == "FS-TOOL-RENAME-NONEMPTY-DESTINATION"
    assert incompatible.error_code == "FS-TOOL-RENAME-INCOMPATIBLE-TARGET"
    assert successful.succeeded
    assert not (public / "empty-source").exists()
    assert (public / "empty-destination").is_dir()


def test_create_and_mkdir_reject_symlinked_parent_after_allow(isolated_root: Path) -> None:
    public = isolated_root / "workspace" / "public"
    output = isolated_root / "workspace" / "output"
    (public / "parent-link").symlink_to(output, target_is_directory=True)
    capabilities = [
        Capability("filesystem.create", "/workspace/public/**"),
        Capability("filesystem.mkdir", "/workspace/public/**"),
    ]
    spy = SpyPrimitives()
    adapter, _ = adapter_for(isolated_root, capabilities, primitives=spy)
    created = adapter.execute(
        request(
            FilesystemOperation.CREATE,
            "public/parent-link/file.bin",
            data=b"payload",
            request_id="DEV-FS-CREATE-SYMLINKED-PARENT",
        )
    )
    directory = adapter.execute(
        request(
            FilesystemOperation.MKDIR,
            "public/parent-link/directory",
            request_id="DEV-FS-MKDIR-SYMLINKED-PARENT",
        )
    )
    assert created.error_code == "EXP014-TARGET-SYMLINK-REJECT"
    assert directory.error_code == "EXP014-TARGET-SYMLINK-REJECT"
    assert spy.requested == []
    assert not (output / "file.bin").exists()
    assert not (output / "directory").exists()


def test_logical_root_is_list_stat_only_after_authorization(isolated_root: Path) -> None:
    capabilities = [Capability(operation.value, "/workspace") for operation in FilesystemOperation]
    spy = SpyPrimitives()
    adapter, _ = adapter_for(isolated_root, capabilities, primitives=spy)
    listed = adapter.execute(request(FilesystemOperation.LIST, "/workspace"))
    stated = adapter.execute(request(FilesystemOperation.STAT, "/workspace"))
    rejected = adapter.execute(
        request(
            FilesystemOperation.CREATE,
            "/workspace",
            data=b"not-created",
            request_id="DEV-FS-ROOT-CREATE-REJECT",
        )
    )
    assert listed.value == ("output", "private", "public")
    assert isinstance(stated.value, FilesystemStat)
    assert rejected.category is FilesystemResultCategory.FAIL_CLOSED
    assert rejected.error_code == "EXP014-TARGET-ROOT-REJECT"
    assert spy.requested == ["list", "stat"]


def test_state_digest_is_deterministic_and_excludes_host_prefix(isolated_root: Path) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "b.bin").write_bytes(b"b")
    (public / "a.bin").write_bytes(b"a")
    mapper = LogicalHostMapper(isolated_root)
    first = digest_manifest(mapper, ("/workspace/public", "/workspace/public/a.bin"))
    second = digest_manifest(mapper, ("/workspace/public/a.bin", "/workspace/public"))
    assert first == second
    assert str(isolated_root) not in first.canonical_json
    assert "mtime" not in first.canonical_json
    assert "inode" not in first.canonical_json


def test_state_digest_changes_for_registered_semantic_mutations(
    isolated_root: Path,
) -> None:
    public = isolated_root / "workspace" / "public"
    target = public / "tracked.bin"
    target.write_bytes(b"before")
    mapper = LogicalHostMapper(isolated_root)
    scope = ("/workspace/public", "/workspace/public/tracked.bin")
    initial = digest_manifest(mapper, scope).digest

    target.write_bytes(b"after")
    content_changed = digest_manifest(mapper, scope).digest
    assert content_changed != initial

    child = public / "new-child.bin"
    child.write_bytes(b"child")
    child_created = digest_manifest(mapper, scope).digest
    assert child_created != content_changed

    child.rename(public / "renamed-child.bin")
    child_renamed = digest_manifest(mapper, scope).digest
    assert child_renamed != child_created

    (public / "renamed-child.bin").unlink()
    child_deleted = digest_manifest(mapper, scope).digest
    assert child_deleted != child_renamed


def test_equivalent_roots_have_identical_semantic_state_digest(
    isolated_root: Path,
) -> None:
    first_public = isolated_root / "workspace" / "public"
    (first_public / "same.bin").write_bytes(b"same")
    with TemporaryDirectory(prefix="safetybox-dev-fs-equivalent-") as directory:
        second_root = Path(directory)
        second_public = second_root / "workspace" / "public"
        second_public.mkdir(parents=True)
        (second_public / "same.bin").write_bytes(b"same")
        scope = ("/workspace/public", "/workspace/public/same.bin")
        first = digest_manifest(LogicalHostMapper(isolated_root), scope)
        second = digest_manifest(LogicalHostMapper(second_root), scope)

    assert first.digest == second.digest
    assert first.canonical_json == second.canonical_json


def test_state_digest_marks_symlink_other_and_absent_without_target_disclosure(
    isolated_root: Path,
) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "link").symlink_to("secret-target-name")
    os.mkfifo(public / "fifo")
    observed = digest_manifest(
        LogicalHostMapper(isolated_root),
        (
            "/workspace/public",
            "/workspace/public/link",
            "/workspace/public/fifo",
            "/workspace/public/absent",
        ),
    )
    assert '"type":"SYMLINK"' in observed.canonical_json
    assert '"type":"OTHER"' in observed.canonical_json
    assert '"type":"ABSENT"' in observed.canonical_json
    assert "secret-target-name" not in observed.canonical_json


def test_missing_and_existing_preconditions_are_tool_errors(isolated_root: Path) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "exists.bin").write_bytes(b"x")
    capabilities = [
        Capability(operation.value, "/workspace/public/**") for operation in FilesystemOperation
    ]
    adapter, _ = adapter_for(isolated_root, capabilities)
    cases = [
        request(FilesystemOperation.READ, "public/missing.bin"),
        request(FilesystemOperation.WRITE, "public/missing.bin", data=b"x"),
        request(FilesystemOperation.APPEND, "public/missing.bin", data=b"x"),
        request(FilesystemOperation.CREATE, "public/exists.bin", data=b"x"),
        request(FilesystemOperation.MKDIR, "public/missing-parent/child"),
    ]
    results = [adapter.execute(case) for case in cases]
    assert all(result.category is FilesystemResultCategory.TOOL_ERROR for result in results)
    assert all(result.decision is Decision.ALLOW for result in results)


def test_wrong_object_types_are_tool_errors(isolated_root: Path) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "directory").mkdir()
    (public / "file.bin").write_bytes(b"file")
    capabilities = [
        Capability(operation.value, "/workspace/public/**") for operation in FilesystemOperation
    ]
    adapter, _ = adapter_for(isolated_root, capabilities)
    results = [
        adapter.execute(request(FilesystemOperation.READ, "public/directory")),
        adapter.execute(request(FilesystemOperation.LIST, "public/file.bin")),
    ]
    assert [result.error_code for result in results] == [
        "FS-TOOL-TYPE-MISMATCH",
        "FS-TOOL-TYPE-MISMATCH",
    ]


def test_unsupported_terminal_and_nondirectory_ancestor_are_tool_errors(
    isolated_root: Path,
) -> None:
    public = isolated_root / "workspace" / "public"
    os.mkfifo(public / "named-pipe")
    (public / "ancestor-file").write_bytes(b"file")
    adapter, _ = adapter_for(
        isolated_root,
        [
            Capability("filesystem.delete", "/workspace/public/**"),
            Capability("filesystem.stat", "/workspace/public/**"),
            Capability("filesystem.create", "/workspace/public/**"),
        ],
    )
    deleted = adapter.execute(request(FilesystemOperation.DELETE, "public/named-pipe"))
    stated = adapter.execute(request(FilesystemOperation.STAT, "public/named-pipe"))
    nested = adapter.execute(
        request(
            FilesystemOperation.CREATE,
            "public/ancestor-file/child",
            data=b"child",
        )
    )
    assert deleted.error_code == "FS-TOOL-UNSUPPORTED-TYPE"
    assert stated.error_code == "FS-TOOL-UNSUPPORTED-TYPE"
    assert nested.error_code == "FS-TOOL-PARENT-NOT-DIRECTORY"


def test_nonempty_directory_delete_is_nonrecursive_tool_error(isolated_root: Path) -> None:
    directory = isolated_root / "workspace" / "public" / "nonempty"
    directory.mkdir()
    (directory / "child.bin").write_bytes(b"child")
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.delete", "/workspace/public/**")],
    )
    result = adapter.execute(request(FilesystemOperation.DELETE, "public/nonempty"))
    assert result.category is FilesystemResultCategory.TOOL_ERROR
    assert (directory / "child.bin").read_bytes() == b"child"


@dataclass
class FailingSink:
    fail_on: EventType
    events_recorded: list[SafetyBoxEvent] = field(default_factory=list)

    def record(self, event: SafetyBoxEvent) -> None:
        if event.event_type is self.fail_on:
            raise OSError("development audit failure")
        self.events_recorded.append(event)


@pytest.mark.parametrize(
    "event_type",
    [EventType.ADAPTER_REQUEST_RECEIVED, EventType.CANONICALIZATION_SUCCEEDED],
)
def test_early_audit_failures_are_fail_closed(isolated_root: Path, event_type: EventType) -> None:
    target = isolated_root / "workspace" / "public" / "write.bin"
    target.write_bytes(b"before")
    failing = FailingSink(event_type)
    policy = TaskContractPolicy(
        TaskContract(
            "dev-task-a",
            "development only",
            [Capability("filesystem.write", "/workspace/public/**")],
        )
    )
    adapter = FilesystemAdapter(
        mapper=LogicalHostMapper(isolated_root),
        authorizer=policy,
        policy_reference="DEV-FS-POLICY@1",
        audit_recorder=AuditRecorder(failing),
    )
    result = adapter.execute(request(FilesystemOperation.WRITE, "public/write.bin", data=b"after"))
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert target.read_bytes() == b"before"


def test_canonicalization_failure_audit_loss_remains_fail_closed(
    isolated_root: Path,
) -> None:
    failing = FailingSink(EventType.CANONICALIZATION_FAILED)
    adapter = FilesystemAdapter(
        mapper=LogicalHostMapper(isolated_root),
        authorizer=TaskContractPolicy(TaskContract("dev-task-a", "development only")),
        policy_reference="DEV-FS-POLICY@1",
        audit_recorder=AuditRecorder(failing),
    )
    result = adapter.execute(request(FilesystemOperation.READ, "../../escape"))
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert result.error_code == "FS-CANONICALIZATION-ROOT-ESCAPE"


def test_unexpected_canonicalization_exception_fails_closed(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter, sink = adapter_for(isolated_root, [])

    def fail_canonicalization(value: str) -> str:
        raise RuntimeError("injected canonicalization failure")

    monkeypatch.setattr(
        "safetybox.filesystem.adapter.canonicalize_logical_path", fail_canonicalization
    )
    result = adapter.execute(request(FilesystemOperation.READ, "public/read.bin"))
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert result.error_code == "FS-CANONICALIZATION-FAILED"
    assert EventType.CANONICALIZATION_FAILED in event_types(sink)
    assert EventType.ACTION_REQUESTED not in event_types(sink)


def test_pre_execution_audit_failure_prevents_effect(isolated_root: Path) -> None:
    target = isolated_root / "workspace" / "public" / "write.bin"
    target.write_bytes(b"before")
    failing = FailingSink(EventType.EXECUTION_STARTED)
    spy = SpyPrimitives()
    policy = TaskContractPolicy(
        TaskContract(
            "dev-task-a",
            "development only",
            [Capability("filesystem.write", "/workspace/public/**")],
        )
    )
    adapter = FilesystemAdapter(
        mapper=LogicalHostMapper(isolated_root),
        authorizer=policy,
        policy_reference="DEV-FS-POLICY@1",
        audit_recorder=AuditRecorder(failing),
        primitives=spy,
    )
    result = adapter.execute(request(FilesystemOperation.WRITE, "public/write.bin", data=b"after"))
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert target.read_bytes() == b"before"
    assert spy.requested == []


def test_post_execution_audit_failure_is_indeterminate_and_effect_remains(
    isolated_root: Path,
) -> None:
    target = isolated_root / "workspace" / "public" / "write.bin"
    target.write_bytes(b"before")
    failing = FailingSink(EventType.EXECUTION_SUCCEEDED)
    policy = TaskContractPolicy(
        TaskContract(
            "dev-task-a",
            "development only",
            [Capability("filesystem.write", "/workspace/public/**")],
        )
    )
    adapter = FilesystemAdapter(
        mapper=LogicalHostMapper(isolated_root),
        authorizer=policy,
        policy_reference="DEV-FS-POLICY@1",
        audit_recorder=AuditRecorder(failing),
    )
    result = adapter.execute(request(FilesystemOperation.WRITE, "public/write.bin", data=b"after"))
    assert result.category is FilesystemResultCategory.FAIL_INDETERMINATE
    assert result.error_code == "FS-AUDIT-POST-EXECUTION"
    assert target.read_bytes() == b"after"
    assert result.evidence.execution_attempted is True
    assert result.evidence.execution_succeeded is None


def test_post_effect_lifecycle_failure_never_claims_nonexecution(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = isolated_root / "workspace" / "public" / "write.bin"
    target.write_bytes(b"before")
    adapter, sink = adapter_for(
        isolated_root,
        [Capability("filesystem.write", "/workspace/public/**")],
    )
    from safetybox.filesystem import audit as filesystem_audit

    real_digest = filesystem_audit.digest_manifest
    calls = 0

    def fail_first_post_effect_digest(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected post-effect lifecycle failure")
        return real_digest(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(filesystem_audit, "digest_manifest", fail_first_post_effect_digest)
    result = adapter.execute(request(FilesystemOperation.WRITE, "public/write.bin", data=b"after"))
    failed = next(
        event for event in sink.events() if event.event_type is EventType.EXECUTION_FAILED
    )

    assert target.read_bytes() == b"after"
    assert result.category is FilesystemResultCategory.FAIL_INDETERMINATE
    assert result.evidence.execution_attempted is True
    assert result.evidence.execution_succeeded is None
    assert failed.executed is True
    assert failed.metadata["execution_attempted"] is True
    assert failed.metadata["execution_succeeded"] is True


@dataclass
class InjectedWriteFailure(SpyPrimitives):
    effect_possible: bool = False

    def write(self, path: Path, data: bytes) -> None:
        self._record("write")
        if self.effect_possible:
            os.truncate(path, 0)
        raise FilesystemPrimitiveError(
            "DEV-FS-PRIMITIVE-FAILURE-WRITE",
            "Injected write failure.",
            effect_possible=self.effect_possible,
        )


@pytest.mark.parametrize(
    ("effect_possible", "expected"),
    [
        (False, FilesystemResultCategory.TOOL_ERROR),
        (True, FilesystemResultCategory.FAIL_INDETERMINATE),
    ],
)
def test_write_failure_classification_tracks_partial_effect_possibility(
    isolated_root: Path,
    effect_possible: bool,
    expected: FilesystemResultCategory,
) -> None:
    target = isolated_root / "workspace" / "public" / "write.bin"
    target.write_bytes(b"before")
    primitives = InjectedWriteFailure(effect_possible=effect_possible)
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.write", "/workspace/public/**")],
        primitives=primitives,
    )
    result = adapter.execute(request(FilesystemOperation.WRITE, "public/write.bin", data=b"after"))
    assert result.category is expected
    assert result.evidence.post_state_digest is not None
    if effect_possible:
        assert target.read_bytes() == b""
    else:
        assert target.read_bytes() == b"before"


@dataclass
class PermissionLikeReadFailure(SpyPrimitives):
    def read(self, path: Path) -> bytes:
        self._record("read")
        raise FilesystemPrimitiveError(
            "DEV-FS-PRIMITIVE-FAILURE-PERMISSION",
            "Injected permission-like failure.",
            effect_possible=False,
        )


def test_permission_like_primitive_failure_is_tool_error(isolated_root: Path) -> None:
    target = isolated_root / "workspace" / "public" / "read.bin"
    target.write_bytes(b"protected")
    primitives = PermissionLikeReadFailure()
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.read", "/workspace/public/**")],
        primitives=primitives,
    )
    result = adapter.execute(request(FilesystemOperation.READ, "public/read.bin"))
    assert result.category is FilesystemResultCategory.TOOL_ERROR
    assert result.error_code == "DEV-FS-PRIMITIVE-FAILURE-PERMISSION"
    assert result.value is None


@dataclass
class UnexpectedAfterStart(SpyPrimitives):
    def read(self, path: Path) -> bytes:
        self._record("read")
        raise RuntimeError("unexpected injected execution failure")


def test_unexpected_failure_after_primitive_start_is_indeterminate(
    isolated_root: Path,
) -> None:
    target = isolated_root / "workspace" / "public" / "read.bin"
    target.write_bytes(b"protected")
    primitives = UnexpectedAfterStart()
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.read", "/workspace/public/**")],
        primitives=primitives,
    )
    result = adapter.execute(request(FilesystemOperation.READ, "public/read.bin"))
    assert result.category is FilesystemResultCategory.FAIL_INDETERMINATE
    assert result.error_code == "FS-UNEXPECTED-FAILURE"
    assert result.evidence.execution_attempted is True
    assert result.evidence.execution_succeeded is None


def test_authorization_exception_fails_closed_without_probe(isolated_root: Path) -> None:
    class FailingAuthorizer:
        def authorize(self, action_request: ActionRequest) -> PolicyDecision:
            raise RuntimeError("policy unavailable")

    spy = SpyPrimitives()
    adapter, sink = adapter_for(isolated_root, [], primitives=spy, authorizer=FailingAuthorizer())
    result = adapter.execute(request(FilesystemOperation.READ, "private/secret.bin"))
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert result.error_code == "FS-AUTHORIZATION-FAILED"
    assert spy.probes == []
    assert spy.requested == []
    assert EventType.AUTHORIZATION_FAILED in event_types(sink)


def test_physical_validation_exception_fails_closed(isolated_root: Path) -> None:
    class FailingValidation(SpyPrimitives):
        def lstat(self, path: Path) -> os.stat_result:
            raise PermissionError("injected validation failure")

    primitives = FailingValidation()
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.read", "/workspace/public/**")],
        primitives=primitives,
    )
    result = adapter.execute(request(FilesystemOperation.READ, "public/file.bin"))
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert result.error_code == "EXP014-TARGET-INSPECTION-FAILED"
    assert primitives.requested == []


def test_state_observation_failure_before_execution_fails_closed(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = isolated_root / "workspace" / "public" / "write.bin"
    target.write_bytes(b"before")
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.write", "/workspace/public/**")],
    )

    def fail_digest(*args: object, **kwargs: object) -> object:
        raise OSError("injected state observation failure")

    monkeypatch.setattr("safetybox.filesystem.audit.digest_manifest", fail_digest)
    result = adapter.execute(request(FilesystemOperation.WRITE, "public/write.bin", data=b"after"))
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert result.error_code == "EXP014-TARGET-VALIDATION-FAILED"
    assert target.read_bytes() == b"before"


def test_compound_authorization_exception_records_both_subdecisions(
    isolated_root: Path,
) -> None:
    public = isolated_root / "workspace" / "public"
    (public / "source.bin").write_bytes(b"source")

    class PartiallyFailingAuthorizer:
        def authorize(self, action_request: ActionRequest) -> PolicyDecision:
            if action_request.resource.endswith("source.bin"):
                raise RuntimeError("source policy failure")
            return PolicyDecision(Decision.ALLOW, "DEV-POLICY-ALLOW", "allowed")

    spy = SpyPrimitives()
    adapter, sink = adapter_for(
        isolated_root,
        [],
        primitives=spy,
        authorizer=PartiallyFailingAuthorizer(),
    )
    result = adapter.execute(
        request(
            FilesystemOperation.RENAME,
            "public/source.bin",
            destination="public/destination.bin",
        )
    )
    failed = next(
        event for event in sink.events() if event.event_type is EventType.AUTHORIZATION_FAILED
    )
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert len(failed.metadata["subdecisions"]) == 2  # type: ignore[arg-type]
    assert len(result.evidence.authorizations) == 2
    assert result.evidence.authorizations[0].decision is None
    assert result.evidence.authorizations[1].decision is Decision.ALLOW
    assert spy.probes == []
    assert spy.requested == []


def test_task_and_session_provenance_remain_isolated(isolated_root: Path) -> None:
    target = isolated_root / "workspace" / "public" / "read.bin"
    target.write_bytes(b"value")
    capabilities = [Capability("filesystem.read", "/workspace/public/**")]
    adapter, sink = adapter_for(isolated_root, capabilities)
    allowed = adapter.execute(
        request(
            FilesystemOperation.READ,
            "public/read.bin",
            session_id="dev-session-a",
            request_id="DEV-FS-SESSION-A",
        )
    )
    denied = adapter.execute(
        request(
            FilesystemOperation.READ,
            "public/read.bin",
            session_id="dev-session-b",
            task_id="wrong-task",
            request_id="DEV-FS-SESSION-B",
        )
    )
    assert allowed.succeeded
    assert denied.category is FilesystemResultCategory.DENY
    a_events = [event for event in sink.events() if event.session_id == "dev-session-a"]
    b_events = [event for event in sink.events() if event.session_id == "dev-session-b"]
    assert [event.sequence_number for event in a_events] == list(range(1, 11))
    assert [event.sequence_number for event in b_events] == list(range(1, 7))
    assert {event.task_id for event in a_events} == {"dev-task-a"}
    assert {event.task_id for event in b_events} == {"wrong-task"}


def test_semantically_equivalent_runs_are_deterministic(isolated_root: Path) -> None:
    target = isolated_root / "workspace" / "public" / "read.bin"
    target.write_bytes(b"deterministic")
    capability = Capability("filesystem.read", "/workspace/public/**")
    first_adapter, first_sink = adapter_for(isolated_root, [capability])
    second_adapter, second_sink = adapter_for(isolated_root, [capability])
    first = first_adapter.execute(request(FilesystemOperation.READ, "public/./read.bin"))
    second = second_adapter.execute(request(FilesystemOperation.READ, "/workspace/public/read.bin"))
    assert first.category == second.category
    assert first.canonical_resource == second.canonical_resource
    assert first.value == second.value
    assert event_types(first_sink) == event_types(second_sink)
    assert [event.sequence_number for event in first_sink.events()] == [
        event.sequence_number for event in second_sink.events()
    ]


def test_expected_fmed_l1_direct_route_bypass_is_demonstrated_only_in_temp_root(
    isolated_root: Path,
) -> None:
    target = isolated_root / "workspace" / "private" / "bypass.bin"
    target.write_bytes(b"before")
    adapter, _ = adapter_for(isolated_root, [])
    denied = adapter.execute(
        request(FilesystemOperation.WRITE, "private/bypass.bin", data=b"adapter")
    )
    descriptor = os.open(target, os.O_WRONLY | os.O_TRUNC)
    try:
        os.write(descriptor, b"EXPECTED_FMED_L1_BYPASS")
    finally:
        os.close(descriptor)
    assert denied.category is FilesystemResultCategory.DENY
    assert target.read_bytes() == b"EXPECTED_FMED_L1_BYPASS"


def test_development_audit_evidence_is_machine_reconstructable(isolated_root: Path) -> None:
    target = isolated_root / "workspace" / "public" / "read.bin"
    target.write_bytes(b"evidence")
    adapter, sink = adapter_for(
        isolated_root,
        [Capability("filesystem.read", "/workspace/public/**")],
    )
    result = adapter.execute(request(FilesystemOperation.READ, "public/read.bin"))
    envelope = result.evidence
    assert envelope.session_id
    assert envelope.task_id
    assert envelope.request_id == envelope.correlation_id
    assert envelope.requested_resource
    assert envelope.canonical_resource == "/workspace/public/read.bin"
    assert envelope.action == "filesystem.read"
    assert envelope.authorizations[0].rule_id
    assert envelope.execution_attempted
    assert envelope.execution_succeeded
    assert envelope.adapter_version
    assert envelope.policy_reference
    assert envelope.sequence_numbers == tuple(event.sequence_number for event in sink.events())
    assert b"evidence" not in repr(sink.events()).encode()


def test_write_payload_is_hashed_but_never_recorded_in_audit(isolated_root: Path) -> None:
    target = isolated_root / "workspace" / "public" / "write.bin"
    target.write_bytes(b"before")
    adapter, sink = adapter_for(
        isolated_root,
        [Capability("filesystem.write", "/workspace/public/**")],
    )
    payload = b"RAW-WRITE-PAYLOAD-MUST-NOT-APPEAR"
    result = adapter.execute(request(FilesystemOperation.WRITE, "public/write.bin", data=payload))
    rendered = repr(sink.events()).encode()
    assert result.succeeded
    assert payload not in rendered
    assert result.evidence.arguments_digest is not None


def test_real_primitive_os_errors_are_normalized_inside_temp_root(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primitives = RealFilesystemPrimitives()
    public = isolated_root / "workspace" / "public"
    (public / "existing.bin").write_bytes(b"existing")
    (public / "nonempty").mkdir()
    (public / "nonempty" / "child").write_bytes(b"child")
    os.mkfifo(public / "fifo")
    missing = public / "missing"

    failing_calls = [
        lambda: primitives.read(missing),
        lambda: primitives.write(missing, b"x"),
        lambda: primitives.append(missing, b"x"),
        lambda: primitives.create(public / "existing.bin", b"x"),
        lambda: primitives.delete_file(missing),
        lambda: primitives.delete_directory(public / "nonempty"),
        lambda: primitives.rename(missing, public / "destination"),
        lambda: primitives.mkdir(public / "nonempty"),
        lambda: primitives.list_directory(public / "existing.bin"),
        lambda: primitives.minimized_stat(missing),
        lambda: primitives.minimized_stat(public / "fifo"),
    ]
    for call in failing_calls:
        with pytest.raises(FilesystemPrimitiveError):
            call()

    monkeypatch.setattr(os, "write", lambda descriptor, data: 0)
    with pytest.raises(FilesystemPrimitiveError) as failure:
        primitives.append(public / "existing.bin", b"x")
    assert failure.value.effect_possible is False


def test_governed_identifier_hides_invalid_path_payload(isolated_root: Path) -> None:
    adapter, sink = adapter_for(isolated_root, [])
    malformed = request(FilesystemOperation.READ, "public/secret\x00suffix")
    result = adapter.execute(malformed)
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert result.evidence.requested_resource.startswith("governed-sha256:")
    assert "secret" not in repr(sink.events())


def test_governed_identifier_hides_invalid_absolute_host_path(isolated_root: Path) -> None:
    adapter, sink = adapter_for(isolated_root, [])
    sentinel = "/home/PRIVATE-HOST-PATH-SENTINEL/.ssh/id_key"
    result = adapter.execute(request(FilesystemOperation.READ, sentinel))
    assert result.category is FilesystemResultCategory.FAIL_CLOSED
    assert result.evidence.requested_resource.startswith("governed-sha256:")
    assert "PRIVATE-HOST-PATH-SENTINEL" not in repr((result, sink.events()))


def test_post_failure_state_observation_error_is_retained_as_unknown(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = isolated_root / "workspace" / "public" / "write.bin"
    target.write_bytes(b"before")
    primitives = InjectedWriteFailure(effect_possible=True)
    adapter, _ = adapter_for(
        isolated_root,
        [Capability("filesystem.write", "/workspace/public/**")],
        primitives=primitives,
    )
    from safetybox.filesystem import audit as filesystem_audit

    real_digest = filesystem_audit.digest_manifest
    calls = 0

    def fail_second_digest(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls > 1:
            raise OSError("injected post-state observation failure")
        return real_digest(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(filesystem_audit, "digest_manifest", fail_second_digest)
    result = adapter.execute(request(FilesystemOperation.WRITE, "public/write.bin", data=b"after"))
    assert result.category is FilesystemResultCategory.FAIL_INDETERMINATE
    assert result.evidence.pre_state_digest is not None
    assert result.evidence.post_state_digest is None
