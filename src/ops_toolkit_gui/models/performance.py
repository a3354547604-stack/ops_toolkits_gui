from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CpuCoreUsage:
    core: str
    percent: float


@dataclass(frozen=True)
class MemoryStat:
    total_mb: int
    used_mb: int
    used_percent: int


@dataclass(frozen=True)
class SwapStat:
    total_mb: int
    used_mb: int
    used_percent: int


@dataclass(frozen=True)
class LoadAvg:
    load1: float
    load5: float
    load15: float


@dataclass(frozen=True)
class ProcessStat:
    pid: int
    user: str
    name: str
    cpu_percent: float
    mem_percent: float


@dataclass(frozen=True)
class PerformanceData:
    cpu_total_percent: float
    cpu_cores: list[CpuCoreUsage]
    memory: MemoryStat
    swap: SwapStat
    load: LoadAvg
    processes: list[ProcessStat]
