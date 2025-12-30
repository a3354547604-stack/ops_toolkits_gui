from __future__ import annotations

import os
import stat
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import psutil

from ops_toolkit_gui.models.common import CollectorResult
from ops_toolkit_gui.models.filesystem import (
    DirUsage,
    FilesystemData,
    LargeFile,
    MountUsage,
    PermCheck,
)


class FilesystemCollector:
    def __init__(
        self,
        scan_dir: str = "/",
        target_dir: str = "/var",
        large_file_mb: int = 200,
        large_file_timeout_s: int = 8,
        dir_timeout_s: int = 8,
        disk_warn_percent: int = 85,
    ) -> None:
        self.scan_dir = scan_dir
        self.target_dir = target_dir
        self.large_file_mb = int(large_file_mb)
        self.large_file_timeout_s = int(large_file_timeout_s)
        self.dir_timeout_s = int(dir_timeout_s)
        self.disk_warn_percent = int(disk_warn_percent)

    def collect(self) -> CollectorResult[FilesystemData]:
        ts = datetime.now()
        warnings: list[str] = []
        notes: list[str] = []

        mounts = self._mounts()
        for m in mounts:
            if m.used_percent >= self.disk_warn_percent:
                warnings.append(
                    f"Disk usage high: {m.mountpoint} {m.used_percent}% (>= {self.disk_warn_percent}%)"
                )

        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_large = ex.submit(self._scan_large_files)
            fut_dirs = ex.submit(self._dir_size_sort)

            large_files: list[LargeFile] = []
            dir_usages: list[DirUsage] = []
            try:
                large_files = fut_large.result(timeout=self.large_file_timeout_s)
            except Exception as e:
                notes.append(f"Large file scan skipped/timeout: {e}")

            try:
                dir_usages = fut_dirs.result(timeout=self.dir_timeout_s)
            except Exception as e:
                notes.append(f"Dir size scan skipped/timeout: {e}")

        perm_checks = self._perm_checks()
        for c in perm_checks:
            if not c.ok:
                warnings.append(f"Permission check failed: {c.path} {c.message}")

        status = "OK" if not warnings else "WARN"
        data = FilesystemData(
            mounts=mounts,
            large_files=large_files,
            dir_usages=dir_usages,
            perm_checks=perm_checks,
            notes=notes,
        )
        return CollectorResult(
            ts=ts,
            status=status,
            warning_count=len(warnings),
            warnings=warnings,
            data=data,
        )

    def _mounts(self) -> list[MountUsage]:
        rows: list[MountUsage] = []
        for p in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(p.mountpoint)
            except Exception:
                continue
            rows.append(
                MountUsage(
                    device=str(p.device),
                    mountpoint=str(p.mountpoint),
                    fstype=str(p.fstype),
                    total_gb=float(u.total / 1024 / 1024 / 1024),
                    used_gb=float(u.used / 1024 / 1024 / 1024),
                    free_gb=float(u.free / 1024 / 1024 / 1024),
                    used_percent=int(u.percent),
                )
            )
        return rows

    def _scan_large_files(self) -> list[LargeFile]:
        root = Path(self.scan_dir)
        min_size = int(self.large_file_mb) * 1024 * 1024

        hits: list[LargeFile] = []
        try:
            for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
                for fn in filenames:
                    p = Path(dirpath) / fn
                    try:
                        st = p.stat()
                    except Exception:
                        continue
                    if st.st_size >= min_size:
                        hits.append(LargeFile(size_bytes=int(st.st_size), path=str(p)))
        except Exception:
            return []

        hits.sort(key=lambda x: x.size_bytes, reverse=True)
        return hits[:50]

    def _dir_size_sort(self) -> list[DirUsage]:
        root = Path(self.target_dir)
        if not root.exists() or not root.is_dir():
            return []

        rows: list[DirUsage] = []
        for p in root.iterdir():
            if not p.is_dir():
                continue
            size = self._dir_size_bytes(p)
            rows.append(DirUsage(size_bytes=size, path=str(p)))

        rows.sort(key=lambda x: x.size_bytes, reverse=True)
        return rows[:50]

    def _dir_size_bytes(self, root: Path) -> int:
        total = 0
        for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
            for fn in filenames:
                p = Path(dirpath) / fn
                try:
                    total += int(p.stat().st_size)
                except Exception:
                    continue
        return total

    def _perm_checks(self) -> list[PermCheck]:
        checks: list[PermCheck] = []
        for path in ("/etc", "/home"):
            p = Path(path)
            if not p.exists():
                continue
            try:
                st = p.stat()
            except Exception:
                continue

            mode = stat.S_IMODE(st.st_mode)
            mode_octal = oct(mode)
            ok = True
            msg = "OK"

            if mode & stat.S_IWOTH:
                ok = False
                msg = "world-writable"

            checks.append(
                PermCheck(
                    path=str(p),
                    mode_octal=mode_octal,
                    owner=str(getattr(st, "st_uid", "")),
                    group=str(getattr(st, "st_gid", "")),
                    ok=ok,
                    message=msg,
                )
            )

        return checks
