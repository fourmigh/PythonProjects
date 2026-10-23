from __future__ import annotations

import html

from PIL import Image
from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from psapp.config import AppConfig

from .canvas import pil_to_qimage


def make_thumbnail(image: Image.Image, size: int = 112) -> QPixmap:
    thumb = image.copy()
    thumb.thumbnail((size, size), Image.LANCZOS)
    return QPixmap.fromImage(pil_to_qimage(thumb))


class ChatPanel(QWidget):
    send_requested = Signal(str)
    candidate_selected = Signal(int)
    params_changed = Signal()

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setObjectName("ChatPanel")
        self.setMinimumWidth(330)
        self.setMaximumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("对话")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        self.log = QTextBrowser()
        self.log.setOpenExternalLinks(True)
        self.log.setObjectName("ChatLog")
        layout.addWidget(self.log, 1)

        self.candidate_label = QLabel("候选结果")
        self.candidate_label.setObjectName("SectionTitle")
        layout.addWidget(self.candidate_label)

        self.candidates = QListWidget()
        self.candidates.setViewMode(QListView.ViewMode.IconMode)
        self.candidates.setFlow(QListView.Flow.LeftToRight)
        self.candidates.setResizeMode(QListView.ResizeMode.Adjust)
        self.candidates.setMovement(QListView.Movement.Static)
        self.candidates.setIconSize(QSize(104, 104))
        self.candidates.setGridSize(QSize(124, 138))
        self.candidates.setFixedHeight(152)
        self.candidates.setSpacing(4)
        self.candidates.currentRowChanged.connect(self._on_candidate_row)
        self.candidate_label.hide()
        self.candidates.hide()
        layout.addWidget(self.candidates)

        params = QGridLayout()
        params.setHorizontalSpacing(8)
        params.setVerticalSpacing(6)

        self.candidates_spin = QSpinBox()
        self.candidates_spin.setRange(1, 4)
        self.candidates_spin.setValue(max(1, min(4, config.candidates)))
        self.candidates_spin.setToolTip("每次请求生成几张候选，每张约 ¥0.30")

        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(10, 60)
        self.steps_spin.setValue(max(10, min(60, config.steps)))

        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(1.0, 10.0)
        self.cfg_spin.setSingleStep(0.5)
        self.cfg_spin.setValue(max(1.0, min(10.0, config.cfg)))

        self.seed_edit = QLineEdit()
        self.seed_edit.setPlaceholderText("随机")

        params.addWidget(QLabel("候选"), 0, 0)
        params.addWidget(self.candidates_spin, 0, 1)
        params.addWidget(QLabel("步数"), 0, 2)
        params.addWidget(self.steps_spin, 0, 3)
        params.addWidget(QLabel("CFG"), 1, 0)
        params.addWidget(self.cfg_spin, 1, 1)
        params.addWidget(QLabel("Seed"), 1, 2)
        params.addWidget(self.seed_edit, 1, 3)
        layout.addLayout(params)

        self.input = QPlainTextEdit()
        self.input.setPlaceholderText(
            "输入修改指令，例如：把背景换成海边，保持人物不变（Ctrl+Enter 发送）"
        )
        self.input.setFixedHeight(78)
        self.input.installEventFilter(self)
        layout.addWidget(self.input)

        bottom = QHBoxLayout()
        self.cost_label = QLabel("累计 ¥0.00")
        self.cost_label.setObjectName("CostLabel")
        bottom.addWidget(self.cost_label, 1)
        self.send_button = QPushButton("发送")
        self.send_button.setObjectName("PrimaryButton")
        self.send_button.setMinimumWidth(88)
        self.send_button.clicked.connect(self._emit_send)
        bottom.addWidget(self.send_button)
        layout.addLayout(bottom)

        self.candidates_spin.valueChanged.connect(self._emit_params_changed)
        self.steps_spin.valueChanged.connect(self._emit_params_changed)
        self.cfg_spin.valueChanged.connect(self._emit_params_changed)
        self.seed_edit.textChanged.connect(self._emit_params_changed)

    def _emit_params_changed(self) -> None:
        self.params_changed.emit()

    def _on_candidate_row(self, row: int) -> None:
        if row >= 0:
            self.candidate_selected.emit(row)

    def _emit_send(self) -> None:
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.input.clear()
        self.send_requested.emit(text)

    def eventFilter(self, obj, event) -> bool:
        if (
            obj is self.input
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self._emit_send()
            return True
        return super().eventFilter(obj, event)

    def append_message(self, text: str, kind: str = "info") -> None:
        colors = {
            "user": "#8ab4ff",
            "info": "#9aa0a6",
            "success": "#7ee787",
            "error": "#ff7b72",
            "system": "#c9a0ff",
        }
        color = colors.get(kind, "#9aa0a6")
        safe = html.escape(text).replace("\n", "<br>")
        self.log.append(f'<div style="color:{color}; margin:3px 0;">{safe}</div>')
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.ensureCursorVisible()

    def set_busy(self, busy: bool) -> None:
        self.send_button.setDisabled(busy)
        self.send_button.setText("生成中…" if busy else "发送")
        self.input.setDisabled(busy)
        self.candidates_spin.setDisabled(busy)
        self.steps_spin.setDisabled(busy)
        self.cfg_spin.setDisabled(busy)
        self.seed_edit.setDisabled(busy)
        if busy:
            self.input.setPlaceholderText("正在生成，请稍候…")

    def set_candidates(self, images: list[Image.Image]) -> None:
        self.candidates.blockSignals(True)
        self.candidates.clear()
        for index, image in enumerate(images):
            item = QListWidgetItem(QIcon(make_thumbnail(image)), f"候选 {index + 1}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.candidates.addItem(item)
        self.candidates.setCurrentRow(0)
        self.candidates.blockSignals(False)
        visible = bool(images)
        self.candidate_label.setVisible(visible)
        self.candidates.setVisible(visible)

    def clear_candidates(self) -> None:
        self.candidates.blockSignals(True)
        self.candidates.clear()
        self.candidates.blockSignals(False)
        self.candidate_label.hide()
        self.candidates.hide()

    def set_cost(self, total: float) -> None:
        self.cost_label.setText(f"累计 ¥{total:.2f}")

    def params(self) -> dict:
        seed_text = self.seed_edit.text().strip()
        seed = int(seed_text) if seed_text.isdigit() else None
        if seed is not None:
            seed = min(seed, 9_999_999_999)
        return {
            "candidates": self.candidates_spin.value(),
            "steps": self.steps_spin.value(),
            "cfg": float(self.cfg_spin.value()),
            "seed": seed,
        }
