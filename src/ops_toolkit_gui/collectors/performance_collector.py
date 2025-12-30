from __future__ import annotations

import os
from datetime import datetime

import psutil

from ops_toolkit_gui.models.common import CollectorResult
from ops_toolkit_gui.models.performance import (
    CpuCoreUsage,
    LoadAvg,
    MemoryStat,
    PerformanceData,
    ProcessStat,
    SwapStat,
)


class PerformanceCollector:
    def __init__(
        self,
        cpu_warn_percent: float = 85.0,
        mem_warn_percent: float = 85.0,
        load_warn_per_cpu: float = 1.2,
        top_n_processes: int = 5,
    ) -> None:
        self.cpu_warn_percent = float(cpu_warn_percent)
        self.mem_warn_percent = float(mem_warn_percent)
        self.load_warn_per_cpu = float(load_warn_per_cpu)
        self.top_n_processes = int(top_n_processes)

    def collect(self) -> CollectorResult[PerformanceData]:
        ts = datetime.now()
        warnings: list[str] = []

        cpu_total = float(psutil.cpu_percent(interval=0.2))
        core_percents = psutil.cpu_percent(interval=0.2, percpu=True)
        cpu_cores = [CpuCoreUsage(core=str(i), percent=float(p)) for i, p in enumerate(core_percents)]

        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()

        memory = MemoryStat(
            total_mb=int(vm.total / 1024 / 1024),
            used_mb=int(vm.used / 1024 / 1024),
            used_percent=int(vm.percent),
        )
        swap = SwapStat(
            total_mb=int(sm.total / 1024 / 1024),
            used_mb=int(sm.used / 1024 / 1024),
            used_percent=int(sm.percent),
        )

        try:
            l1, l5, l15 = os.getloadavg()
            load = LoadAvg(load1=float(l1), load5=float(l5), load15=float(l15))
        except (AttributeError, OSError):
            load = LoadAvg(load1=0.0, load5=0.0, load15=0.0)

        processes = self._top_processes(self.top_n_processes)

        if cpu_total >= self.cpu_warn_percent:
            warnings.append(f"High CPU total: {cpu_total:.1f}% (>= {self.cpu_warn_percent:.0f}%)")
        if memory.used_percent >= self.mem_warn_percent:
            warnings.append(
                f"High memory usage: {memory.used_percent}% (>= {self.mem_warn_percent:.0f}%)"
            )

        cpu_count = psutil.cpu_count() or 1
        if load.load1 > cpu_count * self.load_warn_per_cpu:
            warnings.append(
                f"High load1: {load.load1:.2f} (> {cpu_count} * {self.load_warn_per_cpu:.1f})"
            )

        status = "OK" if not warnings else "WARN"
        data = PerformanceData(
            cpu_total_percent=cpu_total,
            cpu_cores=cpu_cores,
            memory=memory,
            swap=swap,
            load=load,
            processes=processes,
        )
        return CollectorResult(
            ts=ts,
            status=status,
            warning_count=len(warnings),
            warnings=warnings,
            data=data,
        )

    def _top_processes(self, n: int) -> list[ProcessStat]:
        procs: list[psutil.Process] = []
        for p in psutil.process_iter(attrs=["pid", "name", "username"]):
            procs.append(p)

        for p in procs:
            try:
                p.cpu_percent(interval=None)
            except Exception:
                continue

        psutil.cpu_percent(interval=0.1)

        stats: list[ProcessStat] = []
        for p in procs:
            try:
                cpu = float(p.cpu_percent(interval=None))
                mem = float(p.memory_percent())
                info = p.info
                stats.append(
                    ProcessStat(
                        pid=int(info.get("pid") or p.pid),
                        user=str(info.get("username") or ""),
                        name=str(info.get("name") or p.name()),
                        cpu_percent=cpu,
                        mem_percent=mem,
                    )
                )
            except Exception:
                continue

        stats.sort(key=lambda s: (s.cpu_percent, s.mem_percent), reverse=True)
        return stats[: max(0, int(n))]
