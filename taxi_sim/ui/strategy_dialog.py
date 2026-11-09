"""策略方案编辑对话框: 名称 + 类型 + 参数(数值/场站下拉)。"""
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFormLayout, QLineEdit,
                               QVBoxLayout)

from i18n import t
from sim.strategies import STRATEGY_DEFS, STATIONS


class StrategyDialog(QDialog):
    """编辑/新建一个策略方案; exec() 后用 result_scheme() 取结果。"""

    def __init__(self, scheme=None, city_key=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("strat.dlg.title"))
        self.setMinimumWidth(340)
        self.city_key = city_key
        self._scheme = dict(scheme or {})
        self._station_combo = None

        lay = QVBoxLayout(self)
        form = QFormLayout()
        lay.addLayout(form)

        self.name_edit = QLineEdit(self._scheme.get("name", ""))
        form.addRow(t("strat.dlg.name"), self.name_edit)

        self.type_combo = QComboBox()
        self._type_items = []
        for stype in STRATEGY_DEFS:
            self.type_combo.addItem(t(f"strategy.{stype}"), stype)
            self._type_items.append(stype)
        cur = self._scheme.get("type", "random")
        idx = self._type_items.index(cur) if cur in self._type_items else 0
        self.type_combo.setCurrentIndex(idx)
        self._type = self.type_combo.currentData()
        form.addRow(t("strat.dlg.type"), self.type_combo)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)

        self._param_form = QFormLayout()
        form.addRow(self._param_form)
        self._build_params(self._scheme.get("params") or {})

        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

    def _on_type_changed(self):
        self._type = self.type_combo.currentData()
        self._build_params({})

    def _clear_form(self):
        while self._param_form.rowCount():
            self._param_form.removeRow(0)
        self._station_combo = None

    def _build_params(self, params):
        self._clear_form()
        cls = STRATEGY_DEFS[self._type]
        for key, (default, lo, hi) in cls.PARAMS.items():
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setSingleStep((hi - lo) / 100.0)
            spin.setDecimals(2 if hi > 1 else 4)
            try:
                spin.setValue(float(params.get(key, default)))
            except (TypeError, ValueError):
                spin.setValue(default)
            setattr(self, f"_p_{key}", spin)
            self._param_form.addRow(t(f"strat.p.{key}"), spin)
        if self._type == "station":
            self._build_station(params)

    def _build_station(self, params):
        stations = list(STATIONS.get(self.city_key or "", []))
        cur_lat = float(params.get("station_lat") or 0)
        cur_lng = float(params.get("station_lng") or 0)
        self._station_combo = QComboBox()
        for name, lat, lng in stations:
            self._station_combo.addItem(name, (name, lat, lng))
        self._station_combo.addItem(t("strat.p.station_custom"), None)
        match_idx = -1
        for i in range(self._station_combo.count()):
            data = self._station_combo.itemData(i)
            if data and abs(data[1] - cur_lat) < 1e-4 \
                    and abs(data[2] - cur_lng) < 1e-4:
                match_idx = i
                break
        if match_idx >= 0:
            self._station_combo.setCurrentIndex(match_idx)
        elif cur_lat or cur_lng:
            self._station_combo.setCurrentIndex(self._station_combo.count() - 1)
        self._param_form.addRow(t("strat.p.station"), self._station_combo)
        self._lat_edit = QLineEdit(f"{cur_lat:g}" if cur_lat else "")
        self._lng_edit = QLineEdit(f"{cur_lng:g}" if cur_lng else "")
        self._param_form.addRow(t("strat.p.station_lat"), self._lat_edit)
        self._param_form.addRow(t("strat.p.station_lng"), self._lng_edit)
        self._station_combo.currentIndexChanged.connect(
            lambda _i: self._sync_station_fields())
        self._sync_station_fields()

    def _sync_station_fields(self):
        data = self._station_combo.currentData() if self._station_combo else None
        if data:
            _, lat, lng = data
            self._lat_edit.setText(f"{lat:g}")
            self._lng_edit.setText(f"{lng:g}")
            self._lat_edit.setEnabled(False)
            self._lng_edit.setEnabled(False)
        else:
            self._lat_edit.setEnabled(True)
            self._lng_edit.setEnabled(True)

    def result_scheme(self):
        cls = STRATEGY_DEFS[self._type]
        params = {}
        for key in cls.PARAMS:
            params[key] = getattr(self, f"_p_{key}").value()
        if self._type == "station" and self._station_combo is not None:
            data = self._station_combo.currentData()
            if data:                     # 内置场站
                name, lat, lng = data
                params.update(station_name=name, station_lat=lat,
                              station_lng=lng)
            else:                        # 自定义坐标: 手填经纬度
                try:
                    lat = float(self._lat_edit.text() or 0)
                except ValueError:
                    lat = 0.0
                try:
                    lng = float(self._lng_edit.text() or 0)
                except ValueError:
                    lng = 0.0
                params.update(station_name="", station_lat=lat, station_lng=lng)
        name = self.name_edit.text().strip() or t(f"strategy.{self._type}")
        return {"name": name, "type": self._type, "params": params}

