from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QTime, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QHBoxLayout as _QHBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)
from core.building import (
    BUILDING_PRESETS,
    BUILDING_TYPES,
    DEFAULT_BUILDING,
    MALE,
    PEOPLE_KINDS,
    POPULATION_WARN,
    Building,
    Population,
    resident_label_key,
    resident_template,
)
from core.profiles import (
    PALETTE,
    RESIDENT,
    VISITOR,
    PassengerProfile,
    ProfileStore,
    TripLeg,
    fill_defaults,
    make_batch,
    new_profile,
    resolve,
)
from gui.people_art import CATEGORY_COLORS, draw_person, label_key
from i18n import tr

#: 允许测试与外部工具把画像库指到别处，避免误写仓库里的样例文件
DATA_PATH = Path(
    os.environ.get("SIMELEVATOR_DATA")
    or Path(__file__).resolve().parent.parent / "data" / "profiles.json"
)

#: 乘客编辑器里的图形预览尺寸（大号人形）
PREVIEW_PX = 56

FILTER_ITEMS = [
    ("profile.filter.all", "all"),
    ("profile.filter.resident", RESIDENT),
    ("profile.filter.visitor", VISITOR),
]
GROUP_ITEMS = [
    ("profile.group.all", "none"),
    ("profile.group.kind", "kind"),
    ("profile.group.floor", "floor"),
]
KIND_ITEMS = [
    ("profile.filter.resident", RESIDENT),
    ("profile.filter.visitor", VISITOR),
]
#: 人群分类下拉框：i18n key 由 people_art.label_key 统一生成
PEOPLE_ITEMS = [(label_key(kind), kind) for kind in PEOPLE_KINDS]
BATCH_MODE_ITEMS = [
    ("profile.batch.uniform", "uniform"),
    ("profile.batch.low", "low"),
    ("profile.batch.random", "random"),
]
LEG_COLUMNS = ["profile.legs.time", "profile.legs.floor", "profile.legs.stay"]


def _hhmm(minutes: int | None) -> str:
    if minutes is None:
        return "--:--"
    m = int(minutes) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def _swatch_label(kind: str) -> str:
    """人群标签：前面带一个该类配色的色块，后面跟可翻译的名称。

    QLabel 会自动识别这段富文本，因此色块随 CATEGORY_COLORS 变化，
    文字仍走 i18n。注意这行不能设 i18n_key 属性，否则 retranslate 里的
    通用循环会用纯文本把它整个覆盖掉。
    """
    return (
        f'<span style="color:{CATEGORY_COLORS.get(kind, CATEGORY_COLORS[MALE])}">'
        "■</span>&nbsp;" + tr(label_key(kind))
    )


