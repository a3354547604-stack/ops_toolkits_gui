from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ops_toolkit_gui.core.models.common import CollectorResult
from ops_toolkit_gui.core.models.filesystem import DirUsage, FilesystemData, LargeFile, MountUsage, PermCheck


def _human_bytes(n: int) -> str:
    v = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if v < 1024.0:
            return f"{v:.1f}{unit}" if unit != "B" else f"{int(v)}B"
        v /= 1024.0
    return f"{v:.1f}PB"


class FilesystemPage(QWidget):
    applyRequested = Signal(dict)

    def __init__(self) -> None:
        super().__init__()

        self._status = QLabel("-")
        self._notes = QLabel("")
        self._notes.setWordWrap(True)
        self._status.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self._scan_dir = QLineEdit("/")
        self._target_dir = QLineEdit("/var")
        self._large_mb = QSpinBox()
        self._large_mb.setRange(1, 102400)
        self._large_mb.setValue(200)
        self._timeout_s = QSpinBox()
        self._timeout_s.setRange(1, 120)
        self._timeout_s.setValue(8)

        apply_btn = QPushButton("Apply & Refresh")
        apply_btn.clicked.connect(self._on_apply_clicked)  # type: ignore[arg-type]

        cfg = QGroupBox("Scan Config")
        cfg_grid = QGridLayout(cfg)
        cfg_grid.addWidget(QLabel("Scan Dir"), 0, 0)
        cfg_grid.addWidget(self._scan_dir, 0, 1)
        cfg_grid.addWidget(QLabel("Large File (MB)"), 1, 0)
        cfg_grid.addWidget(self._large_mb, 1, 1)
        cfg_grid.addWidget(QLabel("Target Dir"), 2, 0)
        cfg_grid.addWidget(self._target_dir, 2, 1)
        cfg_grid.addWidget(QLabel("Timeout (s)"), 3, 0)
        cfg_grid.addWidget(self._timeout_s, 3, 1)

        cfg_row = QHBoxLayout()
        cfg_row.addWidget(cfg)
        cfg_row.addStretch(1)
        cfg_row.addWidget(apply_btn)

        metrics = QGroupBox("Filesystem Summary")
        grid = QGridLayout(metrics)
        grid.addWidget(QLabel("Status"), 0, 0)
        grid.addWidget(self._status, 0, 1)
        grid.addWidget(QLabel("Notes"), 1, 0)
        grid.addWidget(self._notes, 1, 1)

        self._mounts = self._make_table("Disk Usage (Mounts)", ["DEVICE", "MOUNT", "FSTYPE", "TOTAL(GB)", "USED(GB)", "FREE(GB)", "USED%"], 7)
        self._large = self._make_table("Large Files (scan)", ["SIZE", "PATH"], 2)
        self._dirs = self._make_table("Directory Size Sort (target)", ["SIZE", "PATH"], 2)
        self._perms = self._make_table("Permission Security Checks", ["PATH", "MODE", "OWNER", "GROUP", "OK", "MESSAGE"], 6)

        layout = QVBoxLayout(self)
        layout.addLayout(cfg_row)
        layout.addWidget(metrics)
        layout.addWidget(self._mounts[0])
        layout.addWidget(self._large[0])
        layout.addWidget(self._dirs[0])
        layout.addWidget(self._perms[0])
        layout.addStretch(1)

    def _on_apply_clicked(self) -> None:
        scan_dir = self._scan_dir.text().strip() or "/"
        target_dir = self._target_dir.text().strip() or "/var"
        cfg = {
            "scan_dir": scan_dir,
            "large_file_mb": int(self._large_mb.value()),
            "target_dir": target_dir,
            "timeout_s": int(self._timeout_s.value()),
        }
        self.applyRequested.emit(cfg)

    def _make_table(self, title: str, headers: list[str], cols: int) -> tuple[QGroupBox, QTableWidget]:
        gb = QGroupBox(title)
        t = QTableWidget(0, cols)
        t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setAlternatingRowColors(True)
        t.horizontalHeader().setStretchLastSection(True)
        l = QVBoxLayout(gb)
        l.addWidget(t)
        return gb, t

    def set_data(self, result: CollectorResult[FilesystemData]) -> None:
        d = result.data
        self._status.setText(str(result.status))
        self._notes.setText("\n".join(d.notes) if d.notes else "")

        self._fill_mounts(self._mounts[1], d.mounts)
        self._fill_large(self._large[1], d.large_files)
        self._fill_dirs(self._dirs[1], d.dir_usages)
        self._fill_perms(self._perms[1], d.perm_checks)

    def _fill_mounts(self, t: QTableWidget, rows: list[MountUsage]) -> None:
        t.setRowCount(len(rows))
        for r, m in enumerate(rows):
            t.setItem(r, 0, QTableWidgetItem(m.device))
            t.setItem(r, 1, QTableWidgetItem(m.mountpoint))
            t.setItem(r, 2, QTableWidgetItem(m.fstype))
            t.setItem(r, 3, QTableWidgetItem(f"{m.total_gb:.2f}"))
            t.setItem(r, 4, QTableWidgetItem(f"{m.used_gb:.2f}"))
            t.setItem(r, 5, QTableWidgetItem(f"{m.free_gb:.2f}"))
            t.setItem(r, 6, QTableWidgetItem(str(m.used_percent)))
        t.resizeColumnsToContents()

    def _fill_large(self, t: QTableWidget, rows: list[LargeFile]) -> None:
        t.setRowCount(len(rows))
        for r, f in enumerate(rows):
            t.setItem(r, 0, QTableWidgetItem(_human_bytes(f.size_bytes)))
            t.setItem(r, 1, QTableWidgetItem(f.path))
        t.resizeColumnsToContents()

    def _fill_dirs(self, t: QTableWidget, rows: list[DirUsage]) -> None:
        t.setRowCount(len(rows))
        for r, d in enumerate(rows):
            t.setItem(r, 0, QTableWidgetItem(_human_bytes(d.size_bytes)))
            t.setItem(r, 1, QTableWidgetItem(d.path))
        t.resizeColumnsToContents()

    def _fill_perms(self, t: QTableWidget, rows: list[PermCheck]) -> None:
        t.setRowCount(len(rows))
        for r, c in enumerate(rows):
            t.setItem(r, 0, QTableWidgetItem(c.path))
            t.setItem(r, 1, QTableWidgetItem(c.mode_octal))
            t.setItem(r, 2, QTableWidgetItem(c.owner))
            t.setItem(r, 3, QTableWidgetItem(c.group))
            t.setItem(r, 4, QTableWidgetItem("YES" if c.ok else "NO"))
            t.setItem(r, 5, QTableWidgetItem(c.message))
        t.resizeColumnsToContents()
