"""主窗口: 左侧地图 + 右侧控制面板(城市/数量/策略/速度/统计/配额/日志)。
全部文案走 i18n, 语言由 config.ini 的 language 决定。
"""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QMainWindow, QPushButton, QSpinBox, QTextEdit,
                               QVBoxLayout, QWidget)

from i18n import t
from sim.city import CITIES, get_city
from ui.map_bridge import MapBridge
from ui.settings_dialog import SettingsDialog

STRATEGY_KEYS = ("random", "snake", "hotspot")


class MainWindow(QMainWindow):
    def __init__(self, config, manager, engine):
        super().__init__()
        self.config = config
        self.manager = manager
        self.engine = engine
        self.setWindowTitle(t("app.title"))
        self.resize(1280, 800)

        central = QWidget()
        root = QHBoxLayout(central)
        self.map = MapBridge(config)
        root.addWidget(self.map, 1)
        root.addWidget(self._build_panel())
        self.setCentralWidget(central)
        self._build_menu()

        self.engine.statsUpdated.connect(self._on_stats)
        self.engine.logMessage.connect(self._log)

        self.push_timer = QTimer(self)
        self.push_timer.setInterval(200)
        self.push_timer.timeout.connect(self._push_state)

        self.map.load_city(get_city(self.config.city))
        self._quota_cache = []
        self._refresh_ui_ready()

    # ---------------- 就绪状态(配置不全时锁定界面) ----------------

    def _refresh_ui_ready(self):
        """config.ini 中未配置任何地图 Key 时, 禁用全部控制按钮。"""
        ready = self.config.any_key
        for w in (self.btn_start, self.city_combo, self.taxi_spin,
                  self.pax_spin, self.speed_combo,
                  *self.strat_checks.values()):
            w.setEnabled(ready)
        if not ready:
            self.btn_stop.setEnabled(False)
            self._log(t("msg.config_incomplete"))

    # ---------------- 右侧面板 ----------------

    def _build_panel(self):
        panel = QWidget()
        panel.setFixedWidth(320)
        lay = QVBoxLayout(panel)

        gb1 = QGroupBox(t("panel.control"))
        f1 = QVBoxLayout(gb1)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel(t("panel.city")))
        self.city_combo = QComboBox()
        for k, c in CITIES.items():
            self.city_combo.addItem(c.display_name, k)
        if self.config.city in CITIES:
            self.city_combo.setCurrentIndex(list(CITIES).index(self.config.city))
        row1.addWidget(self.city_combo)
        row1.addWidget(QLabel(t("panel.taxis")))
        self.taxi_spin = QSpinBox()
        self.taxi_spin.setRange(1, 200)
        self.taxi_spin.setValue(self.config.taxi_count)
        row1.addWidget(self.taxi_spin)
        f1.addLayout(row1)

        row1b = QHBoxLayout()
        row1b.addWidget(QLabel(t("panel.passengers")))
        self.pax_spin = QSpinBox()
        self.pax_spin.setRange(1, 2000)
        self.pax_spin.setValue(self.config.passenger_count)
        row1b.addWidget(self.pax_spin)
        row1b.addWidget(QLabel(t("panel.speed")))
        self.speed_combo = QComboBox()
        for v in (1, 2, 4, 8, 16):
            self.speed_combo.addItem(f"×{v}", v)
        cur = int(self.config.speed_multiplier)
        if cur in (1, 2, 4, 8, 16):
            self.speed_combo.setCurrentIndex((1, 2, 4, 8, 16).index(cur))
        row1b.addWidget(self.speed_combo)
        f1.addLayout(row1b)

        f1.addWidget(QLabel(t("panel.strategy_hint")))
        self.strat_checks = {}
        for name in STRATEGY_KEYS:
            cb = QCheckBox(t(f"strategy.{name}"))
            cb.setChecked(True)
            self.strat_checks[name] = cb
            f1.addWidget(cb)

        row2 = QHBoxLayout()
        self.btn_start = QPushButton(t("btn.start"))
        self.btn_stop = QPushButton(t("btn.stop"))
        self.btn_stop.setEnabled(False)
        self.btn_start.clicked.connect(self.start_sim)
        self.btn_stop.clicked.connect(self.stop_sim)
        row2.addWidget(self.btn_start)
        row2.addWidget(self.btn_stop)
        f1.addLayout(row2)
        lay.addWidget(gb1)

        gb2 = QGroupBox(t("panel.stats"))
        f2 = QFormLayout(gb2)
        self.stat_labels = {}
        for key in ("sim_time", "delivered", "waiting", "avg_wait",
                    "empty_ratio", "pool"):
            lab = QLineEdit("0")
            lab.setReadOnly(True)
            self.stat_labels[key] = lab
            f2.addRow(f"{t(f'stats.{key}')}:", lab)
        lay.addWidget(gb2)

        gb3 = QGroupBox(t("quota.group"))
        f3 = QVBoxLayout(gb3)
        self.quota_list = QListWidget()
        f3.addWidget(self.quota_list)
        lay.addWidget(gb3)

        gb4 = QGroupBox(t("log.group"))
        f4 = QVBoxLayout(gb4)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(140)
        f4.addWidget(self.log_edit)
        lay.addWidget(gb4)
        lay.addStretch(1)
        return panel

    def _build_menu(self):
        menu = self.menuBar().addMenu(t("menu.system"))
        act = menu.addAction(t("menu.settings"))
        act.triggered.connect(self.open_settings)

    def open_settings(self):
        dlg = SettingsDialog(self.config, self.manager, self.map, self)
        accepted = dlg.exec()
        self._refresh_ui_ready()
        if accepted:
            self._log(t("msg.config_saved"))
            city = get_city(self.config.city)
            if self.config.city in CITIES:
                self.city_combo.setCurrentIndex(
                    list(CITIES).index(self.config.city))
            self.map.load_city(city)

    # ---------------- 仿真控制 ----------------

    def start_sim(self):
        city_key = self.city_combo.currentData()
        strategies = [n for n, cb in self.strat_checks.items() if cb.isChecked()]
        if not strategies:
            self._log(t("msg.need_strategy"))
            return
        if get_city(self.config.city).name != city_key:
            self.config.set_general(city=city_key)
            self.config.save()
            self.map.load_city(get_city(city_key))
        self.config.set_general(
            default_taxi_count=self.taxi_spin.value(),
            default_passenger_count=self.pax_spin.value(),
            speed_multiplier=self.speed_combo.currentData())
        self.config.save()
        self.engine.config = self.config
        self.engine.start(self.taxi_spin.value(), strategies)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.push_timer.start()

    def stop_sim(self):
        self.engine.stop()
        self.push_timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._log(t("msg.sim_stopped"))

    def _push_state(self):
        self.map.push_state(self.engine.snapshot_state())

    # ---------------- 信号 ----------------

    def _on_stats(self, s):
        for key, lab in self.stat_labels.items():
            lab.setText(str(s.get(key, "-")))
        quota = s.get("quota") or []
        sig = str([(q["provider"], q["used"]) for q in quota])
        if quota and sig != str(self._quota_cache and
                                [(q["provider"], q["used"])
                                 for q in self._quota_cache]):
            self._quota_cache = quota
            self.quota_list.clear()
            for q in quota:
                remain = max(0, q["limit"] - q["used"])
                src = t("quota.learned") if q["learned"] else t("quota.estimated")
                color = "#d32f2f" if remain == 0 else "#2e7d32"
                item = QLabel(t("quota.item", provider=q["provider"],
                                remain=remain, limit=q["limit"], src=src))
                item.setStyleSheet(f"color:{color}")
                self.quota_list.addItem("")
                self.quota_list.setItemWidget(
                    self.quota_list.item(self.quota_list.count() - 1), item)

    def _log(self, msg):
        self.log_edit.append(msg)
