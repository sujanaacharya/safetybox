"""Harmless in-memory simulated tools and observable world state for M4."""

from __future__ import annotations

from dataclasses import dataclass, field

from safetybox.models import ActionRequest


@dataclass(frozen=True, slots=True)
class SimulatedWorldSnapshot:
    """Immutable logical effects observed during one simulation run."""

    files_read: tuple[str, ...]
    network_requests: tuple[str, ...]
    shell_commands: tuple[str, ...]
    database_queries: tuple[str, ...]


@dataclass(slots=True)
class SimulatedWorld:
    """Deliberately tiny mutable state; it never represents real resources."""

    files_read: list[str] = field(default_factory=list)
    network_requests: list[str] = field(default_factory=list)
    shell_commands: list[str] = field(default_factory=list)
    database_queries: list[str] = field(default_factory=list)

    def snapshot(self) -> SimulatedWorldSnapshot:
        return SimulatedWorldSnapshot(
            files_read=tuple(self.files_read),
            network_requests=tuple(self.network_requests),
            shell_commands=tuple(self.shell_commands),
            database_queries=tuple(self.database_queries),
        )


@dataclass(slots=True)
class SimulatedFilesystemTool:
    world: SimulatedWorld

    def execute(self, request: ActionRequest) -> object:
        self.world.files_read.append(request.resource)
        return {"simulated": "filesystem.read", "resource": request.resource}


@dataclass(slots=True)
class SimulatedNetworkTool:
    world: SimulatedWorld

    def execute(self, request: ActionRequest) -> object:
        self.world.network_requests.append(request.resource)
        return {"simulated": "network.send", "resource": request.resource}


@dataclass(slots=True)
class SimulatedShellTool:
    world: SimulatedWorld

    def execute(self, request: ActionRequest) -> object:
        self.world.shell_commands.append(request.resource)
        return {"simulated": "shell.execute", "resource": request.resource}


@dataclass(slots=True)
class SimulatedDatabaseTool:
    world: SimulatedWorld

    def execute(self, request: ActionRequest) -> object:
        self.world.database_queries.append(request.resource)
        return {"simulated": "database.query", "resource": request.resource}


@dataclass(slots=True)
class SimulatedTool:
    """Routes supported action names to in-memory category tools only."""

    world: SimulatedWorld
    _filesystem: SimulatedFilesystemTool = field(init=False)
    _network: SimulatedNetworkTool = field(init=False)
    _shell: SimulatedShellTool = field(init=False)
    _database: SimulatedDatabaseTool = field(init=False)

    def __post_init__(self) -> None:
        self._filesystem = SimulatedFilesystemTool(self.world)
        self._network = SimulatedNetworkTool(self.world)
        self._shell = SimulatedShellTool(self.world)
        self._database = SimulatedDatabaseTool(self.world)

    def execute(self, request: ActionRequest) -> object:
        if request.action == "filesystem.read":
            return self._filesystem.execute(request)
        if request.action == "network.send":
            return self._network.execute(request)
        if request.action == "shell.execute":
            return self._shell.execute(request)
        if request.action == "database.query":
            return self._database.execute(request)
        raise ValueError(f"Unsupported simulated action: {request.action}")
