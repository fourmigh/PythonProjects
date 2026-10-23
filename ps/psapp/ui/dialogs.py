from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from psapp.core.composite import hex_to_rgb, resize_to_fit, side_by_side

from .canvas import pil_to_qimage


def show_image_dialog(
    parent: QWidget | None,
    image: Image.Image,
    title: str,
    max_size: tuple[int, int] = (1140, 760),
) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout(dialog)

    preview = image.copy()
    preview.thumbnail(max_size, Image.LANCZOS)
    label = QLabel()
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setPixmap(QPixmap.fromImage(pil_to_qimage(preview)))
    layout.addWidget(label)

    hint = QLabel("左：原图    右：当前结果")
    hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
    hint.setObjectName("SectionTitle")
    layout.addWidget(hint)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.exec()


class CompareDialog(QDialog):
    def __init__(
        self,
        original: Image.Image,
        current: Image.Image,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("原图 / 结果对比")
        layout = QVBoxLayout(self)
        combined = side_by_side(
            resize_to_fit(original, 1200), resize_to_fit(current, 1200)
        )
        combined.thumbnail((1140, 760), Image.LANCZOS)
        label = QLabel()
        label.setPixmap(QPixmap.fromImage(pil_to_qimage(combined)))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        hint = QLabel("左：原图    右：当前结果")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setObjectName("SectionTitle")
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class BackgroundDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择新背景")
        self.setMinimumWidth(480)
        self._color = "#ffffff"

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.white_radio = QRadioButton("白色背景")
        self.color_radio = QRadioButton("纯色背景")
        self.image_radio = QRadioButton("图片背景")
        self.white_radio.setChecked(True)
        self.group = QButtonGroup(self)
        for radio in (self.white_radio, self.color_radio, self.image_radio):
            self.group.addButton(radio)
            form.addRow(radio)

        self.color_button = QPushButton("选择颜色")
        self.color_button.clicked.connect(self._pick_color)
        self._update_color_button()
        form.addRow("颜色", self.color_button)

        image_row = QWidget()
        image_layout = QHBoxLayout(image_row)
        image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_edit = QLineEdit()
        self.image_edit.setPlaceholderText("选择一张背景图片")
        browse = QPushButton("浏览")
        browse.clicked.connect(self._pick_image)
        image_layout.addWidget(self.image_edit, 1)
        image_layout.addWidget(browse)
        form.addRow("图片", image_row)

        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_color_button(self) -> None:
        self.color_button.setStyleSheet(
            f"background: {self._color}; color: #111; border-radius: 6px;"
        )
        self.color_button.setText(self._color)

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "选择背景颜色")
        if color.isValid():
            self._color = color.name()
            self._update_color_button()
            self.color_radio.setChecked(True)

    def _pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择背景图片",
            "",
            "图片 (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if path:
            self.image_edit.setText(path)
            self.image_radio.setChecked(True)

    def _validate(self) -> None:
        if self.image_radio.isChecked():
            if not self.image_edit.text().strip():
                QMessageBox.warning(self, "背景", "请选择背景图片")
                return
            if not Path(self.image_edit.text().strip()).exists():
                QMessageBox.warning(self, "背景", "背景图片不存在")
                return
        self.accept()

    def is_image(self) -> bool:
        return self.image_radio.isChecked()

    def background_color(self) -> tuple[int, int, int]:
        if self.white_radio.isChecked():
            return (255, 255, 255)
        return hex_to_rgb(self._color)

    def background_image(self) -> Image.Image:
        image = Image.open(self.image_edit.text().strip())
        image.load()
        return image.convert("RGB")
