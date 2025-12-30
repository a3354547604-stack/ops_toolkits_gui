from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QGridLayout, QGroupBox, QHBoxLayout, QWidget

from ops_toolkit_gui.core.models.common import CollectorResult
from ops_toolkit_gui.core.models.performance import PerformanceData


class OverviewPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._last_update = QLabel("Last Update: -")
        self._perf_status = QLabel("Performance: -")
        self._perf_summary = QLabel("CPU: - | MEM: - | LOAD1: -")
        self._warnings = QLabel("Warnings: -")

        self._perf_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._perf_summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._warnings.setTextInteractionFlags(Qt.TextSelectableByMouse)

        gb = QGroupBox("Overview")
        grid = QGridLayout(gb)
        grid.addWidget(self._last_update, 0, 0, 1, 2)
        grid.addWidget(self._perf_status, 1, 0, 1, 2)
        grid.addWidget(self._perf_summary, 2, 0, 1, 2)
        grid.addWidget(self._warnings, 3, 0, 1, 2)

        root = QHBoxLayout(self)
        root.addWidget(gb)
        root.addStretch(1)

    def set_performance(self, result: CollectorResult[PerformanceData]) -> None:
        ts = result.ts.strftime("%F %T") if isinstance(result.ts, datetime) else str(result.ts)
        self._last_update.setText(f"Last Update: {ts}")
        self._perf_status.setText(f"Performance: {result.status}")
        self._perf_summary.setText(
            f"CPU: {result.data.cpu_total_percent:.1f}% | "
            f"MEM: {result.data.memory.used_percent}% | "
            f"LOAD1: {result.data.load.load1:.2f}"
        )
        self._warnings.setText(f"Warnings: {result.warning_count}")
