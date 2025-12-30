from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QGroupBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ops_toolkit_gui.models.common import CollectorResult
from ops_toolkit_gui.models.performance import CpuCoreUsage, PerformanceData, ProcessStat


class NumericItem(QTableWidgetItem):
    def __init__(self, text: str, value: float) -> None:
        super().__init__(text)
        self._value = float(value)

    def __lt__(self, other: QTableWidgetItem) -> bool:  # type: ignore[override]
        if isinstance(other, NumericItem):
            return self._value < other._value
        return super().__lt__(other)


class PerformancePage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.cpu_total = QLabel("-")
        self.mem = QLabel("-")
        self.swap = QLabel("-")
        self.load = QLabel("-")

        for lbl in (self.cpu_total, self.mem, self.swap, self.load):
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        metrics_box = QGroupBox("Metrics")
        grid = QGridLayout(metrics_box)
        grid.addWidget(QLabel("CPU Total"), 0, 0)
        grid.addWidget(self.cpu_total, 0, 1)
        grid.addWidget(QLabel("Memory"), 1, 0)
        grid.addWidget(self.mem, 1, 1)
        grid.addWidget(QLabel("Swap"), 2, 0)
        grid.addWidget(self.swap, 2, 1)
        grid.addWidget(QLabel("Load Avg"), 3, 0)
        grid.addWidget(self.load, 3, 1)

        self.cpu_cores = self._make_core_table("CPU Cores")
        self.processes = self._make_proc_table("Processes")

        self.processes[1].setSortingEnabled(True)
        self.processes[1].sortItems(3, Qt.SortOrder.DescendingOrder)

        layout = QVBoxLayout(self)
        layout.addWidget(metrics_box)
        layout.addWidget(self.cpu_cores[0], 1)
        layout.addWidget(self.processes[0], 2)

    def _make_core_table(self, title: str) -> tuple[QGroupBox, QTableWidget]:
        gb = QGroupBox(title)
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["CORE", "CPU%"])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)

        l = QVBoxLayout(gb)
        l.addWidget(table)
        return gb, table

    def _make_proc_table(self, title: str) -> tuple[QGroupBox, QTableWidget]:
        gb = QGroupBox(title)
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["PID", "USER", "NAME", "CPU%", "MEM%"])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)

        l = QVBoxLayout(gb)
        l.addWidget(table)
        return gb, table

    def set_data(self, result: CollectorResult[PerformanceData]) -> None:
        d = result.data
        self.cpu_total.setText(f"{d.cpu_total_percent:.1f}%")
        self.mem.setText(f"{d.memory.used_mb}/{d.memory.total_mb} MB ({d.memory.used_percent}%)")
        self.swap.setText(f"{d.swap.used_mb}/{d.swap.total_mb} MB ({d.swap.used_percent}%)")
        self.load.setText(f"{d.load.load1:.2f}, {d.load.load5:.2f}, {d.load.load15:.2f}")

        self._fill_cores(self.cpu_cores[1], d.cpu_cores)
        self._fill_procs(self.processes[1], d.processes)

    def _fill_cores(self, table: QTableWidget, cores: list[CpuCoreUsage]) -> None:
        table.setRowCount(len(cores))
        for r, c in enumerate(cores):
            table.setItem(r, 0, QTableWidgetItem(c.core))
            table.setItem(r, 1, NumericItem(f"{c.percent:.1f}", c.percent))
        table.resizeColumnsToContents()

    def _fill_procs(self, table: QTableWidget, procs: list[ProcessStat]) -> None:
        sort_col = table.horizontalHeader().sortIndicatorSection()
        sort_order = table.horizontalHeader().sortIndicatorOrder()

        table.setSortingEnabled(False)
        table.setRowCount(len(procs))
        for r, p in enumerate(procs):
            table.setItem(r, 0, NumericItem(str(p.pid), float(p.pid)))
            table.setItem(r, 1, QTableWidgetItem(p.user))
            table.setItem(r, 2, QTableWidgetItem(p.name))
            table.setItem(r, 3, NumericItem(f"{p.cpu_percent:.1f}", p.cpu_percent))
            table.setItem(r, 4, NumericItem(f"{p.mem_percent:.1f}", p.mem_percent))
        table.resizeColumnsToContents()

        table.setSortingEnabled(True)
        table.sortItems(sort_col, sort_order)