"""乘客图形：卫生间指示牌风格的矢量人形、方向箭头与轿厢人数统计。

四种人群各有一个可辨识的经典造型，全部用 QPainter 现画，不依赖任何
PNG/SVG 资源：

* 男 —— 圆头 + 梯形躯干 + 双腿
* 女 —— 圆头 + 下摆外张的裙 + 双腿
* 儿童 —— 小一号人形 + 上方横线（大人牵着的手）
* 轮椅 —— 圆头 + 躯干 + 大轮圆与轮辐

人形统一在「脚底为 0、头顶为 1」的局部坐标里描述，再按调用方给的像素
高度缩放，因此大厅里的小人和编辑器里的大预览用的是同一套绘制逻辑。
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from core.building import CHILD, FEMALE, MALE, PEOPLE_KINDS, WHEELCHAIR

#: 经典卫生间指示牌配色。色相与造型一起承担语义：颜色区分人群，
#: 头顶箭头区分方向，两者互不干扰。
CATEGORY_COLORS: dict[str, str] = {
    MALE: "#3d7ff5",
    FEMALE: "#e05c8a",
    CHILD: "#4ec9a5",
    WHEELCHAIR: "#9b6dff",
}

#: 方向箭头用中性色，避免与人群配色抢注意力
ARROW_COLOR = "#c9d1e0"

#: 图形小于这个像素高度时细节已经糊成一团，直接不画
MIN_HEIGHT = 4.0

#: 头顶箭头小于这个像素高度就省略，否则会挤进上一层
MIN_ARROW = 2.5


def category_color(gender: object) -> QColor:
    return QColor(CATEGORY_COLORS.get(gender, CATEGORY_COLORS[MALE]))


def label_key(gender: object) -> str:
    """人群分类对应的 i18n key。"""
    return f"people.{gender}" if gender in CATEGORY_COLORS else f"people.{MALE}"


def _scaled(cx: float, feet_y: float, height: float, x: float, y: float) -> QPointF:
    """局部坐标 (x, y) → 屏幕坐标。局部 y=0 是脚底，y=1 是头顶。"""
    return QPointF(cx + x * height, feet_y - y * height)


def _triangle(
    painter: QPainter,
    a: QPointF,
    b: QPointF,
    c: QPointF,
) -> None:
    path = QPainterPath()
    path.moveTo(a)
    path.lineTo(b)
    path.lineTo(c)
    path.closeSubpath()
    painter.drawPath(path)


def _head(painter: QPainter, cx: float, feet: float, h: float, x: float, y: float, r: float) -> None:
    painter.drawEllipse(_scaled(cx, feet, h, x, y), r * h, r * h)


def _taper(
    painter: QPainter,
    cx: float,
    feet: float,
    h: float,
    top_y: float,
    bottom_y: float,
    top_half: float,
    bottom_half: float,
    offset: float = 0.0,
) -> None:
    """上窄下宽（或反之）的躯干/裙。offset 让躯干偏离中轴。"""
    path = QPainterPath()
    path.moveTo(_scaled(cx, feet, h, offset - top_half, top_y))
    path.lineTo(_scaled(cx, feet, h, offset + top_half, top_y))
    path.lineTo(_scaled(cx, feet, h, offset + bottom_half, bottom_y))
    path.lineTo(_scaled(cx, feet, h, offset - bottom_half, bottom_y))
    path.closeSubpath()
    painter.drawPath(path)


def _legs(
    painter: QPainter,
    cx: float,
    feet: float,
    h: float,
    from_y: float,
    half_gap: float,
    thickness: float,
) -> None:
    """两条分开的腿。用两个独立矩形而不是「一块整体再挖空」，
    避免依赖 Clear 合成模式在有背景的控件上留下的痕迹。"""
    for side in (-1, 1):
        inner = half_gap * side
        outer = (half_gap + thickness) * side
        x0, x1 = sorted((inner * h, outer * h))
        painter.drawRect(
            QRectF(
                cx + x0,
                feet - from_y * h,
                x1 - x0,
                from_y * h,
            )
        )


def _draw_male(painter: QPainter, cx: float, feet: float, h: float) -> None:
    _head(painter, cx, feet, h, 0.0, 0.86, 0.13)
    _taper(painter, cx, feet, h, 0.72, 0.44, 0.15, 0.22)
    _legs(painter, cx, feet, h, 0.44, 0.07, 0.12)


def _draw_female(painter: QPainter, cx: float, feet: float, h: float) -> None:
    _head(painter, cx, feet, h, 0.0, 0.86, 0.12)
    # 上身一小截 + 下摆外张的裙
    _taper(painter, cx, feet, h, 0.74, 0.60, 0.09, 0.12)
    _taper(painter, cx, feet, h, 0.60, 0.14, 0.12, 0.26)
    _legs(painter, cx, feet, h, 0.14, 0.05, 0.045)


def _draw_child(painter: QPainter, cx: float, feet: float, h: float) -> None:
    # 上方横线＝牵着他的大人的手，兼作「这是个小孩」的身高暗示
    painter.drawRect(
        QRectF(
            cx - 0.24 * h,
            feet - 0.86 * h,
            0.48 * h,
            0.06 * h,
        )
    )
    _head(painter, cx, feet, h, 0.0, 0.62, 0.10)
    _taper(painter, cx, feet, h, 0.52, 0.30, 0.10, 0.13)
    _legs(painter, cx, feet, h, 0.30, 0.05, 0.05)


def _draw_wheelchair(painter: QPainter, cx: float, feet: float, h: float) -> None:
    color = painter.brush().color()
    # 轮子左右各占一半，是整个图形最宽的部分，因此以它为准居中
    wheel_r = 0.25
    wheel_cy = 0.27
    ring = 0.045
    painter.setPen(QPen(color, max(1.0, ring * h)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(_scaled(cx, feet, h, 0.0, wheel_cy), wheel_r * h, wheel_r * h)
    # 轮辐
    painter.setPen(QPen(color, max(1.0, ring * h * 0.6)))
    painter.drawLine(
        _scaled(cx, feet, h, -wheel_r * 0.62, wheel_cy),
        _scaled(cx, feet, h, wheel_r * 0.62, wheel_cy),
    )
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    # 头与躯干略微偏右，给前方伸出的小腿让位
    _head(painter, cx, feet, h, 0.03, 0.86, 0.11)
    _taper(painter, cx, feet, h, 0.73, 0.52, 0.10, 0.12, offset=0.03)
    # 伸到轮子前方的小腿
    path = QPainterPath()
    path.moveTo(_scaled(cx, feet, h, 0.03, 0.52))
    path.lineTo(_scaled(cx, feet, h, wheel_r, 0.52))
    path.lineTo(_scaled(cx, feet, h, wheel_r, 0.43))
    path.lineTo(_scaled(cx, feet, h, 0.03, 0.43))
    path.closeSubpath()
    painter.drawPath(path)


_PAINTERS = {
    MALE: _draw_male,
    FEMALE: _draw_female,
    CHILD: _draw_child,
    WHEELCHAIR: _draw_wheelchair,
}


def draw_person(
    painter: QPainter,
    cx: float,
    feet_y: float,
    height: float,
    gender: object,
) -> float:
    """在 (cx, feet_y) 处画一个高为 height 的人形，返回头顶的 y 坐标。

    height 小于 MIN_HEIGHT 时什么都不画，直接返回 feet_y。
    """
    if height < MIN_HEIGHT:
        return feet_y
    draw = _PAINTERS.get(gender, _draw_male)
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(category_color(gender))
    draw(painter, cx, feet_y, height)
    painter.restore()
    return feet_y - height


def draw_arrow(painter: QPainter, cx: float, y: float, up: bool, size: float) -> None:
    """在人形头顶画一个方向箭头。y 是箭头底边，size 是箭头总高。"""
    if size < MIN_ARROW:
        return
    half = size * 0.6
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(ARROW_COLOR))
    if up:
        _triangle(
            painter,
            QPointF(cx, y - size),
            QPointF(cx + half, y),
            QPointF(cx - half, y),
        )
    else:
        _triangle(
            painter,
            QPointF(cx, y + size),
            QPointF(cx + half, y),
            QPointF(cx - half, y),
        )
    painter.restore()


def draw_waiting_person(
    painter: QPainter,
    cx: float,
    feet_y: float,
    height: float,
    gender: object,
    up: bool,
    arrow_size: float,
) -> None:
    """大厅里的一整个人形：本体 + 头顶方向箭头。"""
    top = draw_person(painter, cx, feet_y, height, gender)
    if arrow_size >= MIN_ARROW:
        draw_arrow(painter, cx, top - arrow_size * 0.4, up, arrow_size)


def group_counts(passengers) -> dict[str, int]:
    """按 PEOPLE_KINDS 的固定顺序统计各类人数，缺失的类别不出现。"""
    counts: dict[str, int] = {}
    for person in passengers:
        key = person.gender if person.gender in CATEGORY_COLORS else MALE
        counts[key] = counts.get(key, 0) + 1
    return {kind: counts[kind] for kind in PEOPLE_KINDS if kind in counts}


def draw_car_occupants(painter: QPainter, rect: QRectF, passengers) -> None:
    """轿厢内的载荷：每类画一个人形，右边跟上「×N」。

    轿厢开口很窄，画不下几十个小点，因此按类别聚合成至多四格；某一类
    只有一个人时不写 ×1，避免噪声。
    """
    counts = group_counts(passengers)
    if not counts or rect.height() < MIN_HEIGHT:
        return
    groups = list(counts.items())
    slot_w = rect.width() / len(groups)
    body_h = min(rect.height() * 0.82, slot_w * 0.85)
    if body_h < MIN_HEIGHT:
        return
    font = QFont(painter.font())
    font.setPixelSize(max(7, min(11, int(rect.height() * 0.5))))
    painter.save()
    painter.setFont(font)
    for i, (kind, count) in enumerate(groups):
        left = rect.left() + i * slot_w
        cx = left + slot_w * 0.34
        draw_person(painter, cx, rect.center().y() + body_h / 2, body_h, kind)
        if count > 1:
            painter.setPen(QColor("#e8ecf7"))
            painter.drawText(
                QRectF(left + slot_w * 0.52, rect.top(), slot_w * 0.46, rect.height()),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"×{count}",
            )
    painter.restore()
