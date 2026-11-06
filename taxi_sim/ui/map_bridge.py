"""地图桥接层: 按可用 JS Key 加载对应平台模板, 周期推送仿真状态。
Key 无需用户选择平台, 自动按 高德>腾讯>百度 优先取已配置的。
"""
import json
import os

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

from i18n import t

HTML_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "mapsdk", "html")

TEMPLATES = {
    "amap":    ("amap.html",    lambda c: c.amap_js_key),
    "tencent": ("tencent.html", lambda c: c.tencent_key),
    "baidu":   ("baidu.html",   lambda c: c.baidu_ak),
}


class MapBridge(QWebEngineView):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_provider = None

    def load_city(self, city):
        """按优先级选择有 JS Key 的平台并加载城市地图。"""
        for name, (fname, key_getter) in TEMPLATES.items():
            key = key_getter(self.config)
            if not key:
                continue
            with open(os.path.join(HTML_DIR, fname), encoding="utf-8") as f:
                html = f.read()
            lat, lng = city.center
            html = (html
                    .replace("__KEY__", key)
                    .replace("__LAT__", str(lat))
                    .replace("__LNG__", str(lng))
                    .replace("__ZOOM__", "14"))
            self.setHtml(html, QUrl("https://localhost/"))
            self.current_provider = name
            return name
        self.setHtml(t("map.no_key_html"))
        self.current_provider = None
        return None

    def reload_city(self, city):
        return self.load_city(city)

    def push_state(self, state):
        if not self.current_provider:
            return
        self.page().runJavaScript(
            f"updateState({json.dumps(state, ensure_ascii=False)})", 0)
