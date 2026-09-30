from __future__ import annotations

from PySide6.QtCore import QTime, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from algorithms import REGISTRY
from core.models import SimConfig
from gui.chart import ChartWidget
from i18n import tr, languages

ORIGIN_ITEMS = [
    ("settings.origin.uniform", "uniform"),
    ("settings.origin.lobby", "lobby"),
    ("settings.origin.custom", "custom"),
]
DEST_ITEMS = [
    ("settings.dest.uniform", "uniform"),
    ("settings.dest.lobby", "lobby"),
    ("settings.dest.custom", "custom"),
]
LANG_ITEMS = [
    ("lang.zh_CN", "zh_CN"),
    ("lang.en_US", "en_US"),
]
WEEKDAY_ITEMS = [(f"weekday.{d}", d) for d in range(1, 8)]
#: 有人时的最高推进倍率。没人时不限倍率，由 runner.step_auto 自动快进。
TIME_SCALE_ITEMS = [
    ("settings.scale.1", 1.0),
    ("settings.scale.2", 2.0),
    ("settings.scale.5", 5.0),
    ("settings.scale.10", 10.0),
]
STAT_COLUMNS = [
    "stats.algorithm",
    "stats.awt",
    "stats.travel",
    "stats.served",
    "stats.waiting",
    "stats.abandoned",
]
DEFAULT_KEYS = ["algo.lobby", "algo.median", "algo.adaptive"]


