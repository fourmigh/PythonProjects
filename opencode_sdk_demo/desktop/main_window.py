import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QMenuBar, QMenu,
    QStatusBar, QMessageBox, QToolBar, QFrame,
)
from PySide6.QtGui import QAction, QColor, QPalette

from desktop.output_panel import OutputPanel
from desktop.demo_tree import DemoTreeWidget
from desktop.demo_worker import DemoWorker
from desktop.service_manager import ServiceManager


class StatusIndicator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self.set_offline()

    def set_online(self):
        self.setStyleSheet("background-color: #27ae60; border-radius: 6px;")

    def set_offline(self):
        self.setStyleSheet("background-color: #e74c3c; border-radius: 6px;")

    def set_warning(self):
        self.setStyleSheet("background-color: #f39c12; border-radius: 6px;")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Opencode SDK Demo")
        self.resize(1100, 720)

        self._service = ServiceManager(self)
        self._service.status_changed.connect(self._on_service_status)
        self._worker = None

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()

        QTimer = __import__("PySide6.QtCore", fromlist=["QTimer"]).QTimer
        QTimer.singleShot(500, self._auto_connect)

    def _setup_ui(self):
        splitter = QSplitter(Qt.Horizontal)
        self._demo_tree = DemoTreeWidget()
        self._demo_tree.demo_selected.connect(self._run_demo)
        self._output_panel = OutputPanel()

        splitter.addWidget(self._demo_tree)
        splitter.addWidget(self._output_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([280, 800])

        self.setCentralWidget(splitter)

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        act_quit = QAction("退出", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        tools_menu = menubar.addMenu("工具")
        self._act_toggle_service = QAction("启动服务", self)
        self._act_toggle_service.triggered.connect(self._toggle_service)
        tools_menu.addAction(self._act_toggle_service)
        tools_menu.addSeparator()
        act_clear = QAction("清空输出", self)
        act_clear.triggered.connect(self._output_panel.clear_output)
        tools_menu.addAction(act_clear)

        help_menu = menubar.addMenu("帮助")
        act_about = QAction("关于", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _setup_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._lbl_status = QLabel("服务状态: 检测中...")
        self._indicator = StatusIndicator()
        self._indicator.set_warning()

        toolbar.addWidget(self._indicator)
        toolbar.addWidget(self._lbl_status)
        toolbar.addSeparator()

        self._btn_toggle_service = QPushButton("启动服务")
        self._btn_toggle_service.clicked.connect(self._toggle_service)
        toolbar.addWidget(self._btn_toggle_service)
        toolbar.addSeparator()

        btn_clear = QPushButton("清空输出")
        btn_clear.clicked.connect(self._output_panel.clear_output)
        toolbar.addWidget(btn_clear)

        self._btn_stop_demo = QPushButton("终止运行")
        self._btn_stop_demo.clicked.connect(self._stop_demo)
        self._btn_stop_demo.setEnabled(False)
        toolbar.addWidget(self._btn_stop_demo)

    def _setup_statusbar(self):
        status = QStatusBar(self)
        self._status_label = QLabel("就绪")
        status.addPermanentWidget(self._status_label)
        self.setStatusBar(status)

    def _auto_connect(self):
        self._output_panel.append_text("[INFO] 正在检测 opencode 服务...")
        if self._service._ping():
            self._service._ready = True
            self._service._timer.start()
            self._on_service_status(True, "服务已就绪")
        else:
            self._output_panel.append_text('[INFO] 服务未运行，点击"启动服务"按钮启动')
            self._on_service_status(False, "服务未连接")

    def _toggle_service(self):
        if self._service.ready:
            self._service.stop()
        else:
            self._output_panel.append_text("[INFO] 正在启动 opencode 服务...")
            self._status_label.setText("启动中...")
            success = self._service.start()
            if not success:
                self._output_panel.append_text("[FAIL] 服务启动失败")
            self._status_label.setText("就绪")

    def _on_service_status(self, ready, message):
        self._output_panel.append_text(message)
        if ready:
            self._indicator.set_online()
            self._lbl_status.setText("服务状态: 已连接")
            self._status_label.setText("已连接")
            self._btn_toggle_service.setText("停止服务")
            self._act_toggle_service.setText("停止服务")
        else:
            self._indicator.set_offline()
            self._lbl_status.setText(f"服务状态: {message}")
            self._status_label.setText(message)
            self._btn_toggle_service.setText("启动服务")
            self._act_toggle_service.setText("启动服务")

    def _run_demo(self, cat, name):
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "提示", "请等待当前 Demo 运行完毕")
            return

        self._output_panel.clear_output()
        self._output_panel.redirect_stdout()
        self._demo_tree.set_status(cat, name, "running")

        label = name.split("_", 1)[1] if "_" in name else name
        self._output_panel.append_text(f"--- 运行 {label} ({cat}) ---")

        self._worker = DemoWorker(cat, name)
        self._worker.demo_finished.connect(self._on_demo_finished)
        self._worker.started.connect(lambda: self._btn_stop_demo.setEnabled(True))
        self._worker.finished.connect(lambda: self._btn_stop_demo.setEnabled(False))
        self._worker.start()
        self._status_label.setText(f"运行中: {label}")

    def _on_demo_finished(self, success, err_msg):
        self._output_panel.restore_stdout()
        cat = self._worker._category
        name = self._worker._name
        if success:
            self._demo_tree.set_status(cat, name, "success")
            self._status_label.setText("完成")
        else:
            self._demo_tree.set_status(cat, name, "failed")
            self._status_label.setText(f"失败: {err_msg[:50]}")
        self._worker = None

    def _stop_demo(self):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(3000)
            self._output_panel.append_text("[INFO] Demo 已被用户终止")
            if self._worker:
                try:
                    self._output_panel.restore_stdout()
                except Exception:
                    pass
                self._worker = None
            self._status_label.setText("已终止")

    def _show_about(self):
        QMessageBox.about(self, "关于 Opencode SDK Demo",
            "Opencode SDK Python Demo\n\n"
            "一个展示 opencode-ai Python SDK 功能的示例集合，\n"
            "包含 22 个分类 Demo，覆盖基础连接到高级用法。\n\n"
            "技术栈: PySide6 / opencode-ai SDK")

    def closeEvent(self, event):
        self._service.stop()
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(3000)
        event.accept()
