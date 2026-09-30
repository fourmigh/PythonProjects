from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from gui.people_art import draw_car_occupants, draw_waiting_person
from i18n import tr

BG = QColor("#17181d")
SHAFT_BG = QColor("#242630")
SHAFT_EDGE = QColor("#34374a")
CAR = QColor("#3d7ff5")
CAR_DARK = QColor("#2b5fb8")
DOOR = QColor("#c9d1e0")
DOOR_DIM = QColor("#575e70")
DOOR_LINE = QColor("#8b93a8")
PLATFORM = QColor("#3a3e4f")
FLOOR_TEXT = QColor("#aab2c5")
CALL_DOT = QColor("#ff5c5c")
IDLE_TEXT = QColor("#6d7488")

#: 楼层高到这个像素以下就不再画头顶箭头，否则会挤进上一层
MIN_ARROW_ROW = 12.0
#: 一个候梯人占的横向间距
PERSON_PITCH = 14


class ElevatorView(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._sim = None
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(480, 400)

    def set_simulation(self, sim) -> None:
        self._sim = sim
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), BG)
        if self._sim is None:
            self._draw_hint(painter)
            return
        self._draw(painter)
        painter.end()

    def _draw_hint(self, painter: QPainter) -> None:
        painter.setPen(QColor("#6d7488"))
        rect = self.rect()
        painter.drawText(rect.adjusted(40, 40, -40, -40), Qt.AlignmentFlag.AlignCenter, tr("view.hint"))

    def _draw(self, painter: QPainter) -> None:
        sim = self._sim
        margin = 14
        label_w = 46
        floors = sim.floors
        elevators = sim.elevators
        shafts = max(1, len(elevators))
        inner_w = max(10, self.width() - 2 * margin - label_w)
        inner_h = max(10, self.height() - 2 * margin)
        row_h = inner_h / floors
        shaft_w = inner_w / shafts
        font = QFont()
        font.setPixelSize(max(10, min(14, int(row_h * 0.45))))
        painter.setFont(font)

        def row_top(f: float) -> float:
            return margin + (floors - f) * row_h

        for shaft_i in range(shafts):
            x = margin + label_w + shaft_i * shaft_w
            painter.fillRect(QRectF(x + 2, margin, shaft_w - 4, inner_h), SHAFT_BG)
            painter.setPen(QPen(SHAFT_EDGE, 1))
            painter.drawLine(QPointF(x + 2, margin), QPointF(x + 2, margin + inner_h))
            painter.drawLine(
                QPointF(x + shaft_w - 2, margin), QPointF(x + shaft_w - 2, margin + inner_h)
            )

        for f in range(1, floors + 1):
            y = row_top(f)
            painter.setPen(QPen(PLATFORM, 1))
            painter.drawLine(
                QPointF(margin, y + row_h), QPointF(margin + label_w + inner_w, y + row_h)
            )
            painter.setPen(FLOOR_TEXT)
            painter.drawText(
                QRectF(margin, y, label_w - 6, row_h),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{f}{tr('view.floor')}",
            )
            waiting = sim.waiting.get(f, [])
            if waiting:
                painter.setPen(CALL_DOT)
                painter.drawText(
                    QRectF(margin + label_w + 4, y, 16, row_h),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    "!",
                )
            self._draw_waiting(painter, waiting, margin + label_w + 22, y, row_h, shaft_w, shafts)

        for shaft_i, e in enumerate(elevators):
            x = margin + label_w + shaft_i * shaft_w
            self._draw_doors(painter, e, x, row_top, row_h, shaft_w, floors)
            self._draw_car(painter, e, x, row_top, row_h, shaft_w)

    def _draw_waiting(
        self,
        painter: QPainter,
        waiting: list,
        x0: float,
        y: float,
        row_h: float,
        shaft_w: float,
        shafts: int,
    ) -> None:
        # 人形本体 + 头顶方向箭头。颜色表示人群，箭头表示方向，
        # 两者互相独立，因此不再用「不同颜色」去暗示上下行。
        arrow_size = 0.0
        if row_h >= MIN_ARROW_ROW:
            arrow_size = max(2.5, min(6.0, row_h * 0.18))
        body_h = min(max(6.0, row_h * 0.55), row_h - arrow_size - 2.0)
        cy = y + row_h - 4
        per_shaft = max(1, int(shaft_w * 0.35 // PERSON_PITCH))
        for i, p in enumerate(waiting[: shafts * per_shaft]):
            draw_waiting_person(
                painter,
                x0 + i * PERSON_PITCH + 4,
                cy,
                body_h,
                p.gender,
                p.dir > 0,
                arrow_size,
            )

    def _draw_doors(self, painter: QPainter, e, x: float, row_top, row_h: float, shaft_w: float, floors: int) -> None:
        parked_floor = int(round(e.floor))
        door_open = e.door if abs(e.floor - parked_floor) < 0.01 else 0.0
        for f in range(1, floors + 1):
            y = row_top(f)
            door_x = x + shaft_w * 0.15
            door_w = shaft_w * 0.7
            rect = QRectF(door_x, y + row_h * 0.15, door_w, row_h * 0.7)
            painter.setPen(QPen(DOOR_LINE, 1))
            if f == parked_floor and door_open > 0:
                open_w = door_w * 0.85 * door_open
                painter.fillRect(rect, QColor("#101116"))
                left = QRectF(rect.left(), rect.top(), (door_w - open_w) / 2, rect.height())
                right = QRectF(rect.right() - (door_w - open_w) / 2, rect.top(), (door_w - open_w) / 2, rect.height())
                painter.fillRect(left, DOOR_DIM)
                painter.fillRect(right, DOOR_DIM)
                painter.setPen(QPen(DOOR_LINE, 1))
                painter.drawRect(rect)
            else:
                painter.fillRect(rect, DOOR_DIM)
                painter.drawLine(
                    QPointF(rect.center().x(), rect.top()),
                    QPointF(rect.center().x(), rect.bottom()),
                )

    def _draw_car(self, painter: QPainter, e, x: float, row_top, row_h: float, shaft_w: float) -> None:
        car_w = shaft_w * 0.72
        car_h = row_h * 0.86
        car_x = x + (shaft_w - car_w) / 2
        car_y = row_top(e.floor) + (row_h - car_h) / 2
        rect = QRectF(car_x, car_y, car_w, car_h)
        painter.setPen(QPen(CAR_DARK, 1.5))
        painter.setBrush(CAR)
        painter.drawRoundedRect(rect, 4, 4)

        door_w = car_w * 0.66
        door_h = car_h * 0.72
        door_rect = QRectF(
            rect.center().x() - door_w / 2,
            rect.bottom() - door_h - 2,
            door_w,
            door_h,
        )
        painter.setPen(QPen(DOOR_LINE, 1))
        painter.setBrush(QColor("#101116"))
        painter.drawRect(door_rect)
        if e.door > 0:
            open_w = door_w * e.door
            left_w = (door_w - open_w) / 2
            painter.fillRect(QRectF(door_rect.left(), door_rect.top(), left_w, door_h), DOOR)
            painter.fillRect(
                QRectF(door_rect.right() - left_w, door_rect.top(), left_w, door_h), DOOR
            )
            if e.passengers:
                # 轿厢开口很窄，画不下几十个小点：按人群聚合成至多四格，
                # 每格一个人形加上「×N」的人数
                draw_car_occupants(painter, door_rect, e.passengers)
        else:
            painter.fillRect(door_rect, DOOR)
            painter.drawLine(
                QPointF(door_rect.center().x(), door_rect.top()),
                QPointF(door_rect.center().x(), door_rect.bottom()),
            )

        label = f"{int(round(e.floor))}"
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#0e2a66"))
        painter.drawRoundedRect(
            QRectF(rect.left() + 3, rect.top() + 3, 20, 16), 3, 3
        )
        painter.setPen(QColor("#dfe7ff"))
        font = painter.font()
        font.setPixelSize(11)
        painter.setFont(font)
        painter.drawText(
            QRectF(rect.left() + 3, rect.top() + 3, 20, 16),
            Qt.AlignmentFlag.AlignCenter,
            label,
        )

        if e.phase.name == "MOVING" and e.direction != 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#ffd166"))
            cx = rect.center().x()
            if e.direction > 0:
                top = rect.top() + 24
                path = QPainterPath()
                path.moveTo(cx, top)
                path.lineTo(cx + 5, top + 7)
                path.lineTo(cx - 5, top + 7)
                path.closeSubpath()
            else:
                top = rect.top() + 30
                path = QPainterPath()
                path.moveTo(cx, top + 7)
                path.lineTo(cx + 5, top)
                path.lineTo(cx - 5, top)
                path.closeSubpath()
            painter.drawPath(path)
