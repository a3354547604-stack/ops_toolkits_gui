import faulthandler
import sys

from PySide6.QtWidgets import QApplication

from ops_toolkit_gui.gui.main_window import MainWindow


def run() -> None:
    faulthandler.enable()
    app = QApplication(sys.argv)
    app.setApplicationName("Ops Toolkit GUI")

    w = MainWindow()
    w.show()

    raise SystemExit(app.exec())
