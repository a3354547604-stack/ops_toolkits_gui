from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MountUsage:
    device: str
    mountpoint: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    used_percent: int


@dataclass(frozen=True)
class LargeFile:
    size_bytes: int
    path: str


@dataclass(frozen=True)
class DirUsage:
    size_bytes: int
    path: str


@dataclass(frozen=True)
class PermCheck:
    path: str
    mode_octal: str
    owner: str
    group: str
    ok: bool
    message: str


@dataclass(frozen=True)
class FilesystemData:
    mounts: list[MountUsage]
    large_files: list[LargeFile]
    dir_usages: list[DirUsage]
    perm_checks: list[PermCheck]
    notes: list[str]
