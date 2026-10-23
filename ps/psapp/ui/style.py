APP_STYLE = """
QWidget {
    background: #1e1f22;
    color: #e6e6e6;
    font-size: 13px;
}
QMainWindow, QDialog {
    background: #1e1f22;
}
QLabel {
    background: transparent;
}
QLabel#PanelTitle {
    font-size: 15px;
    font-weight: 600;
    color: #ffffff;
}
QLabel#SectionTitle {
    color: #9aa0a6;
    font-size: 12px;
}
QLabel#CostLabel {
    color: #9aa0a6;
}
QToolBar {
    background: #232529;
    border: none;
    spacing: 3px;
    padding: 5px;
}
QToolBar::separator {
    background: #3a3d44;
    width: 1px;
    margin: 4px;
}
QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px 7px;
    color: #d8dadd;
}
QToolButton:hover {
    background: #2f3237;
}
QToolButton:checked {
    background: #2f6fed;
    color: #ffffff;
}
QPushButton {
    background: #2f3237;
    border: 1px solid #3a3d44;
    border-radius: 6px;
    padding: 6px 12px;
    color: #e6e6e6;
}
QPushButton:hover {
    background: #383c42;
}
QPushButton:disabled {
    color: #6b7280;
    background: #26282c;
}
QPushButton#PrimaryButton {
    background: #4f8cff;
    border: none;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#PrimaryButton:hover {
    background: #6aa0ff;
}
QPushButton#PrimaryButton:disabled {
    background: #2f3b55;
    color: #9aa0a6;
}
QLineEdit, QPlainTextEdit, QTextBrowser, QListWidget, QSpinBox,
QDoubleSpinBox, QComboBox {
    background: #2b2d31;
    border: 1px solid #3a3d44;
    border-radius: 6px;
    padding: 4px 6px;
    selection-background-color: #2f6fed;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextBrowser:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #4f8cff;
}
QListWidget::item:selected {
    background: #2f3b55;
    border-radius: 4px;
}
QListWidget {
    outline: none;
}
QTextBrowser {
    border: none;
    background: #202226;
}
QSplitter::handle {
    background: #2b2d31;
}
QStatusBar {
    background: #232529;
    color: #9aa0a6;
}
QStatusBar::item {
    border: none;
}
QMenuBar {
    background: #232529;
}
QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
}
QMenuBar::item:selected {
    background: #2f3237;
    border-radius: 4px;
}
QMenu {
    background: #26282c;
    border: 1px solid #3a3d44;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #2f6fed;
}
QScrollBar:vertical {
    background: #1e1f22;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3a3d44;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: #4a4e56;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #1e1f22;
    height: 10px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #3a3d44;
    border-radius: 5px;
    min-width: 28px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QProgressBar {
    background: #2b2d31;
    border: 1px solid #3a3d44;
    border-radius: 5px;
    text-align: center;
    color: #e6e6e6;
}
QProgressBar::chunk {
    background: #4f8cff;
    border-radius: 4px;
}
QCheckBox, QRadioButton {
    spacing: 6px;
}
QGroupBox {
    border: 1px solid #3a3d44;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #9aa0a6;
}
"""
