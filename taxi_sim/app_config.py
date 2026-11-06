"""config.ini 读写与默认配置。"""
import configparser
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.ini")
DB_PATH = os.path.join(ROOT, "taxi_sim.db")

# 内置保守默认配额(仅首次使用, SDK超限报错后会自动学习校准真实值)
DEFAULT_QUOTAS = {
    ("amap", "route"): 3000,
    ("tencent", "route"): 6000,
    ("baidu", "route"): 5000,
    ("amap", "geocode"): 3000,
    ("tencent", "geocode"): 6000,
    ("baidu", "geocode"): 5000,
}
# 各平台最小调用间隔(秒), 防止触发QPS限制
MIN_INTERVALS = {"amap": 0.35, "tencent": 0.15, "baidu": 0.35}


class AppConfig:
    def __init__(self):
        self.cp = configparser.ConfigParser()
        self.reload()

    def reload(self):
        self.cp.read(CONFIG_PATH, encoding="utf-8")
        for sec, opt, val in [
            ("amap", "js_key", ""), ("amap", "web_key", ""), ("amap", "security_js_code", ""),
            ("tencent", "key", ""), ("baidu", "ak", ""),
        ]:
            if not self.cp.has_option(sec, opt):
                self.cp.set(sec, opt, val)

    # ---- keys ----
    def get(self, section, option, fallback=""):
        return self.cp.get(section, option, fallback=fallback).strip()

    @property
    def amap_web_key(self): return self.get("amap", "web_key")

    @property
    def amap_js_key(self): return self.get("amap", "js_key")

    @property
    def amap_js_code(self): return self.get("amap", "security_js_code")

    @property
    def tencent_key(self): return self.get("tencent", "key")

    @property
    def baidu_ak(self): return self.get("baidu", "ak")

    @property
    def any_key(self):
        return bool(self.amap_web_key or self.tencent_key or self.baidu_ak)

    # ---- general ----
    def _gen(self, option, cast, fallback):
        try:
            return cast(self.get("general", option) or fallback)
        except (TypeError, ValueError):
            return fallback

    @property
    def city(self): return self.get("general", "city", "beijing")

    @property
    def language(self): return self.get("general", "language", "zh_CN")

    @property
    def taxi_count(self): return self._gen("default_taxi_count", int, 20)

    @property
    def passenger_count(self): return self._gen("default_passenger_count", int, 50)

    @property
    def spawn_interval(self): return self._gen("spawn_interval", float, 3)

    @property
    def passenger_patience(self): return self._gen("passenger_patience", float, 120)

    @property
    def speed_multiplier(self): return self._gen("speed_multiplier", float, 4)

    def set_general(self, **kwargs):
        for k, v in kwargs.items():
            self.cp.set("general", k, str(v))

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            self.cp.write(f)
