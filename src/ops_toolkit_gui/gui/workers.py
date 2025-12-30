from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


@dataclass(frozen=True)
class WorkerJob:
    fn: Callable[[], Any]


class Worker(QRunnable):
    def __init__(self, job: WorkerJob) -> None:
        super().__init__()
        self.job = job
        self.signals = WorkerSignals()
        self.setAutoDelete(False)

    @Slot()
    def run(self) -> None:
        try:
            res = self.job.fn()
            self.signals.result.emit(res)
        except Exception as e:  # noqa: BLE001
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()
