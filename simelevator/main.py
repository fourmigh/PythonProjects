from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from gui.window import MainWindow
from i18n import tr


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle(tr("app.title"))
    window.showFullScreen()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
