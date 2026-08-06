import sys
import pathlib

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from desktop.main_window import MainWindow


STYLE = """
QMainWindow {
    background-color: #1e1e1e;
}
QTreeWidget {
    background-color: #252526;
    color: #cccccc;
    border: none;
    font-size: 12px;
}
QTreeWidget::item {
    padding: 4px 0;
}
QTreeWidget::item:hover {
    background-color: #2a2d2e;
}
QTreeWidget::item:selected {
    background-color: #094771;
    color: #ffffff;
}
QPlainTextEdit {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: none;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
}
QToolBar {
    background-color: #333333;
    border: none;
    spacing: 6px;
    padding: 4px 8px;
}
QToolBar QPushButton {
    background-color: #0e639c;
    color: white;
    border: none;
    padding: 4px 12px;
    border-radius: 3px;
    font-size: 12px;
}
QToolBar QPushButton:hover {
    background-color: #1177bb;
}
QToolBar QPushButton:pressed {
    background-color: #094771;
}
QToolBar QLabel {
    color: #cccccc;
    font-size: 12px;
}
QMenuBar {
    background-color: #323233;
    color: #cccccc;
    border: none;
}
QMenuBar::item:selected {
    background-color: #094771;
}
QMenu {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #454545;
}
QMenu::item:selected {
    background-color: #094771;
}
QStatusBar {
    background-color: #007acc;
    color: white;
    font-size: 12px;
}
QSplitter::handle {
    background-color: #333333;
    width: 2px;
}
QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 10px;
}
QScrollBar::handle:vertical {
    background-color: #424242;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)

    icon_path = pathlib.Path(__file__).parent / "resources" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
