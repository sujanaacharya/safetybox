"""Deterministic EXP014-STATE-DIGEST@1 observation utilities."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from pathlib import Path

from safetybox.filesystem.mapping import LogicalHostMapper
from safetybox.filesystem.models import StateDigest
from safetybox.filesystem.versions import STATE_DIGEST_VERSION


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _read_bytes(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def node_record(path: Path) -> dict[str, object]:
    """Observe one node without following a terminal symlink."""
    try:
        status = os.lstat(path)
    except FileNotFoundError:
        return {"type": "ABSENT"}
    if stat.S_ISLNK(status.st_mode):
        return {"type": "SYMLINK"}
    if stat.S_ISREG(status.st_mode):
        content = _read_bytes(path)
        return {
            "type": "FILE",
            "byte_size": len(content),
            "content_sha256": hashlib.sha256(content).hexdigest(),
        }
    if stat.S_ISDIR(status.st_mode):
        children: list[dict[str, str]] = []
        with os.scandir(path) as entries:
            for entry in entries:
                child_status = os.lstat(Path(entry.path))
                if stat.S_ISLNK(child_status.st_mode):
                    child_type = "SYMLINK"
                elif stat.S_ISREG(child_status.st_mode):
                    child_type = "FILE"
                elif stat.S_ISDIR(child_status.st_mode):
                    child_type = "DIRECTORY"
                else:
                    child_type = "OTHER"
                children.append(
                    {
                        "name": unicodedata.normalize("NFC", entry.name),
                        "type": child_type,
                    }
                )
        children.sort(key=lambda child: (child["name"], child["type"]))
        return {"type": "DIRECTORY", "children": children}
    return {"type": "OTHER"}


def digest_manifest(mapper: LogicalHostMapper, logical_paths: tuple[str, ...]) -> StateDigest:
    """Hash a sorted logical-path/node-record manifest without host-path disclosure."""
    records = [
        {"logical_path": logical_path, "node": node_record(mapper.to_host(logical_path))}
        for logical_path in sorted(set(logical_paths))
    ]
    encoded = canonical_json({"records": records, "version": STATE_DIGEST_VERSION})
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return StateDigest(STATE_DIGEST_VERSION, digest, encoded)
