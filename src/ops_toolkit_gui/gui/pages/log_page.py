from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ops_toolkit_gui.models.common import CollectorResult
from ops_toolkit_gui.models.logs import LogData, LogKeywordHit


class LogPage(QWidget):
    applyRequested = Signal(dict)

    def __init__(self) -> None:
        super().__init__()

        self._status = QLabel("-")
        self._status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._pos = QLabel("-")
        self._pos.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._notes = QLabel("")
        self._notes.setWordWrap(True)

        self._path = QLineEdit("/var/log/syslog")
        self._keywords = QLineEdit("ERROR,Failed,Warning")
        self._max_mb = QSpinBox()
        self._max_mb.setRange(1, 102400)
        self._max_mb.setValue(10)
        self._keep = QSpinBox()
        self._keep.setRange(1, 200)
        self._keep.setValue(5)

        apply_btn = QPushButton("Apply / Refresh")
        apply_btn.clicked.connect(self._on_apply_clicked)  # type: ignore[arg-type]

        cfg = QGroupBox("Log Config")
        cfg_grid = QGridLayout(cfg)
        cfg_grid.addWidget(QLabel("Log Path"), 0, 0)
        cfg_grid.addWidget(self._path, 0, 1)
        cfg_grid.addWidget(QLabel("Keywords (comma)"), 1, 0)
        cfg_grid.addWidget(self._keywords, 1, 1)
        cfg_grid.addWidget(QLabel("Rotate Max (MB)"), 2, 0)
        cfg_grid.addWidget(self._max_mb, 2, 1)
        cfg_grid.addWidget(QLabel("Keep Archives"), 3, 0)
        cfg_grid.addWidget(self._keep, 3, 1)

        cfg_row = QHBoxLayout()
        cfg_row.addWidget(cfg)
        cfg_row.addStretch(1)
        cfg_row.addWidget(apply_btn)

        summary = QGroupBox("Log Summary")
        grid = QGridLayout(summary)
        grid.addWidget(QLabel("Status"), 0, 0)
        grid.addWidget(self._status, 0, 1)
        grid.addWidget(QLabel("Last Pos"), 1, 0)
        grid.addWidget(self._pos, 1, 1)
        grid.addWidget(QLabel("Notes"), 2, 0)
        grid.addWidget(self._notes, 2, 1)

        self._hits = QTableWidget(0, 2)
        self._hits.setHorizontalHeaderLabels(["KEYWORD", "COUNT"])
        self._hits.horizontalHeader().setStretchLastSection(True)
        self._hits.setAlternatingRowColors(True)
        self._hits.verticalHeader().setVisible(False)

        hits_box = QGroupBox("Keyword Hits (new lines)")
        hits_l = QVBoxLayout(hits_box)
        hits_l.addWidget(self._hits)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        lines_box = QGroupBox("New Lines")
        lines_l = QVBoxLayout(lines_box)
        lines_l.addWidget(self._log_text)

        layout = QVBoxLayout(self)
        layout.addLayout(cfg_row)
        layout.addWidget(summary)
        layout.addWidget(hits_box, 1)
        layout.addWidget(lines_box, 3)

    def _on_apply_clicked(self) -> None:
        path = self._path.text().strip() or "/var/log/syslog"
        keywords_raw = self._keywords.text().strip()
        self._keywords.setCursorPosition(0)
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        self.applyRequested.emit(
            {
                "path": path,
                "keywords": keywords,
                "rotate_max_mb": int(self._max_mb.value()),
                "rotate_keep_archives": int(self._keep.value()),
            }
        )

    def set_data(self, result: CollectorResult[LogData]) -> None:
        d = result.data
        self._status.setText(str(result.status))
        self._pos.setText(str(d.last_read_pos))
        self._notes.setText("\n".join(d.notes) if d.notes else "")

        self._keywords.setCursorPosition(0)

        self._fill_hits(d.keyword_hits)
        self._append_lines(d.path, d.new_lines)

    def _fill_hits(self, rows: list[LogKeywordHit]) -> None:
        self._hits.setRowCount(len(rows))
        for r, h in enumerate(rows):
            self._hits.setItem(r, 0, QTableWidgetItem(h.keyword))
            self._hits.setItem(r, 1, QTableWidgetItem(str(h.count)))
        self._hits.resizeColumnsToContents()

    def _append_lines(self, path: str, lines: list[str]) -> None:
        if not lines:
            return
        header = f"[{path}] +{len(lines)} lines"
        self._log_text.append(header)
        for line in lines:
            self._log_text.append(line)

        doc = self._log_text.document()
        if doc.blockCount() > 2000:
            cursor = self._log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
