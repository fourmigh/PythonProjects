from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from i18n import tr

PALETTE = [
    QColor("#3d7ff5"),
    QColor("#f5a623"),
    QColor("#4ec9a5"),
    QColor("#e05c8a"),
    QColor("#9b6dff"),
    QColor("#ff7043"),
    QColor("#5bc0de"),
]
BG = QColor("#17181d")
GRID = QColor("#2c2f3d")
TEXT = QColor("#9aa3b8")


def color_for_index(index: int) -> QColor:
    return PALETTE[index % len(PALETTE)]


class ChartWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._runner = None
        self._keys: list[str] = []
        self.setMinimumHeight(150)

    def set_runner(self, runner) -> None:
        self._runner = runner
        self._keys = list(runner.sims.keys())
        self.update()

    def refresh_keys(self) -> None:
        if self._runner is not None:
            self._keys = list(self._runner.sims.keys())
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), BG)
        if self._runner is None or not self._keys:
            painter.setPen(TEXT)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr("stats.empty"))
            painter.end()
            return
        margin = 34
        plot = QRectF(
            margin, 14, max(10, self.width() - margin - 12), max(10, self.height() - 40)
        )
        series = []
        max_y = 1e-6
        max_x = 1e-6
        for i, key in enumerate(self._keys):
            sim = self._runner.sims.get(key)
            if sim is None:
                continue
            pts = [(s.time, s.awt) for s in sim.metrics.samples if s.awt >= 0]
            if len(pts) < 2:
                continue
            series.append((i, key, pts))
            max_x = max(max_x, pts[-1][0])
            max_y = max(max_y, max(v for _, v in pts))
        if not series:
            painter.setPen(TEXT)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr("stats.empty"))
            painter.end()
            return

        painter.setPen(QPen(GRID, 1))
        for g in range(5):
            y = plot.top() + plot.height() * g / 4
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
        painter.setPen(TEXT)
        font = QFont()
        font.setPixelSize(10)
        painter.setFont(font)
        painter.drawText(
            QRectF(0, plot.top() - 6, margin - 6, 14),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"{max_y:.1f}",
        )
        painter.drawText(
            QRectF(0, plot.bottom() - 7, margin - 6, 14),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "0",
        )
        painter.drawText(
            QRectF(plot.left(), plot.bottom() + 4, plot.width(), 14),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"{max_x:.0f}s",
        )

        for i, key, pts in series:
            color = color_for_index(i)
            painter.setPen(QPen(color, 2))
            path_points = []
            for t, v in pts:
                x = plot.left() + plot.width() * (t / max_x)
                y = plot.bottom() - plot.height() * (v / max_y)
                path_points.append(QPointF(x, y))
            for a, b in zip(path_points, path_points[1:]):
                painter.drawLine(a, b)

        legend_x = plot.left() + 8
        legend_y = plot.top() + 8
        for i, key, _pts in series:
            color = color_for_index(i)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRect(QRectF(legend_x, legend_y, 10, 10))
            painter.setPen(TEXT)
            painter.drawText(
                QRectF(legend_x + 14, legend_y - 3, 260, 16),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                tr(key),
            )
            legend_y += 16
        painter.end()
