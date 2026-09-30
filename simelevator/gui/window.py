from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.building import PEOPLE_KINDS
from core.models import SimConfig
from gui.elevator_view import ElevatorView
from gui.passenger_page import PassengerPage
from gui.people_art import draw_arrow, draw_person, label_key
from gui.settings_panel import DEFAULT_KEYS, SettingsPanel
from i18n import add_listener, remove_listener, tr
from runner import ComparisonRunner

PAGE_SIMULATION = 0
PAGE_PASSENGERS = 1

MINUTES_PER_DAY = 1440
_CHIP_STYLES = {
    "smooth": "background: #2b5fb8; color: white;",
    "fast": "background: #b8651a; color: white;",
}
#: 图例里每个人形图标的边长
LEGEND_GLYPH_PX = 22


def format_scale(value: float) -> str:
    """倍率文本：三位以上取整保留可读性，个位数保留一位小数。"""
    return f"{value:.0f}" if value >= 10.0 else f"{value:.1f}"


def format_clock(elapsed: float, start_time_min: int) -> str:
    """把已推进的仿真秒数换算成「第 n 天 HH:MM:SS」。"""
    minutes = int(start_time_min) + int(elapsed // 60)
    return f"{tr('sim.clock_day', n=minutes // MINUTES_PER_DAY + 1)} {minutes % MINUTES_PER_DAY // 60:02d}:{minutes % 60:02d}:{int(elapsed % 60):02d}"


class _LegendGlyph(QWidget):
    """图例里的小图标：直接复用 people_art 画人形和箭头，配色永远不会走样。

    gender 传 None 表示只画箭头（方向图例），否则画该类人形；
    up 为 None 表示不画箭头。
    """

    def __init__(
        self,
        gender: str | None = None,
        up: bool | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._gender = gender
        self._up = up
        self.setFixedSize(LEGEND_GLYPH_PX, LEGEND_GLYPH_PX)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        size = LEGEND_GLYPH_PX
        if self._up is not None:
            # 箭头居中，占满整个图标高度，和电梯视图里的箭头同源
            draw_arrow(painter, size / 2, size / 2, self._up, size * 0.42)
        if self._gender is not None:
            draw_person(painter, size / 2, size - 1, size - 2, self._gender)
        painter.end()


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.runner = ComparisonRunner()
        self._running = False
        self._last_tick = time.perf_counter()
        self._last_panel_update = 0.0

        self.view = ElevatorView()
        self.panel = SettingsPanel()
        self.passengers = PassengerPage(
            floors=self.panel.floors.value(), seed=self.panel.seed.value()
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self.panel)
        scroll.setMinimumWidth(360)
        scroll.setStyleSheet(
            """
            QScrollArea { background: #1f2027; border: none; }
            QScrollBar:vertical { background: #14151a; width: 12px; }
            QScrollBar::handle:vertical { background: #3a3e4f; border-radius: 5px; min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #14151a; }
            QScrollBar::groove:vertical { background: #14151a; width: 12px; }
            """
        )

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(3)
        self.splitter.addWidget(self.view)
        self.splitter.addWidget(scroll)
        self.splitter.setStretchFactor(0, 618)
        self.splitter.setStretchFactor(1, 382)
        self.splitter.setSizes([992, 618])

        self.sim_page = QWidget()
        # 图例独占一行放在竖井视图上方：电梯视图是满铺布局（上边距只有
        # 14px），往里塞图例必然遮住最高层的乘客。
        sim_layout = QVBoxLayout(self.sim_page)
        sim_layout.setContentsMargins(0, 0, 0, 0)
        sim_layout.setSpacing(0)
        self.legend = self._build_legend()
        self.legend.setStyleSheet(
            """
            QWidget#legendBar { background: #1a1b22; border-bottom: 1px solid #2c2f3d; }
            QLabel#legendTitle { color: #9fb4e8; font-weight: bold; }
            QLabel#legendText { color: #c9d1e0; }
            QLabel#legendHint { color: #7b8194; font-size: 11px; }
            """
        )
        sim_layout.addWidget(self.legend)
        sim_layout.addWidget(self.splitter, 1)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.sim_page)
        self.stack.addWidget(self.passengers)

        self.nav_simulation = QPushButton()
        self.nav_passengers = QPushButton()
        for button in (self.nav_simulation, self.nav_passengers):
            button.setCheckable(True)
            button.setMinimumHeight(30)
        self.nav_simulation.setChecked(True)
        self.nav = QButtonGroup(self)
        self.nav.addButton(self.nav_simulation, PAGE_SIMULATION)
        self.nav.addButton(self.nav_passengers, PAGE_PASSENGERS)

        self.building_badge = QLabel()
        self.building_badge.setObjectName("buildingBadge")
        self.clock_label = QLabel()
        self.clock_label.setObjectName("clockLabel")
        self.speed_chip = QLabel()
        self.speed_chip.setObjectName("speedChip")
        self.speed_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_chip.setMinimumHeight(22)
        self._speed_mode = ""
        self._speed_value = -1.0

        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(10, 8, 10, 4)
        nav_row.setSpacing(8)
        nav_row.addWidget(self.nav_simulation)
        nav_row.addWidget(self.nav_passengers)
        nav_row.addStretch(1)
        nav_row.addWidget(self.building_badge)
        nav_row.addWidget(self.clock_label)
        nav_row.addWidget(self.speed_chip)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        nav_widget = QWidget()
        nav_widget.setLayout(nav_row)
        nav_widget.setStyleSheet(
            """
            QWidget { background: #1f2027; }
            QPushButton {
                background: #262932; border: 1px solid #34374a; border-radius: 5px;
                padding: 6px 18px; color: #9aa3b8; font-weight: bold;
            }
            QPushButton:checked { background: #2b5fb8; color: white; border-color: #3d7ff5; }
            QPushButton:hover { background: #34384a; }
            QLabel#buildingBadge {
                background: #262932; border: 1px solid #34374a; border-radius: 10px;
                padding: 3px 12px; color: #8fa4c8; font-weight: bold;
            }
            QLabel#clockLabel { color: #9aa3b8; padding: 0 4px; }
            QLabel#speedChip {
                border-radius: 10px; padding: 3px 12px; color: white; font-weight: bold;
            }
            """
        )
        layout.addWidget(nav_widget)
        layout.addWidget(self.stack, 1)

        self.panel.apply_requested.connect(self._apply_settings)
        self.panel.reset_requested.connect(self._reset_simulation)
        self.panel.run_toggled.connect(self._on_run_toggled)
        self.panel.language_changed.connect(self._on_language_changed)
        self.panel.open_passengers_requested.connect(
            lambda: self.show_page(PAGE_PASSENGERS)
        )
        self.panel.algorithm_list.itemChanged.connect(self._on_algorithm_selection_changed)
        self.panel.view_algorithm.currentIndexChanged.connect(self._on_view_changed)
        self.panel.floors.valueChanged.connect(self._on_context_changed)
        self.panel.seed.valueChanged.connect(self._on_context_changed)
        self.passengers.profiles_changed.connect(self._on_profiles_changed)
        self.passengers.building_changed.connect(self._on_building_changed)
        self.passengers.capacity_changed.connect(self.refresh_building_badge)
        self.nav.idClicked.connect(self.show_page)

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        add_listener(self.retranslate)
        self._apply_settings()
        self.retranslate()
        self._update_clock(0.0, 0.0)

    def show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(PAGE_PASSENGERS if index == PAGE_PASSENGERS else PAGE_SIMULATION)
        if self.stack.currentIndex() == PAGE_PASSENGERS:
            self._running = False
            self.panel.set_running_state(False)

    def _on_context_changed(self, _value) -> None:
        self.passengers.set_context(self.panel.floors.value(), self.panel.seed.value())

    def _on_profiles_changed(self) -> None:
        self._apply_settings()

    def _on_building_changed(self) -> None:
        self.refresh_building_badge()

    def _apply_settings(self) -> None:
        keys = self.panel.selected_algorithm_keys()
        config = self.panel.collect_config()
        self.runner.configure(config, keys, profiles=self.passengers.profiles)
        self._sync_view()
        self.panel.chart.set_runner(self.runner)
        self.panel.update_stats(self.runner.results(), self.runner.now)
        if not keys:
            self._running = False
            self.panel.set_running_state(False)

    def _reset_simulation(self) -> None:
        self.runner.reset()
        self._sync_view()
        self.panel.chart.refresh_keys()
        self.panel.update_stats(self.runner.results(), self.runner.now)
        self.view.update()

    def _on_run_toggled(self, checked: bool) -> None:
        if checked and not self.runner.sims:
            self._apply_settings()
        self._running = checked and bool(self.runner.sims)
        self.panel.set_running_state(self._running)
        self._last_tick = time.perf_counter()

    def _on_algorithm_selection_changed(self, _item) -> None:
        self.panel._refresh_view_combo()
        if not self.runner.sims:
            self._apply_settings()

    def _on_view_changed(self, _index: int) -> None:
        self._sync_view()

    def _sync_view(self) -> None:
        key = self.panel.selected_view_key()
        if key is None and self.runner.sims:
            key = next(iter(self.runner.sims))
        sim = self.runner.sims.get(key) if key else None
        self.view.set_simulation(sim)

    def _on_language_changed(self, lang: str) -> None:
        from i18n import set_language

        set_language(lang)

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = min(0.1, max(0.0, now - self._last_tick))
        self._last_tick = now
        stepped = 0.0
        if self._running and self.runner.sims:
            stepped = self.runner.step_auto(dt, self.panel.time_scale_value())
        self.view.update()
        self._update_clock(dt, stepped)
        if now - self._last_panel_update >= 0.4:
            self._last_panel_update = now
            self.panel.update_stats(self.runner.results(), self.runner.now)
            self.panel.chart.refresh_keys()
            self.panel.chart.update()

    def _update_clock(self, real_dt: float, stepped: float) -> None:
        """刷新时钟与倍速胶囊。显示的是本帧实际生效的倍率，不是下拉设定值。"""
        self.clock_label.setText(
            format_clock(self.runner.now, self.runner.config.start_time_min)
        )
        if not self._running or real_dt <= 0.0:
            self._set_speed_chip("", 0.0)
            return
        effective = stepped / real_dt
        self._set_speed_chip("fast" if stepped > real_dt + 1e-9 else "smooth", effective)

    def _set_speed_chip(self, mode: str, effective: float) -> None:
        if mode == self._speed_mode and self._speed_value == effective:
            return
        self._speed_mode = mode
        self._speed_value = effective
        if mode == "":
            self.speed_chip.clear()
            self.speed_chip.setToolTip("")
            return
        self.speed_chip.setText(
            f"{tr('sim.mode.smooth' if mode == 'smooth' else 'sim.mode.fast')} "
            f"{tr('sim.scale', v=format_scale(effective))}"
        )
        self.speed_chip.setToolTip(tr("sim.clock_tip", v=format_scale(effective)))
        self.speed_chip.setStyleSheet(_CHIP_STYLES[mode])

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key.Key_1:
            self.nav_simulation.setChecked(True)
            self.show_page(PAGE_SIMULATION)
        elif event.key() == Qt.Key.Key_2:
            self.nav_passengers.setChecked(True)
            self.show_page(PAGE_PASSENGERS)
        else:
            super().keyPressEvent(event)

    def _build_legend(self) -> QWidget:
        """图例条：四类人群各一个人形图标，再说明箭头含义。

        放在竖井视图上方独立一行，而不是塞进电梯视图内部——电梯视图
        是满铺布局，上边距只有 14px，盖住最高层的乘客。
        """
        bar = QWidget()
        bar.setObjectName("legendBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 5, 12, 5)
        layout.setSpacing(14)

        self.legend_title = QLabel()
        self.legend_title.setObjectName("legendTitle")
        layout.addWidget(self.legend_title)

        # 图标和文字分开存引用：retranslate 只改文字，图形由 paintEvent 负责
        self.legend_labels: dict[str, QLabel] = {}
        for kind in PEOPLE_KINDS:
            layout.addWidget(_LegendGlyph(kind))
            label = QLabel()
            label.setObjectName("legendText")
            self.legend_labels[kind] = label
            layout.addWidget(label)

        layout.addSpacing(6)
        self.legend_arrow_labels: list[QLabel] = []
        for up, key in ((True, "view.up"), (False, "view.down")):
            layout.addWidget(_LegendGlyph(up=up))
            label = QLabel()
            label.setObjectName("legendText")
            label.setProperty("i18n_key", key)
            self.legend_arrow_labels.append(label)
            layout.addWidget(label)

        self.legend_hint = QLabel()
        self.legend_hint.setObjectName("legendHint")
        layout.addWidget(self.legend_hint)
        layout.addStretch(1)
        return bar

    def _retranslate_legend(self) -> None:
        self.legend_title.setText(tr("people.legend"))
        for kind, label in self.legend_labels.items():
            label.setText(tr(label_key(kind)))
        for label in self.legend_arrow_labels:
            # 「上行/下行」与电梯视图里的楼层标签共用同一对 key
            label.setText(tr(str(label.property("i18n_key"))))
        self.legend_hint.setText(tr("people.legend.hint"))

    def retranslate(self) -> None:
        self.setWindowTitle(tr("app.title"))
        self.nav_simulation.setText(tr("nav.simulation"))
        self.nav_passengers.setText(tr("nav.passengers"))
        self.refresh_building_badge()
        self._speed_mode = ""  # 强制重绘倍速胶囊的文案
        self._retranslate_legend()
        self.panel.retranslate()
        self.passengers.retranslate()
        self.view.update()

    def refresh_building_badge(self) -> None:
        building = self.passengers.building
        self.building_badge.setText(
            tr(
                "building.badge",
                kind=tr(f"building.{building.kind}")
                if building.kind in ("residential", "office")
                else building.kind,
                share=tr("building.resident_share", n=round(building.resident_share * 100)),
                total=tr("building.total", n=self.passengers.population.total),
            )
        )

    def closeEvent(self, event) -> None:
        remove_listener(self.retranslate)
        super().closeEvent(event)
