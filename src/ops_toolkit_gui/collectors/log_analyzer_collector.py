from __future__ import annotations

import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from ops_toolkit_gui.models.common import CollectorResult
from ops_toolkit_gui.models.logs import LogData, LogKeywordHit
from ops_toolkit_gui.services.log_rotate_service import LogRotateService


class LogAnalyzerCollector:
    def __init__(
        self,
        path: str | None = None,
        keywords: list[str] | None = None,
        rotate_max_bytes: int = 10 * 1024 * 1024,
        rotate_keep_archives: int = 5,
        max_lines_per_poll: int = 500,
        max_line_length: int = 2000,
    ) -> None:
        self.path = path or self._default_log_path()
        self.keywords = keywords or ["ERROR", "Failed", "Warning"]
        self._rotator = LogRotateService(
            max_bytes=int(rotate_max_bytes),
            keep_archives=int(rotate_keep_archives),
        )
        self.max_lines_per_poll = int(max_lines_per_poll)
        self.max_line_length = int(max_line_length)
        self._pos: int = 0

    def configure(
        self,
        path: str | None = None,
        keywords: list[str] | None = None,
        rotate_max_bytes: int | None = None,
        rotate_keep_archives: int | None = None,
    ) -> None:
        if path:
            self.path = path
        if keywords is not None:
            self.keywords = keywords
        if rotate_max_bytes is not None:
            self._rotator = LogRotateService(
                max_bytes=int(rotate_max_bytes),
                keep_archives=self._rotator.keep_archives,
            )
        if rotate_keep_archives is not None:
            self._rotator = LogRotateService(
                max_bytes=self._rotator.max_bytes,
                keep_archives=int(rotate_keep_archives),
            )
        self._pos = 0

    def collect(self) -> CollectorResult[LogData]:
        ts = datetime.now()
        warnings: list[str] = []
        notes: list[str] = []

        p = Path(self.path)
        if not p.exists() or not p.is_file():
            notes.append(f"Log file not found: {self.path}")
            data = LogData(
                path=self.path,
                last_read_pos=self._pos,
                new_lines=[],
                keyword_hits=[],
                notes=notes,
            )
            return CollectorResult(ts=ts, status="WARN", warning_count=1, warnings=[notes[-1]], data=data)

        rotate_res = self._rotator.rotate_if_needed(self.path)
        if rotate_res.rotated:
            self._pos = 0
            if rotate_res.archived_path:
                notes.append(f"log rotated: {rotate_res.archived_path}")
            else:
                notes.append("log rotated")

        try:
            st = p.stat()
            if self._pos > st.st_size:
                self._pos = 0
        except Exception as e:
            notes.append(f"stat failed: {e}")

        lines: list[str] = []
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._pos)
                for _ in range(self.max_lines_per_poll):
                    line = f.readline()
                    if not line:
                        break
                    line = line.rstrip("\n")
                    if len(line) > self.max_line_length:
                        line = line[: self.max_line_length] + "…"
                    lines.append(line)
                self._pos = f.tell()
        except Exception as e:
            notes.append(f"read failed: {e}")

        hits = self._keyword_hits(lines, self.keywords)
        hit_list = [LogKeywordHit(keyword=k, count=int(v)) for k, v in hits.items()]
        hit_list.sort(key=lambda x: x.count, reverse=True)

        if sum(hits.values()) > 0:
            warnings.append(f"Keyword hits: {sum(hits.values())}")

        status = "OK" if not warnings else "WARN"
        data = LogData(
            path=self.path,
            last_read_pos=self._pos,
            new_lines=lines,
            keyword_hits=hit_list,
            notes=notes,
        )
        return CollectorResult(
            ts=ts,
            status=status,
            warning_count=len(warnings),
            warnings=warnings,
            data=data,
        )

    def _keyword_hits(self, lines: list[str], keywords: list[str]) -> Counter[str]:
        c: Counter[str] = Counter()
        if not keywords:
            return c

        pats: list[tuple[str, re.Pattern[str]]] = []
        for k in keywords:
            k = k.strip()
            if not k:
                continue
            pats.append((k, re.compile(re.escape(k), re.IGNORECASE)))

        for line in lines:
            for k, rx in pats:
                if rx.search(line):
                    c[k] += 1
        return c

    def _default_log_path(self) -> str:
        for cand in ("/var/log/syslog", "/var/log/messages"):
            if os.path.exists(cand):
                return cand
        return "/var/log/syslog"
