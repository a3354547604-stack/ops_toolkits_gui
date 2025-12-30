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

from ops_toolkit_gui.core.models.common import CollectorResult
from ops_toolkit_gui.core.models.user_activity import OnlineUser, SudoEvent, UserActivityData


class ActivityPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._status = QLabel("-")
        self._succ = QLabel("-")
        self._fail = QLabel("-")
        self._sudo_users = QLabel("-")
        self._notes = QLabel("")
        self._notes.setWordWrap(True)

        for lbl in (self._status, self._succ, self._fail, self._sudo_users):
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        metrics = QGroupBox("Activity Summary")
        grid = QGridLayout(metrics)
        grid.addWidget(QLabel("Status"), 0, 0)
        grid.addWidget(self._status, 0, 1)
        grid.addWidget(QLabel("Login Success (tail)"), 1, 0)
        grid.addWidget(self._succ, 1, 1)
        grid.addWidget(QLabel("Login Failed (tail)"), 2, 0)
        grid.addWidget(self._fail, 2, 1)
        grid.addWidget(QLabel("Sudo Users"), 3, 0)
        grid.addWidget(self._sudo_users, 3, 1)
        grid.addWidget(QLabel("Notes"), 4, 0)
        grid.addWidget(self._notes, 4, 1)

        self._online = self._make_online_table()
        self._sudo = self._make_sudo_table()
        self._abnormal = self._make_text_box("Abnormal Login Time Hits (raw lines, top20)")
        self._rare_ips = self._make_text_box("Rare Login IPs (seen once, top10)")

        layout = QVBoxLayout(self)
        layout.addWidget(metrics)
        layout.addWidget(self._online[0])
        layout.addWidget(self._sudo[0])
        layout.addWidget(self._abnormal[0])
        layout.addWidget(self._rare_ips[0])
        layout.addStretch(1)

    def _make_online_table(self) -> tuple[QGroupBox, QTableWidget]:
        gb = QGroupBox("Current Online Users")
        t = QTableWidget(0, 4)
        t.setHorizontalHeaderLabels(["USER", "TTY", "LOGIN_TIME", "SOURCE"]) 
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setAlternatingRowColors(True)
        t.horizontalHeader().setStretchLastSection(True)
        l = QVBoxLayout(gb)
        l.addWidget(t)
        return gb, t

    def _make_sudo_table(self) -> tuple[QGroupBox, QTableWidget]:
        gb = QGroupBox("Recent Sudo Commands (tail window)")
        t = QTableWidget(0, 3)
        t.setHorizontalHeaderLabels(["TIME", "USER", "COMMAND"]) 
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setAlternatingRowColors(True)
        t.horizontalHeader().setStretchLastSection(True)
        l = QVBoxLayout(gb)
        l.addWidget(t)
        return gb, t

    def _make_text_box(self, title: str) -> tuple[QGroupBox, QLabel]:
        gb = QGroupBox(title)
        lbl = QLabel("(none)")
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setWordWrap(True)
        l = QVBoxLayout(gb)
        l.addWidget(lbl)
        return gb, lbl

    def set_data(self, result: CollectorResult[UserActivityData]) -> None:
        d = result.data
        self._status.setText(str(result.status))
        self._succ.setText(str(d.login_success_last_24h))
        self._fail.setText(str(d.login_failed_last_24h))
        self._sudo_users.setText(", ".join(d.sudo_users) if d.sudo_users else "(none)")
        self._notes.setText("\n".join(d.notes) if d.notes else "")

        self._fill_online(self._online[1], d.online_users)
        self._fill_sudo(self._sudo[1], d.recent_sudo_events_last_24h)
        self._abnormal[1].setText("\n".join(d.abnormal_login_times_last_7d) if d.abnormal_login_times_last_7d else "(none)")
        self._rare_ips[1].setText(", ".join(d.rare_login_ips_last_7d) if d.rare_login_ips_last_7d else "(none)")

    def _fill_online(self, t: QTableWidget, rows: list[OnlineUser]) -> None:
        t.setRowCount(len(rows))
        for r, u in enumerate(rows):
            t.setItem(r, 0, QTableWidgetItem(u.user))
            t.setItem(r, 1, QTableWidgetItem(u.tty))
            t.setItem(r, 2, QTableWidgetItem(u.login_time))
            t.setItem(r, 3, QTableWidgetItem(u.source))
        t.resizeColumnsToContents()

    def _fill_sudo(self, t: QTableWidget, rows: list[SudoEvent]) -> None:
        t.setRowCount(len(rows))
        for r, e in enumerate(rows):
            t.setItem(r, 0, QTableWidgetItem(e.time))
            t.setItem(r, 1, QTableWidgetItem(e.user))
            t.setItem(r, 2, QTableWidgetItem(e.command))
        t.resizeColumnsToContents()