class SettingsPanel(QWidget):
    apply_requested = Signal()
    reset_requested = Signal()
    run_toggled = Signal(bool)
    language_changed = Signal(str)
    open_passengers_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._labels: list[tuple[QLabel, str]] = []
        self._combo_items: list[tuple[QComboBox, list[tuple[str, str]]]] = []
        self._button_keys: list[tuple[QPushButton, str, str, str]] = []
        self._group_keys: list[tuple[QGroupBox, str]] = []
        self._stat_rows: dict[str, int] = {}
        self._build()

    def _spin(self, lo: float, hi: float, step: float, decimals: int = 1) -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setRange(lo, hi)
        box.setSingleStep(step)
        box.setDecimals(decimals)
        return box

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        form_group, form_label = self._group("settings.title")
        form = QFormLayout(form_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.floors = QSpinBox()
        self.floors.setRange(2, 60)
        self.floors.setValue(12)
        self.elevators = QSpinBox()
        self.elevators.setRange(1, 8)
        self.elevators.setValue(3)
        self.speed = self._spin(0.2, 10.0, 0.5)
        self.speed.setValue(2.0)
        self.door_time = self._spin(0.0, 10.0, 0.1)
        self.door_time.setValue(1.0)
        self.boarding_time = self._spin(0.0, 10.0, 0.1)
        self.boarding_time.setValue(0.8)
        self.alighting_time = self._spin(0.0, 10.0, 0.1)
        self.alighting_time.setValue(0.6)
        self.min_door_open = self._spin(0.0, 10.0, 0.1)
        self.min_door_open.setValue(1.0)
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setTime(QTime(7, 0))
        self.start_weekday = QComboBox()
        self.start_weekday.addItem("Mon", 1)
        self.arrival_rate = self._spin(0.0, 60.0, 0.5)
        self.arrival_rate.setValue(6.0)
        self.origin_mode = QComboBox()
        self.dest_mode = QComboBox()
        self.custom_origin = QLineEdit()
        self.custom_dest = QLineEdit()
        self.seed = QSpinBox()
        self.seed.setRange(0, 999999)
        self.seed.setValue(42)
        self.energy_weight = self._spin(0.0, 1.0, 0.05, decimals=2)
        self.energy_weight.setValue(0.3)
        self.idle_park_delay = self._spin(0.0, 60.0, 0.5)
        self.idle_park_delay.setValue(1.0)
        self.history_window = self._spin(10.0, 6000.0, 10.0, decimals=0)
        self.history_window.setValue(300.0)

        self._field(form, "settings.floors", self.floors)
        self._field(form, "settings.elevators", self.elevators)
        self._field(form, "settings.speed", self.speed)
        self._field(form, "settings.door_time", self.door_time)
        self._field(form, "settings.boarding_time", self.boarding_time)
        self._field(form, "settings.alighting_time", self.alighting_time)
        self._field(form, "settings.min_door_open", self.min_door_open)
        self._field(form, "settings.start_time", self.start_time)
        self._field(form, "settings.start_weekday", self.start_weekday)
        self._field(form, "settings.seed", self.seed)
        self._field(form, "settings.energy_weight", self.energy_weight)
        self._field(form, "settings.idle_park_delay", self.idle_park_delay)
        self._field(form, "settings.history_window", self.history_window)
        self._combo_items.append((self.start_weekday, WEEKDAY_ITEMS))
        self._combo_items.append((self.origin_mode, ORIGIN_ITEMS))
        self._combo_items.append((self.dest_mode, DEST_ITEMS))
        self.origin_mode.currentIndexChanged.connect(self._sync_custom_enabled)
        self.dest_mode.currentIndexChanged.connect(self._sync_custom_enabled)
        root.addWidget(form_group)

        demand_group, _demand_title = self._group("settings.arrival_rate")
        demand_layout = QVBoxLayout(demand_group)
        demand_layout.setContentsMargins(10, 8, 10, 10)
        demand_layout.setSpacing(7)
        self.profile_note = QLabel(tr("settings.profile_note"))
        self.profile_note.setWordWrap(True)
        self.profile_note.setStyleSheet("color: #9fb4e8; font-size: 11px;")
        demand_layout.addWidget(self.profile_note)
        demand_form = QFormLayout()
        demand_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        demand_form.setHorizontalSpacing(12)
        self._demand_fields: list[tuple[QLabel, QWidget]] = []
        for key, widget in (
            ("settings.arrival_rate", self.arrival_rate),
            ("settings.origin_mode", self.origin_mode),
            ("settings.custom_origin_weights", self.custom_origin),
            ("settings.dest_mode", self.dest_mode),
            ("settings.custom_dest_weights", self.custom_dest),
        ):
            label = QLabel(tr(key))
            label.setProperty("i18n_key", key)
            self._labels.append((label, key))
            self._demand_fields.append((label, widget))
            demand_form.addRow(label, widget)
        demand_layout.addLayout(demand_form)
        self.passengers_button = QPushButton(tr("settings.open_passengers"))
        demand_layout.addWidget(self.passengers_button)
        root.addWidget(demand_group)
        self._set_demand_enabled(False)

        algo_group, algo_label = self._group("settings.algorithms")
        algo_layout = QVBoxLayout(algo_group)
        algo_layout.setContentsMargins(10, 10, 10, 10)
        self.algorithm_list = QListWidget()
        self.algorithm_list.setMinimumHeight(150)
        for key in REGISTRY:
            item = QListWidgetItem(tr(key))
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if key in DEFAULT_KEYS else Qt.CheckState.Unchecked
            )
            self.algorithm_list.addItem(item)
        algo_layout.addWidget(self.algorithm_list)
        root.addWidget(algo_group)

        view_row = QHBoxLayout()
        self.view_label, _ = self._label("settings.view_algorithm")
        self.view_algorithm = QComboBox()
        view_row.addWidget(self.view_label)
        view_row.addWidget(self.view_algorithm, 1)
        root.addLayout(view_row)
        self._refresh_view_combo()

        controls = QHBoxLayout()
        self.run_button = QPushButton()
        self.run_button.setCheckable(True)
        self._button_keys.append(
            (self.run_button, "run", "settings.run", "settings.pause")
        )
        self.apply_button = QPushButton()
        self._plain_button(self.apply_button, "settings.apply")
        self.reset_button = QPushButton()
        self._plain_button(self.reset_button, "settings.reset")
        controls.addWidget(self.run_button, 2)
        controls.addWidget(self.apply_button, 1)
        controls.addWidget(self.reset_button, 1)
        root.addLayout(controls)

        lang_row = QHBoxLayout()
        self.lang_label, _ = self._label("settings.language")
        self.language_combo = QComboBox()
        self._combo_items.append((self.language_combo, LANG_ITEMS))
        lang_row.addWidget(self.lang_label)
        lang_row.addWidget(self.language_combo, 1)
        root.addLayout(lang_row)

        scale_row = QHBoxLayout()
        self.scale_label, _ = self._label("settings.time_scale")
        self.time_scale = QComboBox()
        for key, factor in TIME_SCALE_ITEMS:
            self.time_scale.addItem(tr(key), factor)
        self.time_scale.setCurrentIndex(0)
        self._combo_items.append((self.time_scale, TIME_SCALE_ITEMS))
        scale_row.addWidget(self.scale_label)
        scale_row.addWidget(self.time_scale, 1)
        root.addLayout(scale_row)
        self.time_scale.setToolTip(tr("settings.time_scale.tip"))

        stats_group, stats_title = self._group("stats.title")
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.setContentsMargins(10, 10, 10, 10)
        self.elapsed_label = QLabel()
        self._labels.append((self.elapsed_label, "stats.elapsed"))
        self.stats_table = QTableWidget(0, len(STAT_COLUMNS))
        self.stats_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for i in range(1, len(STAT_COLUMNS)):
            self.stats_table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents
            )
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stats_table.setMinimumHeight(130)
        self.stats_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        stats_layout.addWidget(self.elapsed_label)
        stats_layout.addWidget(self.stats_table)
        root.addWidget(stats_group)

        self.chart = ChartWidget()
        root.addWidget(self.chart, 1)

        self.run_button.toggled.connect(self.run_toggled.emit)
        self.apply_button.clicked.connect(self.apply_requested.emit)
        self.reset_button.clicked.connect(self.reset_requested.emit)
        self.language_combo.currentIndexChanged.connect(
            lambda _i: self.language_changed.emit(
                self.language_combo.currentData() or "zh_CN"
            )
        )
        self.passengers_button.clicked.connect(self.open_passengers_requested.emit)

        bg = "#1f2027"
        fg = "#d7dbe6"
        self.setStyleSheet(
            f"""
            QWidget {{ background: {bg}; color: {fg}; font-size: 13px; }}
            QGroupBox {{ border: 1px solid #34374a; border-radius: 6px; margin-top: 10px; padding-top: 4px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #9fb4e8; }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QTableWidget {{
                background: #14151a; border: 1px solid #34374a; border-radius: 4px;
                padding: 3px 6px; selection-background-color: #3d7ff5;
            }}
            QListWidget::item {{ padding: 3px; }}
            QListWidget::item:checked {{ color: #9fb4e8; }}
            QPushButton {{
                background: #2b5fb8; border: none; border-radius: 5px;
                padding: 7px 10px; color: white; font-weight: bold;
            }}
            QPushButton:hover {{ background: #3d7ff5; }}
            QPushButton:checked {{ background: #2f9e6a; }}
            QPushButton:disabled {{ background: #3a3e4f; color: #7b8194; }}
            QHeaderView::section {{ background: #14151a; color: #9aa3b8; border: none; padding: 4px; }}
            QTableWidget {{ gridline-color: #2c2f3d; }}
            QScrollBar:vertical {{ background: #1f2027; width: 10px; }}
            QScrollBar::handle:vertical {{ background: #3a3e4f; border-radius: 5px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: #1f2027; }}
            QScrollBar::groove:vertical {{ background: #14151a; width: 10px; }}
            QScrollArea {{ background: #1f2027; border: none; }}
            """
        )
        self.retranslate()

    def _group(self, key: str) -> tuple[QGroupBox, QLabel]:
        box = QGroupBox()
        self._group_keys.append((box, key))
        return box, QLabel()

    def _label(self, key: str) -> tuple[QLabel, str]:
        label = QLabel()
        self._labels.append((label, key))
        return label, key

    def _field(self, form: QFormLayout, key: str, widget: QWidget) -> None:
        label = QLabel()
        self._labels.append((label, key))
        form.addRow(label, widget)

    def _plain_button(self, button: QPushButton, key: str) -> None:
        button.setProperty("i18n_key", key)
        self._labels.append((button, key))

    def _set_demand_enabled(self, enabled: bool) -> None:
        for _label, widget in self._demand_fields:
            widget.setEnabled(enabled)
        self.passengers_button.setEnabled(True)

    def _sync_custom_enabled(self) -> None:
        self.custom_origin.setEnabled(self.origin_mode.currentData() == "custom")
        self.custom_dest.setEnabled(self.dest_mode.currentData() == "custom")

    def _refresh_view_combo(self) -> None:
        current = self.view_algorithm.currentData()
        self.view_algorithm.clear()
        for i in range(self.algorithm_list.count()):
            item = self.algorithm_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                key = item.data(Qt.ItemDataRole.UserRole)
                self.view_algorithm.addItem(tr(key), key)
        if current is not None:
            index = self.view_algorithm.findData(current)
            if index >= 0:
                self.view_algorithm.setCurrentIndex(index)

    def selected_algorithm_keys(self) -> list[str]:
        keys = []
        for i in range(self.algorithm_list.count()):
            item = self.algorithm_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                keys.append(item.data(Qt.ItemDataRole.UserRole))
        return keys

    def selected_view_key(self) -> str | None:
        return self.view_algorithm.currentData()

    def time_scale_value(self) -> float:
        value = self.time_scale.currentData()
        try:
            return float(value)
        except (TypeError, ValueError):
            return 1.0

    def set_running_state(self, running: bool) -> None:
        self.run_button.blockSignals(True)
        self.run_button.setChecked(running)
        self.run_button.blockSignals(False)
        self._update_run_text(running)

    def _update_run_text(self, running: bool) -> None:
        for button, attr, run_key, pause_key in self._button_keys:
            if button is self.run_button:
                button.setText(tr(pause_key if running else run_key))

    def collect_config(self) -> SimConfig:
        time_value = self.start_time.time()
        return SimConfig(
            floors=self.floors.value(),
            elevators=self.elevators.value(),
            speed=self.speed.value(),
            door_time=self.door_time.value(),
            boarding_time=self.boarding_time.value(),
            alighting_time=self.alighting_time.value(),
            min_door_open=self.min_door_open.value(),
            arrival_rate=self.arrival_rate.value(),
            origin_mode=self.origin_mode.currentData() or "uniform",
            dest_mode=self.dest_mode.currentData() or "uniform",
            custom_origin_weights=self.custom_origin.text(),
            custom_dest_weights=self.custom_dest.text(),
            seed=self.seed.value(),
            energy_weight=self.energy_weight.value(),
            idle_park_delay=self.idle_park_delay.value(),
            history_window=self.history_window.value(),
            start_time_min=time_value.hour() * 60 + time_value.minute(),
            start_weekday=int(self.start_weekday.currentData() or 1),
            passenger_source="profile",
        )

    def update_stats(self, results: dict[str, dict[str, float]], elapsed: float) -> None:
        self.elapsed_label.setText(f"{tr('stats.elapsed')} {elapsed:.0f}")
        if set(results) != set(self._stat_rows):
            self.stats_table.setRowCount(0)
            self._stat_rows.clear()
            for key in results:
                row = self.stats_table.rowCount()
                self.stats_table.insertRow(row)
                self._stat_rows[key] = row
                item = QTableWidgetItem(tr(key))
                from gui.chart import color_for_index

                item.setForeground(color_for_index(row))
                self.stats_table.setItem(row, 0, item)
        for key, snap in results.items():
            row = self._stat_rows.get(key)
            if row is None:
                continue
            values = [
                f"{snap['awt']:.2f}",
                f"{snap['travel']:.0f}",
                f"{snap['served']:.0f}",
                f"{snap['waiting']:.0f}",
                f"{snap.get('abandoned', 0.0):.0f}",
            ]
            for col, value in enumerate(values, start=1):
                existing = self.stats_table.item(row, col)
                if existing is None:
                    existing = QTableWidgetItem()
                    self.stats_table.setItem(row, col, existing)
                existing.setText(value)

    def retranslate(self) -> None:
        for label, key in self._labels:
            label.setText(tr(key))
        for box, key in self._group_keys:
            box.setTitle(tr(key))
        for combo, items in self._combo_items:
            index = combo.currentIndex()
            combo.blockSignals(True)
            combo.clear()
            for item_key, data in items:
                combo.addItem(tr(item_key), data)
            if 0 <= index < combo.count():
                combo.setCurrentIndex(index)
            combo.blockSignals(False)
        for i in range(self.algorithm_list.count()):
            item = self.algorithm_list.item(i)
            item.setText(tr(item.data(Qt.ItemDataRole.UserRole)))
        for button, _attr, run_key, pause_key in self._button_keys:
            if button is self.run_button:
                button.setText(tr(run_key if not button.isChecked() else pause_key))
        view_index = self.view_algorithm.currentIndex()
        self.view_algorithm.blockSignals(True)
        self.view_algorithm.clear()
        for i in range(self.algorithm_list.count()):
            item = self.algorithm_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                key = item.data(Qt.ItemDataRole.UserRole)
                self.view_algorithm.addItem(tr(key), key)
        if 0 <= view_index < self.view_algorithm.count():
            self.view_algorithm.setCurrentIndex(view_index)
        self.view_algorithm.blockSignals(False)
        for col, key in enumerate(STAT_COLUMNS):
            self.stats_table.setHorizontalHeaderItem(col, QTableWidgetItem(tr(key)))
        for key, row in self._stat_rows.items():
            item = self.stats_table.item(row, 0)
            if item is not None:
                item.setText(tr(key))
        self._sync_custom_enabled()
        self.profile_note.setText(tr("settings.profile_note"))
        self.passengers_button.setText(tr("settings.open_passengers"))
        self._set_demand_enabled(False)
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
