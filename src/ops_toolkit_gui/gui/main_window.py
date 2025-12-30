from __future__ import annotations

from typing import Any

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from ops_toolkit_gui.core.collectors.performance import PerformanceCollector
from ops_toolkit_gui.core.collectors.user_activity import UserActivityCollector
from ops_toolkit_gui.core.collectors.filesystem import FilesystemCollector
from ops_toolkit_gui.core.models.common import CollectorResult
from ops_toolkit_gui.core.models.performance import PerformanceData
from ops_toolkit_gui.gui.pages.overview_page import OverviewPage
from ops_toolkit_gui.gui.pages.activity_page import ActivityPage
from ops_toolkit_gui.gui.pages.filesystem_page import FilesystemPage
from ops_toolkit_gui.gui.pages.performance_page import PerformancePage
from ops_toolkit_gui.gui.workers import Worker, WorkerJob


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ops Toolkit GUI")
        self.resize(1100, 720)

        self._thread_pool = QThreadPool.globalInstance()
        self._req_id = 0
        self._active_workers: set[Worker] = set()

        self._perf_collector = PerformanceCollector()
        self._activity_collector = UserActivityCollector()
        self._fs_config: dict[str, object] = {
            "scan_dir": "/",
            "target_dir": "/var",
            "large_file_mb": 200,
            "timeout_s": 8,
        }
        self._fs_collector = self._build_fs_collector(self._fs_config)

        self._nav = QTreeWidget()
        self._nav.setHeaderHidden(True)

        self._pages = QStackedWidget()
        self._overview = OverviewPage()
        self._performance = PerformancePage()
        self._activity = ActivityPage()
        self._filesystem = FilesystemPage()

        self._pages.addWidget(self._overview)
        self._pages.addWidget(self._performance)
        self._pages.addWidget(self._activity)
        self._pages.addWidget(self._filesystem)

        self._nav_items: dict[str, int] = {
            "Overview": 0,
            "Performance": 1,
            "Activity": 2,
            "Filesystem": 3,
        }
        for title in self._nav_items.keys():
            self._nav.addTopLevelItem(QTreeWidgetItem([title]))
        self._nav.setCurrentItem(self._nav.topLevelItem(0))

        splitter = QSplitter()
        splitter.addWidget(self._nav)
        splitter.addWidget(self._pages)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self.statusBar().showMessage("Ready")

        self._nav.currentItemChanged.connect(self._on_nav_changed)  # type: ignore[arg-type]

        self._filesystem.applyRequested.connect(self._on_filesystem_apply)  # type: ignore[arg-type]

        self._perf_timer = QTimer(self)
        self._perf_timer.setInterval(3000)
        self._perf_timer.timeout.connect(self.refresh_performance)  # type: ignore[arg-type]
        self._perf_timer.start()

        self._activity_timer = QTimer(self)
        self._activity_timer.setInterval(10000)
        self._activity_timer.timeout.connect(self.refresh_activity)  # type: ignore[arg-type]
        self._activity_timer.start()

        self._fs_timer = QTimer(self)
        self._fs_timer.setInterval(60000)
        self._fs_timer.timeout.connect(self.refresh_filesystem)  # type: ignore[arg-type]
        self._fs_timer.start()

        self.refresh_performance()
        self.refresh_activity()
        self.refresh_filesystem()

    def _build_fs_collector(self, cfg: dict[str, object]) -> FilesystemCollector:
        scan_dir = str(cfg.get("scan_dir") or "/")
        target_dir = str(cfg.get("target_dir") or "/var")
        large_file_mb = int(cfg.get("large_file_mb") or 200)
        timeout_s = int(cfg.get("timeout_s") or 8)

        # Use one timeout for both heavy scans.
        return FilesystemCollector(
            scan_dir=scan_dir,
            target_dir=target_dir,
            large_file_mb=large_file_mb,
            large_file_timeout_s=timeout_s,
            dir_timeout_s=timeout_s,
        )

    def _on_filesystem_apply(self, cfg: dict) -> None:
        self._fs_config.update(cfg)
        self._fs_collector = self._build_fs_collector(self._fs_config)
        self.statusBar().showMessage(
            f"Filesystem config applied: scan_dir={self._fs_config.get('scan_dir')} large_mb={self._fs_config.get('large_file_mb')} target_dir={self._fs_config.get('target_dir')} timeout={self._fs_config.get('timeout_s')}s"
        )
        self.refresh_filesystem()

    def _on_nav_changed(self, current: QTreeWidgetItem | None, _prev: QTreeWidgetItem | None) -> None:
        if current is None:
            return
        title = current.text(0)
        idx = self._nav_items.get(title)
        if idx is not None:
            self._pages.setCurrentIndex(idx)

    def refresh_performance(self) -> None:
        self._req_id += 1
        req_id = self._req_id

        def job() -> CollectorResult[PerformanceData]:
            return self._perf_collector.collect()

        w = Worker(WorkerJob(fn=job))
        self._active_workers.add(w)
        w.signals.result.connect(lambda r, _w=w: self._on_perf_result(req_id, r))  # type: ignore[arg-type]
        w.signals.error.connect(lambda m, _w=w: self._on_worker_error(m))  # type: ignore[arg-type]
        w.signals.finished.connect(lambda _w=w: self._active_workers.discard(_w))  # type: ignore[arg-type]
        self._thread_pool.start(w)

    def refresh_activity(self) -> None:
        self._req_id += 1
        req_id = self._req_id

        def job() -> object:
            return self._activity_collector.collect()

        w = Worker(WorkerJob(fn=job))
        self._active_workers.add(w)
        w.signals.result.connect(lambda r, _w=w: self._on_activity_result(req_id, r))  # type: ignore[arg-type]
        w.signals.error.connect(lambda m, _w=w: self._on_worker_error(m))  # type: ignore[arg-type]
        w.signals.finished.connect(lambda _w=w: self._active_workers.discard(_w))  # type: ignore[arg-type]
        self._thread_pool.start(w)

    def _on_activity_result(self, req_id: int, res: Any) -> None:
        if req_id != self._req_id:
            return
        if not isinstance(res, CollectorResult):
            return
        try:
            self._activity.set_data(res)
        except Exception as e:  # noqa: BLE001
            self._on_worker_error(str(e))

    def refresh_filesystem(self) -> None:
        self._req_id += 1
        req_id = self._req_id

        def job() -> object:
            return self._fs_collector.collect()

        w = Worker(WorkerJob(fn=job))
        self._active_workers.add(w)
        w.signals.result.connect(lambda r, _w=w: self._on_filesystem_result(req_id, r))  # type: ignore[arg-type]
        w.signals.error.connect(lambda m, _w=w: self._on_worker_error(m))  # type: ignore[arg-type]
        w.signals.finished.connect(lambda _w=w: self._active_workers.discard(_w))  # type: ignore[arg-type]
        self._thread_pool.start(w)

    def _on_filesystem_result(self, req_id: int, res: Any) -> None:
        if req_id != self._req_id:
            return
        if not isinstance(res, CollectorResult):
            return
        try:
            self._filesystem.set_data(res)
        except Exception as e:  # noqa: BLE001
            self._on_worker_error(str(e))

    def _on_perf_result(self, req_id: int, res: Any) -> None:
        if req_id != self._req_id:
            return
        if not isinstance(res, CollectorResult):
            return

        try:
            perf_res: CollectorResult[PerformanceData] = res
            self._overview.set_performance(perf_res)
            self._performance.set_data(perf_res)

            self.statusBar().showMessage(
                f"Updated: {perf_res.ts.strftime('%F %T')} | Status: {perf_res.status} | Warnings: {perf_res.warning_count}"
            )
        except Exception as e:  # noqa: BLE001
            self._on_worker_error(str(e))

    def _on_worker_error(self, msg: str) -> None:
        # Avoid frequent modal dialogs during periodic refresh.
        self.statusBar().showMessage(f"Error: {msg}")
