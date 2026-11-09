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
    # 百度: 单 AK(控制台勾选多个服务即可同时用于地图与Web服务)
    "baidu":   ("baidu.html",   lambda c: c.baidu_ak),
}


def pick_provider(config):
    """按 高德>腾讯>百度 优先级返回第一个已配置 JS Key 的平台名。"""
    for name, (_fname, key_getter) in TEMPLATES.items():
        if key_getter(config):
            return name
    return None


def build_html(config, city, provider):
    """生成指定平台的城市地图页面(纯字符串, 便于单测)。"""
    fname, key_getter = TEMPLATES[provider]
    with open(os.path.join(HTML_DIR, fname), encoding="utf-8") as f:
        html = f.read()
    lat, lng = city.center
    return (html
            .replace("__KEY__", key_getter(config))
            .replace("__SEC__", config.amap_js_code)
            .replace("__LAT__", f"{lat:g}")
            .replace("__LNG__", f"{lng:g}")
            .replace("__ZOOM__", "14"))


class MapBridge(QWebEngineView):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_provider = None
        self.current_city = None

    def load_city(self, city):
        """重新生成 HTML 并加载指定城市地图(切城市/改Key均可安全重复调用)。"""
        provider = pick_provider(self.config)
        if not provider:
            self.setHtml(t("map.no_key_html"))
            self.current_provider = None
            self.current_city = None
            return None
        html = build_html(self.config, city, provider)
        # 递增的虚拟URL, 避免 QWebEngine 将相同URL的setHtml视为同一历史项而不刷新
        self.setHtml(html, QUrl(f"https://taxi-sim.local/{provider}/{city.name}"))
        self.current_provider = provider
        self.current_city = city.name
        return provider

    def reload_city(self, city):
        return self.load_city(city)

    def push_state(self, state):
        if not self.current_provider:
            return
        self.page().runJavaScript(
            f"updateState({json.dumps(state, ensure_ascii=False)})", 0)
        if self.config.follow_mode:
            taxis = state.get("taxis") or []
            if taxis:
                # 优先跟随活跃车(非下班); 全部下班则跟第一辆
                taxi = next((x for x in taxis if x["state"] != "off_duty"),
                            taxis[0])
                self.page().runJavaScript(
                    f"setCenter({taxi['lat']:.6f},{taxi['lng']:.6f})", 0)
