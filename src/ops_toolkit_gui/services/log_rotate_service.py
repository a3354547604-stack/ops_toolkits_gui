from __future__ import annotations

import gzip
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class RotateResult:
    rotated: bool
    archived_path: str | None
    message: str


class LogRotateService:
    def __init__(
        self,
        max_bytes: int = 10 * 1024 * 1024,
        keep_archives: int = 5,
        archive_suffix: str = ".gz",
    ) -> None:
        self.max_bytes = int(max_bytes)
        self.keep_archives = int(keep_archives)
        self.archive_suffix = archive_suffix

    def rotate_if_needed(self, log_path: str) -> RotateResult:
        p = Path(log_path)
        if not p.exists() or not p.is_file():
            return RotateResult(rotated=False, archived_path=None, message=f"log not found: {log_path}")

        try:
            size = p.stat().st_size
        except Exception as e:
            return RotateResult(rotated=False, archived_path=None, message=f"stat failed: {e}")

        if size < self.max_bytes:
            return RotateResult(rotated=False, archived_path=None, message="no rotation")

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_dir = p.parent / "ops_toolkit_archives"
        archive_dir.mkdir(parents=True, exist_ok=True)

        rotated_plain = archive_dir / f"{p.name}.{ts}"
        rotated_gz = Path(str(rotated_plain) + self.archive_suffix)

        try:
            # Atomic-ish: move current log aside, then recreate empty log.
            shutil.move(str(p), str(rotated_plain))
            # Recreate empty file with same permissions best-effort.
            p.touch(exist_ok=True)
        except Exception as e:
            return RotateResult(rotated=False, archived_path=None, message=f"rotate move failed: {e}")

        try:
            with open(rotated_plain, "rb") as f_in, gzip.open(rotated_gz, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            rotated_plain.unlink(missing_ok=True)
        except Exception as e:
            return RotateResult(rotated=True, archived_path=str(rotated_plain), message=f"gzip failed: {e}")

        self._cleanup_old_archives(archive_dir, p.name)
        return RotateResult(rotated=True, archived_path=str(rotated_gz), message="rotated")

    def _cleanup_old_archives(self, archive_dir: Path, base_name: str) -> None:
        try:
            files = sorted(
                archive_dir.glob(f"{base_name}.*{self.archive_suffix}"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )
        except Exception:
            return

        for f in files[self.keep_archives :]:
            try:
                os.remove(f)
            except Exception:
                continue
