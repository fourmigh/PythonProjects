from __future__ import annotations

import sys
import unittest

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from core.building import CHILD, FEMALE, MALE, PEOPLE_KINDS, WHEELCHAIR
from gui.people_art import (
    ARROW_COLOR,
    CATEGORY_COLORS,
    MIN_ARROW,
    MIN_HEIGHT,
    draw_arrow,
    draw_car_occupants,
    draw_person,
    draw_waiting_person,
    group_counts,
    label_key,
)

APP = QApplication.instance() or QApplication(sys.argv)

BACKGROUND = QColor("#17181d")


def render(fn, width: int = 200, height: int = 160) -> QImage:
    img = QImage(width, height, QImage.Format.Format_ARGB32)
    img.fill(BACKGROUND)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    try:
        fn(painter)
    finally:
        painter.end()
    return img


def color_mask(img: QImage, color: str) -> list[list[bool]]:
    """容差匹配某颜色的像素；抗锯齿边缘是混色，故留 40 的余量。"""
    want = QColor(color)
    out = []
    for y in range(img.height()):
        row = []
        for x in range(img.width()):
            got = img.pixelColor(x, y)
            row.append(
                abs(got.red() - want.red()) < 40
                and abs(got.green() - want.green()) < 40
                and abs(got.blue() - want.blue()) < 40
            )
        out.append(row)
    return out


def bbox(mask: list[list[bool]]) -> tuple[int, int, int, int] | None:
    points = [(x, y) for y, row in enumerate(mask) for x, on in enumerate(row) if on]
    if not points:
        return None
    return (
        min(x for x, _ in points),
        min(y for _, y in points),
        max(x for x, _ in points),
        max(y for _, y in points),
    )


def filled(mask: list[list[bool]]) -> int:
    return sum(sum(1 for on in row if on) for row in mask)


def row_counts(mask: list[list[bool]]) -> list[int]:
    return [sum(1 for on in row if on) for row in mask]


class FakePassenger:
    def __init__(self, gender: str) -> None:
        self.gender = gender


class CategoryArtTests(unittest.TestCase):
    def test_every_category_has_its_own_color(self) -> None:
        self.assertEqual(set(CATEGORY_COLORS), set(PEOPLE_KINDS))
        self.assertEqual(len(set(CATEGORY_COLORS.values())), len(PEOPLE_KINDS))

    def test_label_key_covers_every_category(self) -> None:
        for kind in PEOPLE_KINDS:
            self.assertEqual(label_key(kind), f"people.{kind}")

    def test_label_key_falls_back_for_unknown(self) -> None:
        self.assertEqual(label_key("nonsense"), f"people.{MALE}")

    def test_each_category_draws_a_distinct_centred_figure(self) -> None:
        signatures = {}
        for kind in PEOPLE_KINDS:
            with self.subTest(kind=kind):
                mask = color_mask(
                    render(lambda p, k=kind: draw_person(p, 100, 140, 100, k)),
                    CATEGORY_COLORS[kind],
                )
                box = bbox(mask)
                self.assertIsNotNone(box, f"{kind} 没有画出任何像素")
                self.assertGreater(filled(mask), 500, f"{kind} 过于稀疏")
                # 以人为中心，四类的包围盒中心都必须落在中轴上
                center_x = (box[0] + box[2]) / 2
                self.assertAlmostEqual(center_x, 100, delta=1.5)
                # 脚下踩在 feet_y 上；儿童刻意画得矮一些，见下方专门用例
                self.assertAlmostEqual(box[3], 140, delta=2)
                if kind != CHILD:
                    self.assertAlmostEqual(box[1], 140 - 100, delta=3)
                signatures[kind] = tuple(row_counts(mask))
        self.assertEqual(
            len(set(signatures.values())),
            len(PEOPLE_KINDS),
            "四类人形必须有可区分的轮廓",
        )

    def test_child_is_drawn_smaller_than_adult(self) -> None:
        heights = {}
        for kind in (MALE, CHILD):
            mask = color_mask(
                render(lambda p, k=kind: draw_person(p, 100, 140, 100, k)),
                CATEGORY_COLORS[kind],
            )
            box = bbox(mask)
            heights[kind] = box[3] - box[1]
        self.assertLess(heights[CHILD], heights[MALE])

    def test_unknown_category_falls_back_to_male(self) -> None:
        mask = color_mask(
            render(lambda p: draw_person(p, 100, 140, 100, "不存在")),
            CATEGORY_COLORS[MALE],
        )
        self.assertGreater(filled(mask), 500)

    def test_tiny_heights_draw_nothing_instead_of_crashing(self) -> None:
        for height in (0.0, 0.5, 2.0, MIN_HEIGHT - 0.1):
            with self.subTest(height=height):
                mask = color_mask(
                    render(lambda p, h=height: draw_person(p, 100, 140, h, MALE)),
                    CATEGORY_COLORS[MALE],
                )
                self.assertEqual(filled(mask), 0)


