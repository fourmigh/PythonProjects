from __future__ import annotations

from pathlib import Path

import requests
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from psapp.config import AppConfig, save_config

MODELS = [
    "Qwen/Qwen-Image-Edit-2509",
    "Qwen/Qwen-Image-Edit",
]


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("设置")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)

        hint = QLabel(
            "API Key 仅保存在本次运行的内存中，不会写入磁盘。"
            "关闭程序后需要重新输入。"
        )
        hint.setWordWrap(True)
        hint.setObjectName("SectionTitle")
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(8)

        self.api_key = QLineEdit(config.api_key)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("sk-...")
        key_row = QWidget()
        key_layout = QHBoxLayout(key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(self.api_key, 1)
        link = QLabel(
            '<a href="https://cloud.siliconflow.cn/account/ak">获取 Key</a>'
        )
        link.setOpenExternalLinks(True)
        key_layout.addWidget(link)
        form.addRow("硅基流动 API Key", key_row)

        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.addItems(MODELS)
        self.model.setCurrentText(config.model)
        form.addRow("模型", self.model)

        self.output_dir = QLineEdit(config.output_dir)
        browse = QPushButton("浏览")
        browse.clicked.connect(self._browse_output)
        out_row = QWidget()
        out_layout = QHBoxLayout(out_row)
        out_layout.setContentsMargins(0, 0, 0, 0)
        out_layout.addWidget(self.output_dir, 1)
        out_layout.addWidget(browse)
        form.addRow("输出目录", out_row)

        self.base_url = QLineEdit(config.base_url)
        form.addRow("接口地址", self.base_url)

        self.candidates = QSpinBox()
        self.candidates.setRange(1, 4)
        self.candidates.setValue(config.candidates)
        form.addRow("默认候选数", self.candidates)

        self.steps = QSpinBox()
        self.steps.setRange(10, 60)
        self.steps.setValue(config.steps)
        form.addRow("默认步数", self.steps)

        self.cfg = QDoubleSpinBox()
        self.cfg.setRange(1.0, 10.0)
        self.cfg.setSingleStep(0.5)
        self.cfg.setValue(config.cfg)
        form.addRow("默认 CFG", self.cfg)

        self.feather = QSpinBox()
        self.feather.setRange(0, 40)
        self.feather.setValue(config.feather)
        form.addRow("选区羽化", self.feather)

        self.max_edge = QSpinBox()
        self.max_edge.setRange(512, 4096)
        self.max_edge.setSingleStep(128)
        self.max_edge.setValue(config.max_edge)
        form.addRow("上传最长边", self.max_edge)

        self.timeout = QSpinBox()
        self.timeout.setRange(30, 600)
        self.timeout.setValue(config.timeout)
        form.addRow("请求超时（秒）", self.timeout)

        self.proxy = QLineEdit(config.proxy)
        self.proxy.setPlaceholderText("例如 http://127.0.0.1:7890，留空直连")
        form.addRow("代理", self.proxy)

        self.paste_back = QCheckBox("局部编辑时只贴回选区（推荐）")
        self.paste_back.setChecked(config.paste_back)
        form.addRow("贴回", self.paste_back)

        self.rewrite_enabled = QCheckBox("发送前用智谱免费模型优化提示词")
        self.rewrite_enabled.setChecked(config.rewrite_enabled)
        form.addRow("提示词改写", self.rewrite_enabled)

        self.zhipu_api_key = QLineEdit(config.zhipu_api_key)
        self.zhipu_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.zhipu_api_key.setPlaceholderText("可选，用于提示词改写")
        form.addRow("智谱 API Key", self.zhipu_api_key)

        self.zhipu_model = QLineEdit(config.zhipu_model)
        form.addRow("智谱模型", self.zhipu_model)

        layout.addLayout(form)

        test_row = QHBoxLayout()
        test_button = QPushButton("测试硅基流动连接")
        test_button.clicked.connect(self._test_connection)
        clear_button = QPushButton("清空 Key 输入")
        clear_button.clicked.connect(self._clear_keys)
        test_row.addWidget(test_button)
        test_row.addWidget(clear_button)
        test_row.addStretch(1)
        layout.addLayout(test_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.output_dir.text()
        )
        if path:
            self.output_dir.setText(path)

    def _test_connection(self) -> None:
        api_key = self.api_key.text().strip()
        base_url = self.base_url.text().strip().rstrip("/")
        if not api_key:
            QMessageBox.warning(self, "测试连接", "请先填写 API Key")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            response = requests.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=20,
            )
            if response.status_code == 200:
                QMessageBox.information(self, "测试连接", "连接成功，API Key 有效")
            elif response.status_code in (401, 403):
                QMessageBox.warning(self, "测试连接", "API Key 无效或没有权限")
            else:
                QMessageBox.warning(
                    self,
                    "测试连接",
                    f"接口返回 HTTP {response.status_code}\n{response.text[:300]}",
                )
        except requests.RequestException as exc:
            QMessageBox.warning(self, "测试连接", f"连接失败：{exc}")
        finally:
            QApplication.restoreOverrideCursor()

    def _clear_keys(self) -> None:
        self.api_key.clear()
        self.zhipu_api_key.clear()

    def _save(self) -> None:
        self.config.api_key = self.api_key.text().strip()
        self.config.model = self.model.currentText().strip() or MODELS[0]
        self.config.base_url = (
            self.base_url.text().strip().rstrip("/") or "https://api.siliconflow.cn/v1"
        )
        self.config.output_dir = self.output_dir.text().strip()
        if not self.config.output_dir:
            self.config.output_dir = str(Path.cwd() / "outputs")
        self.config.candidates = self.candidates.value()
        self.config.steps = self.steps.value()
        self.config.cfg = float(self.cfg.value())
        self.config.feather = self.feather.value()
        self.config.max_edge = self.max_edge.value()
        self.config.timeout = self.timeout.value()
        self.config.proxy = self.proxy.text().strip()
        self.config.paste_back = self.paste_back.isChecked()
        self.config.rewrite_enabled = self.rewrite_enabled.isChecked()
        self.config.zhipu_api_key = self.zhipu_api_key.text().strip()
        self.config.zhipu_model = (
            self.zhipu_model.text().strip() or "glm-4-flash-250414"
        )
        save_config(self.config)
        self.accept()
