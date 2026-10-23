from __future__ import annotations

import io

from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget


def pil_to_qimage(image: Image.Image) -> QImage:
    image = image.convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(
        data, image.width, image.height, image.width * 4, QImage.Format.Format_RGBA8888
    )
    return qimage.copy()


class ImageCanvas(QWidget):
    mask_changed = Signal()
    zoom_changed = Signal(float)

    MODE_VIEW = "view"
    MODE_BRUSH = "brush"
    MODE_RECT = "rect"
    MODE_ERASE = "erase"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(False)

        self._image: Image.Image | None = None
        self._qimage = QImage()
        self._mask = QImage()
        self._overlay = QImage()
        self._zoom = 1.0
        self._offset = QPointF(0.0, 0.0)
        self._mode = self.MODE_VIEW
        self._brush_size = 36
        self._drawing = False
        self._panning = False
        self._fit_mode = True
        self._has_mask = False
        self._last_image_pos = QPointF()
        self._last_screen_pos = QPointF()
        self._rect_start = QPointF()
        self._rect_current = QPointF()
        self._hover_pos: QPointF | None = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    @property
    def image(self) -> Image.Image | None:
        return self._image

    @property
    def zoom(self) -> float:
        return self._zoom

    @property
    def mode(self) -> str:
        return self._mode

    def set_image(self, image: Image.Image, reset_mask: bool = True) -> None:
        self._image = image.convert("RGB")
        self._qimage = pil_to_qimage(self._image)
        if reset_mask or self._mask.size() != self._qimage.size():
            self._mask = QImage(
                self._qimage.width(),
                self._qimage.height(),
                QImage.Format.Format_Grayscale8,
            )
            self._mask.fill(0)
            self._overlay = QImage(
                self._qimage.width(),
                self._qimage.height(),
                QImage.Format.Format_ARGB32,
            )
            self._overlay.fill(QColor(0, 0, 0, 0))
            self._has_mask = False
        self._fit_mode = True
        self.fit_to_view()

    def set_mask_from_pil(self, mask: Image.Image) -> None:
        if self._image is None:
            return
        mask = mask.convert("L").resize(self._image.size)
        data = mask.tobytes()
        qimage = QImage(
            data, mask.width, mask.height, mask.width, QImage.Format.Format_Grayscale8
        )
        self._mask = qimage.copy()
        overlay = Image.new("RGBA", mask.size, (255, 64, 64, 0))
        overlay.putalpha(mask.point(lambda value: int(value * 0.45)))
        self._overlay = pil_to_qimage(overlay)
        self._has_mask = mask.getbbox() is not None
        self.update()
        self.mask_changed.emit()

    def get_mask_pil(self) -> Image.Image | None:
        if self._mask.isNull():
            return None
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        self._mask.save(buffer, "PNG")
        data = bytes(buffer.data())
        buffer.close()
        if not data:
            return None
        return Image.open(io.BytesIO(data)).convert("L")

    def clear_mask(self) -> None:
        if self._mask.isNull():
            return
        self._mask.fill(0)
        self._overlay.fill(QColor(0, 0, 0, 0))
        self._has_mask = False
        self.update()
        self.mask_changed.emit()

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == self.MODE_VIEW:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)
        self.update()

    def set_brush_size(self, size: int) -> None:
        self._brush_size = max(1, int(size))

    def fit_to_view(self) -> None:
        if self._qimage.isNull():
            return
        self._fit_mode = True
        margin = 28
        available_w = max(1, self.width() - margin * 2)
        available_h = max(1, self.height() - margin * 2)
        zoom = min(
            available_w / self._qimage.width(), available_h / self._qimage.height()
        )
        self._zoom = max(0.02, min(zoom, 8.0))
        self._offset = QPointF(
            (self.width() - self._qimage.width() * self._zoom) / 2,
            (self.height() - self._qimage.height() * self._zoom) / 2,
        )
        self.zoom_changed.emit(self._zoom)
        self.update()

    def zoom_in(self) -> None:
        self._zoom_at(QPointF(self.width() / 2, self.height() / 2), 1.25)

    def zoom_out(self) -> None:
        self._zoom_at(QPointF(self.width() / 2, self.height() / 2), 1 / 1.25)

    def _zoom_at(self, position: QPointF, factor: float) -> None:
        if self._qimage.isNull():
            return
        old_zoom = self._zoom
        new_zoom = max(0.02, min(12.0, old_zoom * factor))
        if abs(new_zoom - old_zoom) < 1e-9:
            return
        image_pos = QPointF(
            (position.x() - self._offset.x()) / old_zoom,
            (position.y() - self._offset.y()) / old_zoom,
        )
        self._zoom = new_zoom
        self._offset = QPointF(
            position.x() - image_pos.x() * new_zoom,
            position.y() - image_pos.y() * new_zoom,
        )
        self._fit_mode = False
        self.zoom_changed.emit(self._zoom)
        self.update()

    def _to_image(self, position: QPointF) -> QPointF:
        return QPointF(
            (position.x() - self._offset.x()) / self._zoom,
            (position.y() - self._offset.y()) / self._zoom,
        )

    def _to_screen(self, position: QPointF) -> QPointF:
        return QPointF(
            position.x() * self._zoom + self._offset.x(),
            position.y() * self._zoom + self._offset.y(),
        )

    def _inside(self, position: QPointF) -> bool:
        if self._qimage.isNull():
            return False
        return (
            0 <= position.x() < self._qimage.width()
            and 0 <= position.y() < self._qimage.height()
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#15161a"))
        if self._qimage.isNull():
            painter.setPen(QColor("#6b7280"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "拖入或打开一张图片\n\n"
                "或按 Ctrl+V 粘贴剪贴板图片\n\n"
                "支持 PNG / JPG / WEBP",
            )
            return

        target = QRectF(
            self._offset.x(),
            self._offset.y(),
            max(1, round(self._qimage.width() * self._zoom)),
            max(1, round(self._qimage.height() * self._zoom)),
        )
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(target, self._qimage)
        if self._has_mask:
            painter.drawImage(target, self._overlay)
        painter.setPen(QPen(QColor("#3a3d44"), 1))
        painter.drawRect(target)

        if self._drawing and self._mode == self.MODE_RECT:
            start = self._to_screen(self._rect_start)
            current = self._to_screen(self._rect_current)
            rect = QRectF(start, current).normalized()
            pen = QPen(QColor("#4f8cff"), 1)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)

        if (
            self._mode in (self.MODE_BRUSH, self.MODE_ERASE)
            and self._hover_pos is not None
            and self._inside(self._hover_pos)
        ):
            center = self._to_screen(self._hover_pos)
            radius = self._brush_size / 2
            painter.setPen(QPen(QColor("#e6e6e6"), 1))
            painter.drawEllipse(center, radius, radius)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fit_mode:
            self.fit_to_view()

    def wheelEvent(self, event) -> None:
        if self._qimage.isNull():
            return
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom_at(event.position(), factor)

    def mousePressEvent(self, event) -> None:
        if self._qimage.isNull():
            return
        button = event.button()
        if button == Qt.MouseButton.MiddleButton or (
            button == Qt.MouseButton.LeftButton and self._mode == self.MODE_VIEW
        ):
            self._panning = True
            self._last_screen_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if button != Qt.MouseButton.LeftButton:
            return

        image_pos = self._to_image(event.position())
        if self._mode == self.MODE_RECT:
            self._drawing = True
            self._rect_start = image_pos
            self._rect_current = image_pos
            self.update()
        elif self._mode in (self.MODE_BRUSH, self.MODE_ERASE):
            self._drawing = True
            self._last_image_pos = image_pos
            self._draw_dot(image_pos)
            self._has_mask = True
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._qimage.isNull():
            return
        self._hover_pos = self._to_image(event.position())
        if self._panning:
            delta = event.position() - self._last_screen_pos
            self._offset += delta
            self._last_screen_pos = event.position()
            self._fit_mode = False
            self.update()
            return

        if self._drawing:
            image_pos = self._hover_pos
            if self._mode == self.MODE_RECT:
                self._rect_current = image_pos
                self.update()
            elif self._mode in (self.MODE_BRUSH, self.MODE_ERASE):
                self._draw_segment(self._last_image_pos, image_pos)
                self._last_image_pos = image_pos
                self.update()
        else:
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        changed = False
        if self._panning:
            self._panning = False
            self.set_mode(self._mode)
        elif self._drawing:
            if self._mode == self.MODE_RECT:
                rect = QRectF(self._rect_start, self._rect_current).normalized()
                if rect.width() > 1 and rect.height() > 1:
                    self._fill_rect(rect)
                    self._has_mask = True
                    changed = True
                self.update()
            elif self._mode in (self.MODE_BRUSH, self.MODE_ERASE):
                changed = True
            self._drawing = False
        if changed:
            self.mask_changed.emit()

    def leaveEvent(self, event) -> None:
        self._hover_pos = None
        self.update()
        super().leaveEvent(event)

    def _brush_width(self) -> float:
        return max(1.0, self._brush_size / max(self._zoom, 1e-6))

    def _draw_dot(self, position: QPointF) -> None:
        width = self._brush_width()
        rect = QRectF(
            position.x() - width / 2,
            position.y() - width / 2,
            width,
            width,
        )
        mask_painter = QPainter(self._mask)
        mask_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        mask_painter.setPen(QPen(Qt.PenStyle.NoPen))
        color = (
            QColor(0, 0, 0)
            if self._mode == self.MODE_ERASE
            else QColor(255, 255, 255)
        )
        mask_painter.setBrush(color)
        mask_painter.drawEllipse(rect)
        mask_painter.end()

        overlay_painter = QPainter(self._overlay)
        overlay_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._mode == self.MODE_ERASE:
            overlay_painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            overlay_painter.setBrush(QColor(0, 0, 0, 255))
        else:
            overlay_painter.setBrush(QColor(255, 64, 64, 115))
        overlay_painter.setPen(QPen(Qt.PenStyle.NoPen))
        overlay_painter.drawEllipse(rect)
        overlay_painter.end()

    def _draw_segment(self, start: QPointF, end: QPointF) -> None:
        width = self._brush_width()
        pen = QPen(
            QColor(0, 0, 0) if self._mode == self.MODE_ERASE else QColor(255, 255, 255)
        )
        pen.setWidthF(width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        mask_painter = QPainter(self._mask)
        mask_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        mask_painter.setPen(pen)
        mask_painter.drawLine(start, end)
        mask_painter.end()

        overlay_painter = QPainter(self._overlay)
        overlay_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._mode == self.MODE_ERASE:
            overlay_painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            pen2 = QPen(QColor(0, 0, 0, 255))
        else:
            pen2 = QPen(QColor(255, 64, 64, 115))
        pen2.setWidthF(width)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen2.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        overlay_painter.setPen(pen2)
        overlay_painter.drawLine(start, end)
        overlay_painter.end()

    def _fill_rect(self, rect: QRectF) -> None:
        mask_painter = QPainter(self._mask)
        mask_painter.fillRect(
            rect,
            QColor(0, 0, 0) if self._mode == self.MODE_ERASE else QColor(255, 255, 255),
        )
        mask_painter.end()

        overlay_painter = QPainter(self._overlay)
        if self._mode == self.MODE_ERASE:
            overlay_painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            overlay_painter.fillRect(rect, QColor(0, 0, 0, 255))
        else:
            overlay_painter.fillRect(rect, QColor(255, 64, 64, 115))
        overlay_painter.end()
