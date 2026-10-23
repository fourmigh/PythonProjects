from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from psapp.ui.main_window import MainWindow
from psapp.ui.style import APP_STYLE


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PS Studio")
    app.setOrganizationName("fourmigh")
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
