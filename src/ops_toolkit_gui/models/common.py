from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class CollectorResult(Generic[T]):
    ts: datetime
    status: str
    warning_count: int
    data: T
    warnings: list[str] = field(default_factory=list)
