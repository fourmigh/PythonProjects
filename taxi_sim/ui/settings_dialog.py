"""设置界面: 只需填写 Key, 配额由系统自动学习; 附官网申请页跳转与在线测试Key。
全部文案走 i18n; 语言选项在"通用"页, 保存后重启生效。
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFormLayout, QLabel,
                               QLineEdit, QPushButton, QSpinBox, QTabWidget,
                               QVBoxLayout, QWidget)

from i18n import SUPPORTED, current_language, t
from sim.city import CITIES

LINK_URLS = {
    "amap": [
        ("link.amap.apply", "https://console.amap.com/dev/key/app"),
        ("link.amap.quota", "https://console.amap.com/dev/quota"),
    ],
    "tencent": [
        ("link.tencent.apply", "https://lbs.qq.com/dev/console/application/mine"),
        ("link.tencent.quota", "https://lbs.qq.com/dev/console/quotaManage"),
    ],
    "baidu": [
        ("link.baidu.apply", "https://lbsyun.baidu.com/apiconsole/key"),
        ("link.baidu.quota", "https://lbsyun.baidu.com/apiconsole/key/overview"),
    ],
}


class SettingsDialog(QDialog):
    def __init__(self, config, manager, map_bridge, parent=None):
        super().__init__(parent)
        self.config = config
        self.manager = manager
        self.map_bridge = map_bridge
        self.setWindowTitle(t("settings.title"))
        self.resize(560, 480)
        self._build()

    # ---------------- 组件构造 ----------------

    def _link_label(self, text_key, url):
        lab = QLabel(f'<a href="{url}">{t(text_key)}</a>')
        lab.setTextFormat(Qt.RichText)
        lab.setOpenExternalLinks(True)
        return lab

    def _provider_tab(self, name):
        w = QWidget()
        form = QFormLayout(w)
        ed = {}
        if name == "amap":
            ed["web_key"] = QLineEdit(self.config.amap_web_key)
            ed["web_key"].setEchoMode(QLineEdit.Password)
            ed["js_key"] = QLineEdit(self.config.amap_js_key)
            ed["js_key"].setEchoMode(QLineEdit.Password)
            ed["js_code"] = QLineEdit(self.config.amap_js_code)
            ed["js_code"].setEchoMode(QLineEdit.Password)
            form.addRow(t("settings.web_key"), ed["web_key"])
            form.addRow(t("settings.js_key"), ed["js_key"])
            form.addRow(t("settings.security_code"), ed["js_code"])
            self._amap_ed = ed
        elif name == "tencent":
            ed["key"] = QLineEdit(self.config.tencent_key)
            ed["key"].setEchoMode(QLineEdit.Password)
            ed["secret"] = QLineEdit(self.config.tencent_sk)
            ed["secret"].setEchoMode(QLineEdit.Password)
            form.addRow(t("settings.key"), ed["key"])
            form.addRow(t("settings.secret_key"), ed["secret"])
            hint = QLabel(t("settings.tencent_sig_hint"))
            hint.setWordWrap(True)
            form.addRow(hint)
            self._tencent_ed = ed
        else:
            ed["key"] = QLineEdit(self.config.baidu_ak)
            ed["key"].setEchoMode(QLineEdit.Password)
            ed["sk"] = QLineEdit(self.config.baidu_sk)
            ed["sk"].setEchoMode(QLineEdit.Password)
            form.addRow(t("settings.ak"), ed["key"])
            form.addRow(t("settings.baidu_sk"), ed["sk"])
            sn_hint = QLabel(t("settings.baidu_sn_hint"))
            sn_hint.setWordWrap(True)
            form.addRow(sn_hint)
            hint = QLabel(t("settings.baidu_referer_hint"))
            hint.setWordWrap(True)
            form.addRow(hint)
            self._baidu_ed = ed
        btn = QPushButton(t("settings.test_key"))
        status = QLabel(t("settings.status_none"))
        btn.clicked.connect(lambda: self._test_key(name, ed, status))
        form.addRow(btn, status)
        form.addRow(QLabel(""))
        for text_key, url in LINK_URLS[name]:
            form.addRow(self._link_label(text_key, url))
        note = QLabel(t("settings.quota_note"))
        note.setWordWrap(True)
        form.addRow(note)
        return w

    @staticmethod
    def _spin(value, lo, hi):
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setValue(int(value))
        return s

    def _general_tab(self):
        w = QWidget()
        form = QFormLayout(w)

        self.lang_combo = QComboBox()
        for lang in SUPPORTED:
            from i18n import zh_CN, en_US
            tables = {"zh_CN": zh_CN.STRINGS, "en_US": en_US.STRINGS}
            self.lang_combo.addItem(tables[lang].get("lang." + lang, lang), lang)
        self.lang_combo.setCurrentIndex(
            SUPPORTED.index(current_language())
            if current_language() in SUPPORTED else 0)
        form.addRow(t("settings.lang"), self.lang_combo)

        self.city_combo = QComboBox()
        self.city_combo.addItem(t("city.current"), "current")
        for key, c in CITIES.items():
            self.city_combo.addItem(c.display_name, key)
        idx = self.city_combo.findData(self.config.city)
        if idx >= 0:
            self.city_combo.setCurrentIndex(idx)
        form.addRow(t("settings.sim_city"), self.city_combo)

        self.taxi_spin = self._spin(self.config.taxi_count, 1, 200)
        form.addRow(t("settings.taxi_count"), self.taxi_spin)
        self.pax_spin = self._spin(self.config.passenger_count, 1, 2000)
        form.addRow(t("settings.passenger_count"), self.pax_spin)
        self.spawn_spin = QDoubleSpinBox()
        self.spawn_spin.setRange(0.5, 30)
        self.spawn_spin.setSingleStep(0.5)
        self.spawn_spin.setValue(self.config.spawn_interval)
        form.addRow(t("settings.spawn_interval"), self.spawn_spin)
        self.patience_spin = self._spin(self.config.passenger_patience, 10, 600)
        form.addRow(t("settings.patience"), self.patience_spin)
        self.speed_combo = QComboBox()
        for v in (1, 2, 4, 8, 16):
            self.speed_combo.addItem(f"×{v}", v)
        cur = int(self.config.speed_multiplier)
        if cur in (1, 2, 4, 8, 16):
            self.speed_combo.setCurrentIndex((1, 2, 4, 8, 16).index(cur))
        form.addRow(t("settings.speed"), self.speed_combo)
        return w

    def _build(self):
        tabs = QTabWidget()
        tabs.addTab(self._provider_tab("amap"), t("settings.tab.amap"))
        tabs.addTab(self._provider_tab("tencent"), t("settings.tab.tencent"))
        tabs.addTab(self._provider_tab("baidu"), t("settings.tab.baidu"))
        tabs.addTab(self._general_tab(), t("settings.tab.general"))
        lay = QVBoxLayout(self)
        lay.addWidget(tabs)
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    # ---------------- 动作 ----------------

    def _test_key(self, name, ed, status):
        if name == "amap":
            self.config.cp.set("amap", "web_key", ed["web_key"].text().strip())
        elif name == "tencent":
            self.config.cp.set("tencent", "key", ed["key"].text().strip())
            self.config.cp.set("tencent", "secret_key",
                               ed["secret"].text().strip())
        else:
            self.config.cp.set("baidu", "ak", ed["key"].text().strip())
            self.config.cp.set("baidu", "sk", ed["sk"].text().strip())
        self.manager.reload_config()
        ok, key, detail = self.manager.test_key(name)
        if ok:
            from mapsdk.quota import QuotaLedger
            QuotaLedger().record(name, "geocode")  # 测试消耗记入台账
        text = t(key) if key else detail
        status.setText(("✅ " if ok else "❌ ") + text)
        status.setStyleSheet("color:" + ("green" if ok else "red"))

    def _save(self):
        self.config.cp.set("amap", "web_key", self._amap_ed["web_key"].text().strip())
        self.config.cp.set("amap", "js_key", self._amap_ed["js_key"].text().strip())
        self.config.cp.set("amap", "security_js_code",
                           self._amap_ed["js_code"].text().strip())
        self.config.cp.set("tencent", "key", self._tencent_ed["key"].text().strip())
        self.config.cp.set("tencent", "secret_key",
                           self._tencent_ed["secret"].text().strip())
        self.config.cp.set("baidu", "ak", self._baidu_ed["key"].text().strip())
        self.config.cp.set("baidu", "sk", self._baidu_ed["sk"].text().strip())
        self.config.set_general(
            language=self.lang_combo.currentData(),
            city=self.city_combo.currentData(),
            default_taxi_count=self.taxi_spin.value(),
            default_passenger_count=self.pax_spin.value(),
            spawn_interval=self.spawn_spin.value(),
            passenger_patience=self.patience_spin.value(),
            speed_multiplier=self.speed_combo.currentData(),
        )
        self.config.save()
        self.manager.reload_config()
        self.accept()
