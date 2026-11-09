"""主窗口: 左侧地图 + 右侧控制面板(城市/数量/策略/速度/统计/配额/日志)。
全部文案走 i18n, 语言由 config.ini 的 language 决定。
"""
import threading

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox,
                               QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMainWindow, QPushButton,
                               QSpinBox, QTextEdit, QVBoxLayout, QWidget)

from i18n import t
from data import locate as locator
from sim.city import CITIES, CURRENT, city_from_location, get_city
from ui.map_bridge import MapBridge
from ui.settings_dialog import SettingsDialog
from ui.strategy_dialog import StrategyDialog


class MainWindow(QMainWindow):
    locationReady = Signal(object)   # 定位结果 (lat, lng, source) 或 None

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

        self._located = self._load_located()
        self._locating = False
        self.locationReady.connect(self._on_location_ready)
        self.map.load_city(self._current_city_obj())
        self._quota_cache = []
        self._refresh_ui_ready()
        if self.config.any_key:
            QTimer.singleShot(300, self.locate_now)   # 启动后自动定位一次

    # ---------------- 定位 ----------------

    def _load_located(self):
        lat, lng = self.config.located_lat, self.config.located_lng
        return (lat, lng) if lat is not None and lng is not None else None

    def _current_city_obj(self):
        if self.config.city == CURRENT and self._located:
            return get_city(CURRENT, *self._located)
        return get_city(self.config.city)

    def locate_now(self):
        """后台线程获取当前坐标(不阻塞界面)。"""
        if self._locating:
            return
        self._locating = True
        self._log(t("msg.locating"))
        threading.Thread(target=self._locate_worker, daemon=True).start()

    def _locate_worker(self):
        try:
            res = locator.locate(self.config)
        except Exception:
            res = None
        self.locationReady.emit(res)

    def _on_location_ready(self, res):
        self._locating = False
        if not res:
            self._log(t("msg.locate_failed"))
            return
        lat, lng = res[0], res[1]
        self._located = (lat, lng)
        city, hit = city_from_location(lat, lng)
        if self.engine.timer.isActive() and self.engine.city.name != city.name:
            self.stop_sim()
        self.config.set_general(city=city.name, located_lat=f"{lat:.6f}",
                                located_lng=f"{lng:.6f}")
        self.config.save()
        idx = self.city_combo.findData(city.name)
        if idx >= 0:
            self.city_combo.blockSignals(True)
            self.city_combo.setCurrentIndex(idx)
            self.city_combo.blockSignals(False)
        self.map.load_city(city)
        self._log(t("msg.located_hit", city=city.display_name) if hit
                  else t("msg.located_temp", lat=lat, lng=lng))

    # ---------------- 就绪状态(配置不全时锁定界面) ----------------

    def _refresh_ui_ready(self):
        """config.ini 中未配置任何地图 Key 时, 禁用全部控制按钮。"""
        ready = self.config.any_key
        for w in (self.btn_start, self.city_combo, self.taxi_spin,
                  self.pax_spin, self.speed_combo, self.shift_spin,
                  self.strat_list):
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
        self.city_combo.addItem(t("city.current"), CURRENT)
        for k, c in CITIES.items():
            self.city_combo.addItem(c.display_name, k)
        idx = self.city_combo.findData(self.config.city)
        if idx >= 0:
            self.city_combo.setCurrentIndex(idx)
        self.city_combo.currentIndexChanged.connect(self._on_city_changed)
        row1.addWidget(self.city_combo)

        self.btn_locate = QPushButton("📍")
        self.btn_locate.setToolTip(t("panel.locate"))
        self.btn_locate.setFixedWidth(30)
        self.btn_locate.clicked.connect(self.locate_now)
        row1.addWidget(self.btn_locate)
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

        row1c = QHBoxLayout()
        row1c.addWidget(QLabel(t("panel.shift")))
        self.shift_spin = QDoubleSpinBox()
        self.shift_spin.setRange(0.25, 8.0)
        self.shift_spin.setSingleStep(0.25)
        self.shift_spin.setDecimals(2)
        self.shift_spin.setValue(self.config.shift_hours)
        self.shift_spin.setToolTip(t("panel.shift"))
        row1c.addWidget(self.shift_spin)
        self.follow_check = QCheckBox(t("panel.follow"))
        self.follow_check.setChecked(self.config.follow_mode)
        self.follow_check.toggled.connect(self._on_follow_toggled)
        row1c.addWidget(self.follow_check)
        row1c.addStretch(1)
        f1.addLayout(row1c)

        # 策略方案: 列表(勾选启用) + 增/编/删
        f1.addWidget(QLabel(t("strat.hint")))
        self.strat_list = QListWidget()
        self.strat_list.setMaximumHeight(120)
        f1.addWidget(self.strat_list)
        self._load_schemes()
        row_strat = QHBoxLayout()
        for key, tip in (("strat.add", "strat.add_tip"),
                         ("strat.edit", "strat.edit_tip"),
                         ("strat.del", "strat.del_tip")):
            btn = QPushButton(t(key))
            btn.setToolTip(t(tip))
            btn.setFixedWidth(60)
            btn.clicked.connect(
                self._on_strat_add if key == "strat.add"
                else (self._on_strat_edit if key == "strat.edit"
                      else self._on_strat_del))
            row_strat.addWidget(btn)
        row_strat.addStretch(1)
        f1.addLayout(row_strat)

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

        gb5 = QGroupBox(t("panel.strat_cmp"))
        f5 = QVBoxLayout(gb5)
        self.strat_cmp_list = QListWidget()
        f5.addWidget(self.strat_cmp_list)
        lay.addWidget(gb5)

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
            idx = self.city_combo.findData(self.config.city)
            if idx >= 0:
                self.city_combo.blockSignals(True)
                self.city_combo.setCurrentIndex(idx)
                self.city_combo.blockSignals(False)
            self._located = self._load_located()
            self.map.load_city(self._current_city_obj())

    def _on_city_changed(self, _index=None):
        """切换城市: 立即重载地图; 若仿真在跑, 先停止避免新旧城市数据混用。"""
        city_key = self.city_combo.currentData()
        if not city_key or city_key == self.config.city:
            return
        if city_key == CURRENT:
            if not self._located:
                self._log(t("msg.locate_need"))
                self.locate_now()
                return
            city = get_city(CURRENT, *self._located)
        else:
            city = get_city(city_key)
        if self.engine.timer.isActive():
            self.stop_sim()
        self.config.set_general(city=city_key)
        self.config.save()
        self.map.load_city(city)
        self._log(t("msg.city_switched", city=city.display_name))

    # ---------------- 仿真控制 ----------------

    def _on_follow_toggled(self, checked):
        self.config.set_general(follow_mode=int(checked))
        self.config.save()

    # ---------------- 策略方案管理 ----------------

    def _load_schemes(self):
        self.strat_list.clear()
        for s in self.config.get_strategies():
            item = QListWidgetItem(f"{s['name']} ({t('strategy.' + s['type'])})")
            item.setData(Qt.UserRole, s)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if s.get("enabled") else Qt.Unchecked)
            self.strat_list.addItem(item)

    def _schemes_from_ui(self):
        out = []
        for i in range(self.strat_list.count()):
            item = self.strat_list.item(i)
            s = dict(item.data(Qt.UserRole))
            s["enabled"] = (item.checkState() == Qt.Checked)
            out.append(s)
        return out

    def _on_strat_add(self):
        dlg = StrategyDialog(city_key=self.config.city, parent=self)
        if not dlg.exec():
            return
        schemes = self._schemes_from_ui()
        schemes.append(dlg.result_scheme())
        self.config.set_strategies(schemes)
        self.config.save()
        self._load_schemes()

    def _on_strat_edit(self):
        row = self.strat_list.currentRow()
        if row < 0:
            return
        dlg = StrategyDialog(scheme=self.strat_list.item(row).data(Qt.UserRole),
                             city_key=self.config.city, parent=self)
        if not dlg.exec():
            return
        schemes = self._schemes_from_ui()
        schemes[row] = dlg.result_scheme()
        self.config.set_strategies(schemes)
        self.config.save()
        self._load_schemes()

    def _on_strat_del(self):
        row = self.strat_list.currentRow()
        if row < 0:
            return
        schemes = self._schemes_from_ui()
        del schemes[row]
        self.config.set_strategies(schemes)
        self.config.save()
        self._load_schemes()

    # ---------------- 仿真控制 ----------------

    def start_sim(self):
        city_key = self.city_combo.currentData()
        schemes = [s for s in self._schemes_from_ui() if s["enabled"]]
        if not schemes:
            self._log(t("msg.need_strategy"))
            return
        if city_key == CURRENT:
            if not self._located:
                self._log(t("msg.locate_need"))
                self.locate_now()
                return
            city = get_city(CURRENT, *self._located)
        else:
            city = get_city(city_key)
        if self.map.current_city != city.name:
            self.map.load_city(city)
        self.config.set_general(
            city=city_key,
            default_taxi_count=self.taxi_spin.value(),
            default_passenger_count=self.pax_spin.value(),
            speed_multiplier=self.speed_combo.currentData(),
            shift_hours=self.shift_spin.value())
        self.config.set_strategies(self._schemes_from_ui())
        self.config.save()
        self.engine.config = self.config
        self.engine.start(self.taxi_spin.value(), schemes, city=city)
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
        # 策略对比行(每秒刷新一次)
        self.strat_cmp_list.clear()
        rows = s.get("strategies") or []
        if not rows:
            self.strat_cmp_list.addItem(t("strat.cmp.empty"))
        for r in rows:
            item = QListWidgetItem("")
            lab = QLabel(t("strat.cmp.row", name=t("strategy." + r["name"]),
                           taxis=r["taxis"], orders=r["orders"],
                           income=r["income"], empty=r["empty_ratio"] * 100,
                           wait=r["avg_wait"]))
            self.strat_cmp_list.addItem(item)
            self.strat_cmp_list.setItemWidget(item, lab)
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