class _PersonPreview(QWidget):
    """画像编辑器里的大号人物图形：选什么人群就画什么，所见即所得。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._gender: str = MALE

    def set_gender(self, gender: object) -> None:
        self._gender = gender if gender in CATEGORY_COLORS else MALE
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#14151a"))
        draw_person(
            painter,
            self.width() / 2,
            self.height() - 6,
            min(self.width(), self.height()) - 12,
            self._gender,
        )
        painter.end()


class PassengerPage(QWidget):
    """乘客画像页：左侧列表（0.618）+ 右侧编辑器（0.382）。"""

    profiles_changed = Signal()
    building_changed = Signal()
    capacity_changed = Signal()

    def __init__(self, floors: int = 12, seed: int = 42, parent: QWidget | None = None):
        super().__init__(parent)
        self.floors = floors
        self.seed = seed
        self.store = ProfileStore(DATA_PATH)
        self.profiles: list[PassengerProfile] = self.store.load()
        if not self.profiles:
            from core.profiles import sample_profiles

            self.profiles = sample_profiles()
            self.store.save(self.profiles)
        self.building: Building = self.store.building
        self._loading = False
        self._clamped_to = floors
        self._build()
        self.reload_list()
        if self.profiles:
            self.list.setCurrentRow(0)

    # -------------------------------------------------------------- building
    @property
    def population(self) -> Population:
        """当前大楼按楼层数算出的乘客规模，供预览与批量生成共用。"""
        return self.building.population(self.floors, self.seed)

    def apply_building(self, building: Building, rebuild: bool | None = None) -> None:
        """提交整套大楼属性（楼型 + 容量参数 + 住客占比）。

        已落盘的画像不会因为提交而被改动——大楼属性只影响此后新建、复制
        和批量生成的画像。调用方可用 rebuild 明确指定是否按新楼型重建。
        """
        building = building.normalized()
        if building == self.building:
            return
        if rebuild is None:
            rebuild = self._confirm_rebuild()
        if rebuild is None:  # 用户取消
            self._sync_building_widgets()
            return
        self.building = building
        if rebuild and self.profiles:
            start = self.store.next_index()
            self.profiles = make_batch(
                start_index=start,
                base_seed=self.seed,
                floors=self.floors,
                building=building,
            )
        self._persist()
        self._sync_building_widgets()
        self._refresh_population()
        self.reload_list()
        self.building_changed.emit()
        self.capacity_changed.emit()
        self.profiles_changed.emit()

    def _confirm_rebuild(self) -> bool | None:
        """询问是否按新楼型重建全部画像：True 重建 / False 仅影响新建 / None 取消。"""
        box = QMessageBox(self)
        box.setWindowTitle(tr("building.rebuild.title"))
        box.setText(tr("building.rebuild.text", n=len(self.profiles)))
        rebuild = box.addButton(tr("building.rebuild.yes"), QMessageBox.ButtonRole.AcceptRole)
        new_only = box.addButton(tr("building.rebuild.no"), QMessageBox.ButtonRole.RejectRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is rebuild:
            return True
        if clicked is new_only:
            return False
        return None

    def _on_building_kind_changed(self, _index: int) -> None:
        if self._loading:
            return
        kind = self.building_combo.currentData() or DEFAULT_BUILDING.kind
        preset = BUILDING_PRESETS.get(kind, DEFAULT_BUILDING)
        # 切楼型等于换一栋楼：容量参数一并回到该楼型预设
        self.apply_building(preset)

    def _on_share_changed(self, value: int) -> None:
        if self._loading:
            return
        # 占比只影响访客数量，无需打扰用户确认
        self._submit_capacity(rebuild=False)

    def _on_capacity_changed(self, _value: int) -> None:
        """入住率 / 每层单元数 / 每单元人数变化：只刷新预览，不重建。"""
        if self._loading:
            return
        self._submit_capacity(rebuild=False)

    def _on_mix_changed(self, _value: object) -> None:
        """人群构成与轮椅/儿童特殊参数变化：只影响新建，不打扰用户确认。"""
        if self._loading:
            return
        self._submit_capacity(rebuild=False)

    def _submit_capacity(self, rebuild: bool | None = False) -> None:
        self.apply_building(self._building_from_widgets(), rebuild=rebuild)

    def _building_from_widgets(self) -> Building:
        low = self.occupants_min_spin.value()
        high = self.occupants_max_spin.value()
        # 四个占比各自独立输入，不必凑成 100：normalized() 会统一归一
        mix = {kind: self.mix_spins[kind].value() / 100.0 for kind in PEOPLE_KINDS}
        return Building(
            kind=self.building_combo.currentData() or self.building.kind,
            resident_share=self.share_spin.value() / 100.0,
            occupancy_rate=self.occupancy_spin.value() / 100.0,
            units_per_floor=self.units_spin.value(),
            occupants_per_unit=(min(low, high), max(low, high)),
            people_mix=mix,
            wheelchair_patience=self.wheelchair_patience.value(),
            child_min_companions=self.child_companions_spin.value(),
            child_patience=self.child_patience.value(),
        )

    def _sync_building_widgets(self) -> None:
        self._loading = True
        try:
            index = self.building_combo.findData(self.building.kind)
            if index >= 0:
                self.building_combo.setCurrentIndex(index)
            self.share_spin.setValue(round(self.building.resident_share * 100))
            self.occupancy_spin.setValue(round(self.building.occupancy_rate * 100))
            self.units_spin.setValue(self.building.units_per_floor)
            self.occupants_min_spin.setValue(self.building.occupants_per_unit[0])
            self.occupants_max_spin.setValue(self.building.occupants_per_unit[1])
            # 控件显示归一化后的比例，否则 45/45/7/3 这类非整百输入会
            # 在界面上和「实际比例」对不上
            for kind, share in self.building.normalized().people_mix.items():
                if kind in self.mix_spins:
                    self.mix_spins[kind].setValue(round(share * 100))
            self.wheelchair_patience.setValue(self.building.wheelchair_patience)
            self.child_companions_spin.setValue(self.building.child_min_companions)
            self.child_patience.setValue(self.building.child_patience)
        finally:
            self._loading = False
        self.building_hint.setText(tr("building.hint"))
        self._sync_kind_labels()

    def _refresh_population(self) -> None:
        """把大楼容量换算成的人数写进预览与批量总数。"""
        pop = self.population
        self.population_label.setText(
            tr(
                "building.population",
                residents=pop.residents,
                visitors=pop.visitors,
                total=pop.total,
            )
        )
        counts = {kind: pop.mix.get(kind, 0) for kind in PEOPLE_KINDS}
        self.mix_population_label.setText(tr("building.mix.population", **counts))
        heavy = pop.total > POPULATION_WARN
        self.population_hint.setText(tr("building.population.warn") if heavy else "")
        self.population_hint.setVisible(heavy)
        self.batch_total.setText(tr("profile.batch.total", n=pop.total))
        self.batch_total.setToolTip(tr("profile.batch.hint"))

    def _sync_kind_labels(self) -> None:
        """商务楼里住客即员工，标签随之改写。"""
        staff = self.building.kind == "office"
        for combo in (self.filter_combo, self.kind_combo):
            index = combo.findData(RESIDENT)
            if index >= 0:
                combo.setItemText(
                    index,
                    tr("profile.kind.staff" if staff else "profile.filter.resident"),
                )
        self.add_resident_btn.setText(
            tr("profile.add_staff" if staff else "profile.add_resident")
        )

    def set_context(self, floors: int, seed: int) -> None:
        if floors == self.floors and seed == self.seed:
            return
        # setRange 会钳制越界值并触发 valueChanged，若此时提交会把
        # 尚未重建的旧日程表读回画像，因此整段屏蔽提交
        self._loading = True
        self.floors = floors
        # 种子只影响此后新建的画像：已随机落盘的数据绝不因改种子而重掷
        self.seed = seed
        if floors != self._clamped_to:
            self._clamp_stored()
        self._clamp_spins()
        self._loading = False
        # 楼层数直接决定容量，必须重算预览
        self._refresh_population()
        self.capacity_changed.emit()
        self.reload_list()

    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setStretchFactor(0, 618)
        splitter.setStretchFactor(1, 382)
        splitter.setSizes([992, 618])
        root.addWidget(splitter)
        self._sync_building_widgets()
        self._refresh_population()
        self._apply_style()

    # ------------------------------------------------------------------ left
    def _build_left(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 10, 14)
        layout.setSpacing(8)

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("profile.search"))
        self.search.setClearButtonEnabled(True)
        self.filter_combo = QComboBox()
        for key, data in FILTER_ITEMS:
            self.filter_combo.addItem(tr(key), data)
        self.filter_combo.setMaximumWidth(120)
        top.addWidget(self.search, 1)
        top.addWidget(self.filter_combo)
        layout.addLayout(top)

        self.building_box = QGroupBox()
        self.building_box.setTitle(tr("building.title"))
        building_layout = QVBoxLayout(self.building_box)
        building_layout.setContentsMargins(10, 8, 10, 8)
        building_layout.setSpacing(6)

        self.building_combo = QComboBox()
        for kind in BUILDING_TYPES:
            self.building_combo.addItem(tr(f"building.{kind}"), kind)
        self.share_spin = QSpinBox()
        self.share_spin.setRange(0, 100)
        self.share_spin.setValue(round(self.building.resident_share * 100))
        self.share_spin.setSuffix("%")
        self.occupancy_spin = QSpinBox()
        self.occupancy_spin.setRange(0, 100)
        self.occupancy_spin.setValue(round(self.building.occupancy_rate * 100))
        self.occupancy_spin.setSuffix("%")
        self.units_spin = QSpinBox()
        self.units_spin.setRange(0, 50)
        self.units_spin.setValue(self.building.units_per_floor)
        self.occupants_min_spin = QSpinBox()
        self.occupants_min_spin.setRange(1, 200)
        self.occupants_min_spin.setValue(self.building.occupants_per_unit[0])
        self.occupants_max_spin = QSpinBox()
        self.occupants_max_spin.setRange(1, 200)
        self.occupants_max_spin.setValue(self.building.occupants_per_unit[1])
        self.occupants_range_label = QLabel("–")

        occupants_row = QHBoxLayout()
        occupants_row.setContentsMargins(0, 0, 0, 0)
        occupants_row.setSpacing(4)
        occupants_row.addWidget(self.occupants_min_spin)
        occupants_row.addWidget(self.occupants_range_label)
        occupants_row.addWidget(self.occupants_max_spin)

        # ---- 子区一：容量
        self.capacity_title = QLabel(tr("building.capacity_title"))
        self.capacity_title.setObjectName("sectionTitle")
        capacity_form = QFormLayout()
        capacity_form.setContentsMargins(0, 0, 0, 0)
        capacity_form.setSpacing(6)
        self.capacity_labels: list[tuple[QLabel, str]] = []
        for key, field in (
            ("building.share_field", self.share_spin),
            ("building.occupancy_rate", self.occupancy_spin),
            ("building.units_per_floor", self.units_spin),
            ("building.occupants_per_unit", None),
        ):
            label = QLabel(tr(key))
            self.capacity_labels.append((label, key))
            capacity_form.addRow(label, occupants_row if field is None else field)

        self.population_label = QLabel()

        # ---- 子区二：人群构成
        self.mix_title = QLabel(tr("building.mix_title"))
        self.mix_title.setObjectName("sectionTitle")
        self.mix_spins: dict[str, QSpinBox] = {}
        self.mix_labels: dict[str, QLabel] = {}
        for kind in PEOPLE_KINDS:
            spin = QSpinBox()
            spin.setRange(0, 100)
            spin.setValue(round(self.building.mix_for(kind) * 100))
            spin.setSuffix("%")
            spin.setToolTip(tr(label_key(kind)))
            self.mix_spins[kind] = spin
        # 四个占比并排一行，标签带色块，和仿真里的人物配色对得上
        mix_row = QHBoxLayout()
        mix_row.setContentsMargins(0, 0, 0, 0)
        mix_row.setSpacing(4)
        for kind in PEOPLE_KINDS:
            label = QLabel(_swatch_label(kind))
            self.mix_labels[kind] = label
            mix_row.addWidget(label)
            mix_row.addWidget(self.mix_spins[kind])

        self.wheelchair_patience = QDoubleSpinBox()
        self.wheelchair_patience.setRange(0.1, 10.0)
        self.wheelchair_patience.setSingleStep(0.1)
        self.wheelchair_patience.setDecimals(2)
        self.wheelchair_patience.setValue(self.building.wheelchair_patience)
        self.wheelchair_patience.setSuffix("×")
        self.child_companions_spin = QSpinBox()
        self.child_companions_spin.setRange(1, 20)
        self.child_companions_spin.setValue(self.building.child_min_companions)
        self.child_patience = QDoubleSpinBox()
        self.child_patience.setRange(0.1, 10.0)
        self.child_patience.setSingleStep(0.1)
        self.child_patience.setDecimals(2)
        self.child_patience.setValue(self.building.child_patience)
        self.child_patience.setSuffix("×")

        behavior_form = QFormLayout()
        behavior_form.setContentsMargins(0, 0, 0, 0)
        behavior_form.setSpacing(6)
        self.behavior_labels: list[tuple[QLabel, str]] = []
        for key, field in (
            ("building.wheelchair_patience", self.wheelchair_patience),
            ("building.child_min_companions", self.child_companions_spin),
            ("building.child_patience", self.child_patience),
        ):
            label = QLabel(tr(key))
            self.behavior_labels.append((label, key))
            behavior_form.addRow(label, field)

        self.mix_population_label = QLabel()
        self.mix_population_label.setObjectName("mixTotal")
        self.mix_hint = QLabel()
        self.mix_hint.setObjectName("buildingHint")
        self.mix_hint.setWordWrap(True)
        self.population_hint = QLabel()
        self.population_hint.setObjectName("populationWarn")
        self.population_hint.setWordWrap(True)
        self.building_hint = QLabel()
        self.building_hint.setObjectName("buildingHint")
        self.building_hint.setWordWrap(True)

        building_layout.addWidget(self.building_combo)
        building_layout.addWidget(self.capacity_title)
        building_layout.addLayout(capacity_form)
        building_layout.addWidget(self.population_label)
        building_layout.addWidget(self.mix_title)
        building_layout.addLayout(mix_row)
        building_layout.addLayout(behavior_form)
        building_layout.addWidget(self.mix_population_label)
        building_layout.addWidget(self.mix_hint)
        building_layout.addWidget(self.population_hint)
        building_layout.addWidget(self.building_hint)
        layout.addWidget(self.building_box)

        self.group_combo = QComboBox()
        for key, data in GROUP_ITEMS:
            self.group_combo.addItem(tr(key), data)
        self.group_combo.setMaximumWidth(160)
        layout.addWidget(self.group_combo, 0, Qt.AlignmentFlag.AlignRight)

        self.list = QListWidget()
        self.list.setAlternatingRowColors(False)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.list, 1)

        self.count_label = QLabel()
        layout.addWidget(self.count_label)

        buttons = QHBoxLayout()
        self.add_resident_btn = QPushButton(tr("profile.add_resident"))
        self.add_visitor_btn = QPushButton(tr("profile.add_visitor"))
        buttons.addWidget(self.add_resident_btn)
        buttons.addWidget(self.add_visitor_btn)
        layout.addLayout(buttons)

        row2 = QHBoxLayout()
        self.batch_btn = QPushButton(tr("profile.batch"))
        self.duplicate_btn = QPushButton(tr("profile.duplicate"))
        self.delete_btn = QPushButton(tr("profile.delete"))
        row2.addWidget(self.batch_btn)
        row2.addWidget(self.duplicate_btn)
        row2.addWidget(self.delete_btn)
        layout.addLayout(row2)

        self.batch_row = QWidget()
        batch_layout = QHBoxLayout(self.batch_row)
        batch_layout.setContentsMargins(0, 0, 0, 0)
        batch_layout.setSpacing(6)
        self.batch_total = QLabel()
        self.batch_total.setObjectName("batchTotal")
        self.batch_mode_label = QLabel(tr("profile.batch.floor_mode"))
        self.batch_mode = QComboBox()
        for key, data in BATCH_MODE_ITEMS:
            self.batch_mode.addItem(tr(key), data)
        self.batch_confirm = QPushButton(tr("settings.apply"))
        batch_layout.addWidget(self.batch_total, 1)
        batch_layout.addWidget(self.batch_mode_label)
        batch_layout.addWidget(self.batch_mode, 1)
        batch_layout.addWidget(self.batch_confirm, 1)
        self.batch_row.setVisible(False)
        layout.addWidget(self.batch_row)

        self.search.textChanged.connect(self.reload_list)
        self.filter_combo.currentIndexChanged.connect(self.reload_list)
        self.group_combo.currentIndexChanged.connect(self.reload_list)
        self.list.currentRowChanged.connect(self._on_select)
        self.building_combo.currentIndexChanged.connect(self._on_building_kind_changed)
        self.share_spin.valueChanged.connect(self._on_share_changed)
        self.occupancy_spin.valueChanged.connect(self._on_capacity_changed)
        self.units_spin.valueChanged.connect(self._on_capacity_changed)
        self.occupants_min_spin.valueChanged.connect(self._on_capacity_changed)
        self.occupants_max_spin.valueChanged.connect(self._on_capacity_changed)
        for spin in self.mix_spins.values():
            spin.valueChanged.connect(self._on_mix_changed)
        self.wheelchair_patience.valueChanged.connect(self._on_mix_changed)
        self.child_companions_spin.valueChanged.connect(self._on_mix_changed)
        self.child_patience.valueChanged.connect(self._on_mix_changed)
        self.add_resident_btn.clicked.connect(lambda: self.add(RESIDENT))
        self.add_visitor_btn.clicked.connect(lambda: self.add(VISITOR))
        self.batch_btn.clicked.connect(
            lambda: self.batch_row.setVisible(not self.batch_row.isVisible())
        )
        self.batch_confirm.clicked.connect(self._do_batch)
        self.duplicate_btn.clicked.connect(self.duplicate)
        self.delete_btn.clicked.connect(self.delete_current)
        return panel

    # ----------------------------------------------------------------- right
    def _build_right(self) -> QWidget:
        scroll = QWidget()
        layout = QVBoxLayout(scroll)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        basic = QGroupBox(tr("profile.title"))
        form = QFormLayout(basic)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(7)

        self.name_edit = QLineEdit()
        self.kind_combo = QComboBox()
        for key, data in KIND_ITEMS:
            self.kind_combo.addItem(tr(key), data)
        self.gender_combo = QComboBox()
        for key, data in PEOPLE_ITEMS:
            self.gender_combo.addItem(tr(key), data)
        self.person_preview = _PersonPreview()
        self.person_preview.setFixedSize(PREVIEW_PX, PREVIEW_PX)
        self.color_combo = QComboBox()
        for color in PALETTE:
            self.color_combo.addItem(color, color)
            index = self.color_combo.count() - 1
            self.color_combo.setItemData(
                index, _color_icon(color), Qt.ItemDataRole.DecorationRole
            )
        self.home_floor = QSpinBox()
        self.home_floor.setRange(1, 60)
        self.main_floor = QSpinBox()
        self.main_floor.setRange(1, 60)
        self.attendance = QDoubleSpinBox()
        self.attendance.setRange(0.0, 100.0)
        self.attendance.setDecimals(0)
        self.attendance.setSingleStep(5.0)
        self.jitter = QSpinBox()
        self.jitter.setRange(0, 120)
        self.companions = QSpinBox()
        self.companions.setRange(1, 20)
        self.abandon = QDoubleSpinBox()
        self.abandon.setRange(5.0, 600.0)
        self.abandon.setDecimals(0)
        self.arrive = QTimeEdit()
        self.arrive.setDisplayFormat("HH:mm")
        self.stay = QSpinBox()
        self.stay.setRange(1, 600)
        self.needs_meet = QCheckBox()

        self.weekday_boxes: dict[int, QCheckBox] = {}
        weekday_row = QWidget()
        weekday_layout = QHBoxLayout(weekday_row)
        weekday_layout.setContentsMargins(0, 0, 0, 0)
        weekday_layout.setSpacing(4)
        for day in range(1, 8):
            box = QCheckBox(tr(f"weekday.{day}"))
            self.weekday_boxes[day] = box
            weekday_layout.addWidget(box)
        weekday_layout.addStretch(1)

        form.addRow(self._label("profile.field.name"), self.name_edit)
        form.addRow(self._label("profile.field.kind"), self.kind_combo)
        form.addRow(self._label("profile.field.gender"), self._row_with_preview(
            self.gender_combo, self.person_preview
        ))
        form.addRow(self._label("profile.field.color"), self.color_combo)
        self.home_row = self._row("profile.field.home_floor", self.home_floor)
        self.main_row = self._row("profile.field.dest_floor", self.main_floor)
        form.addRow(*self.home_row)
        form.addRow(*self.main_row)
        form.addRow(self._label("profile.field.weekdays"), weekday_row)
        form.addRow(self._label("profile.field.attendance"), self.attendance)
        form.addRow(self._label("profile.field.jitter"), self.jitter)
        form.addRow(self._label("profile.field.companions"), self.companions)
        form.addRow(self._label("profile.field.abandon"), self.abandon)
        self.arrive_row = self._row("profile.field.arrive", self.arrive)
        self.stay_row = self._row("profile.field.stay", self.stay)
        form.addRow(*self.arrive_row)
        form.addRow(*self.stay_row)
        form.addRow(self._label("profile.field.needs_meet"), self.needs_meet)
        layout.addWidget(basic)

        self.legs_group = QGroupBox(tr("profile.legs.title"))
        legs_layout = QVBoxLayout(self.legs_group)
        legs_layout.setContentsMargins(10, 8, 10, 10)
        legs_layout.setSpacing(6)
        self.legs_table = QTableWidget(0, len(LEG_COLUMNS))
        self.legs_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.legs_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.legs_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.legs_table.verticalHeader().setVisible(False)
        self.legs_table.setMinimumHeight(140)
        legs_layout.addWidget(self.legs_table)
        leg_buttons = QHBoxLayout()
        self.leg_add_btn = QPushButton(tr("profile.legs.add"))
        self.leg_remove_btn = QPushButton(tr("profile.legs.remove"))
        leg_buttons.addWidget(self.leg_add_btn)
        leg_buttons.addWidget(self.leg_remove_btn)
        leg_buttons.addStretch(1)
        legs_layout.addLayout(leg_buttons)
        self.legs_hint = QLabel(tr("profile.legs.hint"))
        self.legs_hint.setWordWrap(True)
        self.legs_hint.setStyleSheet("color: #7b8194; font-size: 11px;")
        legs_layout.addWidget(self.legs_hint)
        layout.addWidget(self.legs_group)

        self.preview_group = QGroupBox(tr("profile.behavior"))
        preview_layout = QVBoxLayout(self.preview_group)
        preview_layout.setContentsMargins(10, 8, 10, 10)
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: #9fb4e8; font-size: 12px;")
        preview_layout.addWidget(self.preview_label)
        self.rationale_label = QLabel(tr("profile.rationale"))
        self.rationale_label.setWordWrap(True)
        self.rationale_label.setStyleSheet("color: #7b8194; font-size: 11px;")
        preview_layout.addWidget(self.rationale_label)
        layout.addWidget(self.preview_group)
        layout.addStretch(1)

        self.delete_btn.setEnabled(False)
        self.duplicate_btn.setEnabled(False)
        self.kind_combo.currentIndexChanged.connect(self._on_kind_changed)
        self.gender_combo.currentIndexChanged.connect(self._on_gender_changed)
        self.name_edit.editingFinished.connect(self._commit)
        self.color_combo.currentIndexChanged.connect(self._commit)
        for spin in (
            self.home_floor,
            self.main_floor,
            self.jitter,
            self.companions,
            self.stay,
        ):
            spin.valueChanged.connect(self._commit)
        for box in (self.attendance, self.abandon):
            box.valueChanged.connect(self._commit)
        self.arrive.timeChanged.connect(self._commit)
        self.needs_meet.toggled.connect(self._commit)
        for box in self.weekday_boxes.values():
            box.toggled.connect(self._commit)
        self.leg_add_btn.clicked.connect(self._add_leg)
        self.leg_remove_btn.clicked.connect(self._remove_leg)
        self.legs_table.itemChanged.connect(self._commit)
        return scroll

    def _label(self, key: str) -> QLabel:
        label = QLabel(tr(key))
        label.setProperty("i18n_key", key)
        return label

    def _row(self, key: str, widget: QWidget) -> tuple[QLabel, QWidget]:
        return self._label(key), widget

    def _row_with_preview(self, widget: QWidget, preview: QWidget) -> QWidget:
        """把控件和人物图形预览并排放进一个容器，供 QFormLayout 当作一个字段。"""
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(widget)
        row.addWidget(preview)
        row.addStretch(1)
        return holder

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget { background: #1f2027; color: #d7dbe6; font-size: 13px; }
            QGroupBox { border: 1px solid #34374a; border-radius: 6px; margin-top: 10px; padding-top: 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #9fb4e8; }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTimeEdit, QListWidget, QTableWidget {
                background: #14151a; border: 1px solid #34374a; border-radius: 4px;
                padding: 3px 6px; selection-background-color: #3d7ff5;
            }
            QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled, QTimeEdit:disabled {
                color: #7b8194; background: #191b21;
            }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background: #2b5fb8; }
            QLabel#buildingHint { color: #7b8194; font-size: 11px; }
            QLabel#sectionTitle {
                color: #9fb4e8; font-weight: bold; font-size: 12px;
                padding-top: 6px; border-top: 1px solid #2c2f3d; margin-top: 2px;
            }
            QLabel#mixTotal { color: #7b8194; font-size: 11px; }
            QLabel#populationWarn { color: #f5a623; font-size: 11px; }
            QLabel#batchTotal { color: #9fb4e8; font-weight: bold; }
            QPushButton {
                background: #2b5fb8; border: none; border-radius: 5px;
                padding: 6px 8px; color: white; font-weight: bold;
            }
            QPushButton:hover { background: #3d7ff5; }
            QPushButton:disabled { background: #3a3e4f; color: #7b8194; }
            QHeaderView::section { background: #14151a; color: #9aa3b8; border: none; padding: 4px; }
            QTableWidget { gridline-color: #2c2f3d; }
            QSplitter::handle { background: #34374a; }
            QScrollBar:vertical { background: #1f2027; width: 10px; }
            QScrollBar::handle:vertical { background: #3a3e4f; border-radius: 5px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #1f2027; }
            """
        )

    # ------------------------------------------------------------------ data
    def _clamp_spins(self) -> None:
        top = max(2, self.floors)
        for spin in (self.home_floor, self.main_floor):
            spin.setRange(1, top)

    def _clamp_stored(self) -> None:
        """楼层数变化时钳制已存画像的越界楼层，并落盘。"""
        top = max(2, self.floors)
        self._clamped_to = self.floors
        changed = False
        for profile in self.profiles:
            if profile.home_floor is not None and profile.home_floor > top:
                profile.home_floor = top
                changed = True
            if profile.main_floor is not None and profile.main_floor > top:
                profile.main_floor = top
                changed = True
            for leg in profile.legs:
                if leg.target_floor is not None and leg.target_floor > top:
                    leg.target_floor = top
                    changed = True
        if changed:
            self._persist()

    def current(self) -> PassengerProfile | None:
        row = self.list.currentRow()
        if row < 0:
            return None
        pid = self.list.item(row).data(Qt.ItemDataRole.UserRole)
        for profile in self.profiles:
            if profile.pid == pid:
                return profile
        return None

    def _visible_profiles(self) -> list[PassengerProfile]:
        text = self.search.text().strip().lower()
        kind_filter = self.filter_combo.currentData() or "all"
        result = []
        for profile in self.profiles:
            if kind_filter != "all" and profile.kind != kind_filter:
                continue
            if text and text not in profile.name.lower() and text not in profile.pid.lower():
                continue
            result.append(profile)
        return result

    def reload_list(self) -> None:
        self._loading = True
        keep = self.list.currentRow()
        selected = self.current()
        self.list.clear()
        for profile in self._visible_profiles():
            item = QListWidgetItem(self._item_text(profile))
            item.setData(Qt.ItemDataRole.UserRole, profile.pid)
            item.setForeground(QBrush(QColor(profile.color)))
            self.list.addItem(item)
        self.count_label.setText(tr("profile.count", n=len(self.profiles)))
        self._loading = False
        target = 0
        if selected is not None:
            for i in range(self.list.count()):
                if self.list.item(i).data(Qt.ItemDataRole.UserRole) == selected.pid:
                    target = i
                    break
        else:
            target = max(0, min(keep, self.list.count() - 1))
        if self.list.count():
            self.list.setCurrentRow(target)
        else:
            self._show_empty()
        self.profiles_changed.emit()

    def _item_text(self, profile: PassengerProfile) -> str:
        key = profile.summary_key()
        detail = tr(key, n=profile.visitor_stay if profile.kind == VISITOR else len(profile.legs))
        kind = tr("profile.filter.resident" if profile.kind == RESIDENT else "profile.filter.visitor")
        return f"{profile.pid}  {profile.name}   [{kind}]  {detail}"

    def _profile_widgets(self) -> tuple[QWidget, ...]:
        """编辑区里会随画像读写的控件。空状态与选中态共用同一份清单。"""
        return (
            self.name_edit,
            self.kind_combo,
            self.gender_combo,
            self.person_preview,
            self.color_combo,
            self.home_floor,
            self.main_floor,
            self.attendance,
            self.jitter,
            self.companions,
            self.abandon,
            self.arrive,
            self.stay,
        )

    def _show_empty(self) -> None:
        self._loading = True
        for widget in self._profile_widgets():
            widget.setEnabled(False)
        self.legs_table.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.duplicate_btn.setEnabled(False)
        self.person_preview.set_gender(MALE)
        self.preview_label.setText(tr("profile.empty"))
        self._loading = False

    def _on_select(self, _row: int) -> None:
        if self._loading:
            return
        profile = self.current()
        if profile is None:
            self._show_empty()
            return
        self._loading = True
        for widget in self._profile_widgets():
            widget.setEnabled(True)
        self.legs_table.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.duplicate_btn.setEnabled(True)
        self.name_edit.setText(profile.name)
        self.kind_combo.setCurrentIndex(max(0, self.kind_combo.findData(profile.kind)))
        gender = profile.gender if profile.gender in CATEGORY_COLORS else MALE
        index = self.gender_combo.findData(gender)
        self.gender_combo.setCurrentIndex(index if index >= 0 else 0)
        self.person_preview.set_gender(gender)
        color_index = self.color_combo.findText(profile.color)
        self.color_combo.setCurrentIndex(color_index if color_index >= 0 else 0)
        self._clamp_spins()
        self.home_floor.setValue(profile.home_floor or 2)
        # 住客不再存常去楼层，控件填派生值仅供切换成访客时预填
        self.main_floor.setValue(
            self._default_target(profile.home_floor or 2)
            if profile.kind == RESIDENT
            else (profile.main_floor or 2)
        )
        self.attendance.setValue((profile.attendance or 0.0) * 100.0)
        self.jitter.setValue(profile.jitter_min or 0)
        self.companions.setValue(profile.companions or 1)
        self.abandon.setValue(profile.abandon_sec or 60.0)
        self.arrive.setTime(QTime(0, 0).addSecs(int(profile.visitor_arrive or 0) * 60))
        self.stay.setValue(profile.visitor_stay or 60)
        self.needs_meet.setChecked(profile.needs_meet)
        for day, box in self.weekday_boxes.items():
            box.setChecked(day in profile.weekdays)
        self._load_legs(profile.legs)
        self._loading = False
        self._sync_kind_visibility(profile.kind)
        self._update_preview()

    def _load_legs(self, legs: list[TripLeg]) -> None:
        self.legs_table.blockSignals(True)
        self.legs_table.setRowCount(0)
        for leg in legs:
            self._append_leg_row(leg)
        self.legs_table.blockSignals(False)

    def _append_leg_row(self, leg: TripLeg) -> None:
        row = self.legs_table.rowCount()
        self.legs_table.insertRow(row)

        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        time_edit.setTime(QTime(0, 0).addSecs(int(leg.time_min or 0) * 60))
        time_edit.setMinimumHeight(26)
        time_edit.setStyleSheet("padding: 1px 3px;")
        self.legs_table.setCellWidget(row, 0, time_edit)

        floor_box = QSpinBox()
        floor_box.setRange(1, max(2, self.floors))
        floor_box.setValue(leg.target_floor or 1)
        floor_box.setMinimumHeight(26)
        floor_box.setStyleSheet("padding: 1px 3px;")
        self.legs_table.setCellWidget(row, 1, floor_box)

        stay_box = QSpinBox()
        stay_box.setRange(0, 1440)
        stay_box.setValue(leg.stay_min or 0)
        stay_box.setMinimumHeight(26)
        stay_box.setStyleSheet("padding: 1px 3px;")
        self.legs_table.setCellWidget(row, 2, stay_box)

        # cellWidget 不是 table item，itemChanged 收不到，必须单独接线
        time_edit.timeChanged.connect(self._commit)
        floor_box.valueChanged.connect(self._commit)
        stay_box.valueChanged.connect(self._commit)

    def _read_legs(self) -> list[TripLeg]:
        legs: list[TripLeg] = []
        for row in range(self.legs_table.rowCount()):
            time_edit = self.legs_table.cellWidget(row, 0)
            floor_box = self.legs_table.cellWidget(row, 1)
            stay_box = self.legs_table.cellWidget(row, 2)
            if not isinstance(time_edit, QTimeEdit):
                continue
            legs.append(
                TripLeg(
                    time_min=time_edit.time().hour() * 60 + time_edit.time().minute(),
                    target_floor=floor_box.value() if floor_box else None,
                    stay_min=stay_box.value() if stay_box else None,
                )
            )
        return legs

    def _default_target(self, home_floor: int) -> int:
        """新增行程的默认目标层。

        住宅楼：居住层与外出层之间取大堂；商务楼：从大堂去办公层，
        因此目标层取当前楼层之上一层。
        """
        top = max(2, self.floors)
        if resident_template(self.building).target == "lobby":
            return 2 if home_floor <= 1 else 1
        return min(top, max(2, home_floor + 1))

    def _add_leg(self) -> None:
        if self._loading:
            return
        profile = self.current()
        home = (profile.home_floor if profile else None) or 2
        self.legs_table.blockSignals(True)
        self._append_leg_row(
            TripLeg(
                time_min=12 * 60,
                target_floor=self._default_target(home),
                stay_min=60,
            )
        )
        self.legs_table.blockSignals(False)
        self._commit()

    def _remove_leg(self) -> None:
        if self._loading:
            return
        row = self.legs_table.currentRow()
        if row < 0:
            row = self.legs_table.rowCount() - 1
        if row < 0:
            return
        self.legs_table.blockSignals(True)
        self.legs_table.removeRow(row)
        self.legs_table.blockSignals(False)
        self._commit()

    def _on_kind_changed(self, _index: int) -> None:
        if self._loading:
            return
        kind = self.kind_combo.currentData() or RESIDENT
        self._sync_kind_visibility(kind)
        self._commit()

    def _on_gender_changed(self, _index: int) -> None:
        """切人群分类：先更新大号图形预览，再落盘。"""
        if self._loading:
            return
        self.person_preview.set_gender(self.gender_combo.currentData() or MALE)
        self._commit()

    def _sync_kind_visibility(self, kind: str) -> None:
        is_resident = kind == RESIDENT
        self.home_row[0].setVisible(is_resident)
        self.home_floor.setVisible(is_resident)
        self.legs_group.setVisible(is_resident)
        self.arrive_row[0].setVisible(not is_resident)
        self.arrive.setVisible(not is_resident)
        self.stay_row[0].setVisible(not is_resident)
        self.stay.setVisible(not is_resident)
        # 住客的常去楼层已移除，目的层由日程逐段决定
        self.main_row[0].setVisible(not is_resident)
        self.main_floor.setVisible(not is_resident)

    # --------------------------------------------------------------- actions
    def add(self, kind: str) -> None:
        index = self.store.next_index()
        raw = new_profile(kind, "", index, self.seed)
        # 姓名参与随机种子，必须先定名再回填，否则画像属性与身份不自洽
        raw.name = f"{'住客' if kind == RESIDENT else '访客'}{index:03d}"
        # 创建时即随机补全并落盘：画像从诞生起就是完整数据
        profile = fill_defaults(raw, self.floors, self.seed, self.building)
        self.profiles.append(profile)
        self._persist()
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.filter_combo.setCurrentIndex(0)
        self.reload_list()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.ItemDataRole.UserRole) == profile.pid:
                self.list.setCurrentRow(i)
                break
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def _do_batch(self) -> None:
        mode = self.batch_mode.currentData() or "uniform"
        start = self.store.next_index()
        population = self.population
        if population.total <= 0:
            return
        new_profiles = make_batch(
            start_index=start,
            base_seed=self.seed,
            floors=self.floors,
            building=self.building,
            floor_mode=mode,
            population=population,
        )
        self.profiles.extend(new_profiles)
        self._persist()
        self.batch_row.setVisible(False)
        self.reload_list()

    def duplicate(self) -> None:
        profile = self.current()
        if profile is None:
            return
        index = self.store.next_index()
        copy = profile.clone()
        copy.pid = f"P{index:03d}"
        copy.name = f"{profile.name} 2"
        # 保留原画像已随机好的行程/参数，仅换身份
        self.profiles.append(fill_defaults(copy, self.floors, self.seed, self.building))
        self._persist()
        self.reload_list()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.ItemDataRole.UserRole) == copy.pid:
                self.list.setCurrentRow(i)
                break

    def delete_current(self) -> None:
        profile = self.current()
        if profile is None:
            return
        self.profiles = [p for p in self.profiles if p.pid != profile.pid]
        self._persist()
        self.reload_list()

    def _commit(self) -> None:
        if self._loading:
            return
        profile = self.current()
        if profile is None:
            return
        profile.name = self.name_edit.text().strip() or profile.pid
        profile.kind = self.kind_combo.currentData() or RESIDENT
        profile.gender = self.gender_combo.currentData() or MALE
        profile.color = self.color_combo.currentText() or PALETTE[0]
        profile.attendance = self.attendance.value() / 100.0
        profile.jitter_min = self.jitter.value()
        profile.companions = self.companions.value()
        profile.abandon_sec = self.abandon.value()
        profile.weekdays = [
            day for day, box in sorted(self.weekday_boxes.items()) if box.isChecked()
        ]
        profile.needs_meet = self.needs_meet.isChecked()
        top = max(2, self.floors)
        if profile.kind == RESIDENT:
            profile.home_floor = min(top, max(1, self.home_floor.value()))
            profile.main_floor = None
            # 刻意保留空行程：住客日程为空即表示其从不出行
            profile.legs = self._read_legs()
            profile.visitor_arrive = None
            profile.visitor_stay = None
        else:
            profile.home_floor = None
            profile.main_floor = min(top, max(1, self.main_floor.value()))
            profile.visitor_arrive = self.arrive.time().hour() * 60 + self.arrive.time().minute()
            profile.visitor_stay = self.stay.value()
            profile.legs = []
        self._persist()
        row = self.list.currentRow()
        if 0 <= row < self.list.count():
            item = self.list.item(row)
            item.setText(self._item_text(profile))
            item.setForeground(QBrush(QColor(profile.color)))
        self._update_preview()

    def _persist(self) -> None:
        self.store.building = self.building
        try:
            self.store.save(self.profiles)
        except OSError:
            pass
        self.profiles_changed.emit()

    def _update_preview(self) -> None:
        profile = self.current()
        if profile is None:
            return
        resolved = resolve(profile, self.floors, self.seed)
        lines: list[str] = []
        position = resolved.home_floor or 1
        if resolved.kind == RESIDENT:
            for leg in resolved.legs:
                if leg.target_floor != position:
                    lines.append(
                        f"{_hhmm(leg.time_min)}   {position} → {leg.target_floor}"
                    )
                    position = leg.target_floor
            if resolved.legs and position != (resolved.home_floor or 1):
                last = resolved.legs[-1]
                lines.append(
                    f"{_hhmm(int(last.time_min or 0) + int(last.stay_min or 0))}"
                    f"   {position} → {resolved.home_floor}"
                )
        else:
            delay = 5 if resolved.needs_meet else 0
            up = int(resolved.visitor_arrive or 0) + delay
            lines.append(f"{_hhmm(up)}   1 → {resolved.main_floor}")
            lines.append(
                f"{_hhmm(up + int(resolved.visitor_stay or 0))}   {resolved.main_floor} → 1"
            )
        suffix = f"  ×{resolved.companions}" if resolved.companions > 1 else ""
        self.preview_label.setText(
            ("\n".join(lines) + suffix) if lines else tr("profile.behavior.empty")
        )

    def retranslate(self) -> None:
        self.search.setPlaceholderText(tr("profile.search"))
        for combo, items in (
            (self.building_combo, [(f"building.{k}", k) for k in BUILDING_TYPES]),
            (self.filter_combo, FILTER_ITEMS),
            (self.group_combo, GROUP_ITEMS),
            (self.kind_combo, KIND_ITEMS),
            (self.gender_combo, PEOPLE_ITEMS),
            (self.batch_mode, BATCH_MODE_ITEMS),
        ):
            data = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            for key, value in items:
                combo.addItem(tr(key), value)
            index = combo.findData(data)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)
        # 商务楼里「住客」的语义是员工，标签随楼型切换
        self._sync_kind_labels()
        self.add_visitor_btn.setText(tr("profile.add_visitor"))
        self.batch_mode_label.setText(tr("profile.batch.floor_mode"))
        self.occupants_range_label.setText("–")
        self.building_box.setTitle(tr("building.title"))
        self.building_hint.setText(tr("building.hint"))
        self.capacity_title.setText(tr("building.capacity_title"))
        self.mix_title.setText(tr("building.mix_title"))
        self.mix_hint.setText(tr("building.mix.hint"))
        for kind, label in self.mix_labels.items():
            # 带色块的富文本标签不走通用 i18n 循环，单独重建
            label.setText(_swatch_label(kind))
            self.mix_spins[kind].setToolTip(tr(label_key(kind)))
        for label, key in self.capacity_labels:
            label.setText(tr(key))
        for label, key in self.behavior_labels:
            label.setText(tr(key))
        self._refresh_population()
        self.batch_btn.setText(tr("profile.batch"))
        self.duplicate_btn.setText(tr("profile.duplicate"))
        self.delete_btn.setText(tr("profile.delete"))
        self.batch_confirm.setText(tr("settings.apply"))
        self.leg_add_btn.setText(tr("profile.legs.add"))
        self.leg_remove_btn.setText(tr("profile.legs.remove"))
        self.legs_hint.setText(tr("profile.legs.hint"))
        self.rationale_label.setText(tr("profile.rationale"))
        for label in self.findChildren(QLabel):
            key = label.property("i18n_key")
            if key:
                label.setText(tr(key))
        for day, box in self.weekday_boxes.items():
            box.setText(tr(f"weekday.{day}"))
        group_boxes = self.findChildren(QGroupBox)
        for box, key in zip(group_boxes, ["profile.title", "profile.legs.title", "profile.behavior"]):
            box.setTitle(tr(key))
        for col, key in enumerate(LEG_COLUMNS):
            self.legs_table.setHorizontalHeaderItem(col, QTableWidgetItem(tr(key)))
        self.count_label.setText(tr("profile.count", n=len(self.profiles)))
        # 可见列表只算一次：人数上千时逐项重算会退化成 O(n²)
        visible = self._visible_profiles()
        for i in range(min(self.list.count(), len(visible))):
            self.list.item(i).setText(self._item_text(visible[i]))
        self._sync_kind_visibility(self.kind_combo.currentData() or RESIDENT)
        self._update_preview()


def _color_icon(color: str) -> object:
    from PySide6.QtGui import QIcon, QPixmap

    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)
