from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LogKeywordHit:
    keyword: str
    count: int


@dataclass(frozen=True)
class LogData:
    path: str
    last_read_pos: int
    new_lines: list[str]
    keyword_hits: list[LogKeywordHit]
    notes: list[str]