class ArrowTests(unittest.TestCase):
    def _arrow(self, up: bool) -> tuple[list[int], tuple[int, int, int, int] | None]:
        mask = color_mask(
            render(lambda p: draw_arrow(p, 100, 70, up, 24)), ARROW_COLOR
        )
        rows = row_counts(mask)
        return rows, bbox(mask)

    def test_up_arrow_is_narrow_at_top(self) -> None:
        rows, box = self._arrow(True)
        self.assertIsNotNone(box)
        self.assertAlmostEqual(box[1], 70 - 24, delta=2)
        self.assertAlmostEqual(box[3], 70, delta=2)
        tip = sum(rows[46:58])
        base = sum(rows[58:71])
        self.assertLess(tip, base, "上行箭头应是上窄下宽的三角")

    def test_down_arrow_is_narrow_at_bottom(self) -> None:
        rows, box = self._arrow(False)
        self.assertIsNotNone(box)
        self.assertAlmostEqual(box[1], 70, delta=2)
        self.assertAlmostEqual(box[3], 70 + 24, delta=2)
        base = sum(rows[70:82])
        tip = sum(rows[82:95])
        self.assertLess(tip, base, "下行箭头应是下窄上宽的三角")

    def test_arrows_point_in_opposite_directions(self) -> None:
        up_rows, _ = self._arrow(True)
        down_rows, _ = self._arrow(False)
        self.assertNotEqual(up_rows[46:70], down_rows[70:94])

    def test_tiny_arrow_is_skipped(self) -> None:
        for size in (0.0, 1.0, MIN_ARROW - 0.1):
            with self.subTest(size=size):
                mask = color_mask(
                    render(lambda p, s=size: draw_arrow(p, 100, 70, True, s)),
                    ARROW_COLOR,
                )
                self.assertEqual(filled(mask), 0)

    def test_waiting_person_puts_arrow_above_the_head(self) -> None:
        img = render(lambda p: draw_waiting_person(p, 100, 140, 40, MALE, True, 10))
        body = bbox(color_mask(img, CATEGORY_COLORS[MALE]))
        arrow = bbox(color_mask(img, ARROW_COLOR))
        self.assertIsNotNone(body)
        self.assertIsNotNone(arrow)
        self.assertLess(arrow[3], body[1], "箭头必须整个位于头顶之上")

    def test_waiting_person_without_arrow_space(self) -> None:
        img = render(lambda p: draw_waiting_person(p, 100, 140, 40, MALE, True, 0.0))
        self.assertEqual(filled(color_mask(img, ARROW_COLOR)), 0)


class CarOccupantTests(unittest.TestCase):
    def test_group_counts_follows_people_kinds_order(self) -> None:
        people = [FakePassenger(WHEELCHAIR), FakePassenger(MALE), FakePassenger(MALE)]
        self.assertEqual(list(group_counts(people)), [MALE, WHEELCHAIR])
        self.assertEqual(group_counts(people), {MALE: 2, WHEELCHAIR: 1})

    def test_group_counts_ignores_unknown_kind(self) -> None:
        self.assertEqual(group_counts([FakePassenger("x"), FakePassenger(MALE)]), {MALE: 2})

    def test_empty_car_draws_nothing(self) -> None:
        img = render(lambda p: draw_car_occupants(p, QRectF(10, 50, 180, 60), []))
        for color in CATEGORY_COLORS.values():
            self.assertEqual(filled(color_mask(img, color)), 0)

    def test_one_group_without_count_label(self) -> None:
        """只有一个人时不写 ×1，避免视觉噪声。"""
        rect = QRectF(10, 50, 180, 60)
        img = render(lambda p: draw_car_occupants(p, rect, [FakePassenger(MALE)]))
        mask = color_mask(img, CATEGORY_COLORS[MALE])
        self.assertGreater(filled(mask), 100)
        # 计数文字是白灰色，不属于任何人群色
        grey = color_mask(img, "#e8ecf7")
        self.assertEqual(filled(grey), 0)

    def test_all_four_groups_fit_in_a_narrow_door(self) -> None:
        rect = QRectF(0, 50, 180, 60)
        people = (
            [FakePassenger(MALE)] * 3
            + [FakePassenger(FEMALE)] * 5
            + [FakePassenger(CHILD)]
            + [FakePassenger(WHEELCHAIR)] * 2
        )
        img = render(lambda p: draw_car_occupants(p, rect, people))
        for kind in PEOPLE_KINDS:
            with self.subTest(kind=kind):
                self.assertGreater(filled(color_mask(img, CATEGORY_COLORS[kind])), 20)
        # 三类超过 1 人，因此有三处计数文字
        self.assertGreater(filled(color_mask(img, "#e8ecf7")), 5)

    def test_too_small_door_draws_nothing(self) -> None:
        rect = QRectF(0, 0, 4, MIN_HEIGHT - 1)
        img = render(lambda p: draw_car_occupants(p, rect, [FakePassenger(MALE)] * 9))
        for color in CATEGORY_COLORS.values():
            self.assertEqual(filled(color_mask(img, color)), 0)


if __name__ == "__main__":
    unittest.main()
