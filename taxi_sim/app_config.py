"""config.ini 读写与默认配置。"""
import configparser
import json
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

# 策略方案默认值: type 对应 sim/strategies.py 注册表; enabled 为本局是否启用
DEFAULT_SCHEMES = [
    {"name": "随机游走", "type": "random",   "params": {},                    "enabled": True},
    {"name": "蛇形扫描", "type": "snake",    "params": {},                    "enabled": True},
    {"name": "热点抢客", "type": "hotspot",  "params": {},                    "enabled": True},
    {"name": "网格轮巡", "type": "grid",     "params": {"grid_n": 4},         "enabled": False},
    {"name": "热区驻点", "type": "standby",  "params": {"radius": 2.0},       "enabled": False},
    {"name": "避堵漫游", "type": "roam",     "params": {"radius": 0.03},      "enabled": False},
    {"name": "历史热点", "type": "history",  "params": {"top_n": 3},          "enabled": False},
    {"name": "场站驻点", "type": "station",  "params": {"radius": 2.0,
                                                        "station_name": "",
                                                        "station_lat": 0.0,
                                                        "station_lng": 0.0}, "enabled": False},
]


class AppConfig:
    def __init__(self):
        self.cp = configparser.ConfigParser()
        self.reload()

    def reload(self):
        self.cp.read(CONFIG_PATH, encoding="utf-8")
        for sec, opt, val in [
            ("amap", "js_key", ""), ("amap", "web_key", ""), ("amap", "security_js_code", ""),
            ("tencent", "key", ""), ("tencent", "secret_key", ""),
            ("baidu", "ak", ""), ("baidu", "sk", ""),
        ]:
            # config.ini 不存在时不分配 section 会导致 set 抛 NoSectionError
            if not self.cp.has_section(sec):
                self.cp.add_section(sec)
            if not self.cp.has_option(sec, opt):
                self.cp.set(sec, opt, val)
        for sec in ("general", "strategies"):
            if not self.cp.has_section(sec):
                self.cp.add_section(sec)

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
    def tencent_sk(self): return self.get("tencent", "secret_key")

    @property
    def baidu_ak(self): return self.get("baidu", "ak")

    @property
    def baidu_sk(self): return self.get("baidu", "sk")

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

    def _loc(self, option):
        try:
            v = self.get("general", option)
            return float(v) if v else None
        except (TypeError, ValueError):
            return None

    @property
    def located_lat(self): return self._loc("located_lat")

    @property
    def located_lng(self): return self._loc("located_lng")

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

    @property
    def shift_hours(self):
        """班次时长(小时); 兼容旧配置的 shift_minutes(分钟)。"""
        v = self.get("general", "shift_hours")
        if not v:
            try:
                return round(int(self.get("general", "shift_minutes") or 60)
                             / 60.0, 2)
            except (TypeError, ValueError):
                return 1.0
        try:
            return float(v)
        except ValueError:
            return 1.0

    @property
    def follow_mode(self): return self._gen("follow_mode", int, 0) == 1

    # ---- fare(完单计价) ----
    def _fare(self, option, fallback):
        try:
            return float(self.cp.get("fare", option, fallback=fallback))
        except (TypeError, ValueError):
            return fallback

    @property
    def fare_base(self): return self._fare("base_fare", 13.0)

    @property
    def fare_base_km(self): return self._fare("base_km", 3.0)

    @property
    def fare_per_km(self): return self._fare("per_km", 2.3)

    # ---- strategies(策略方案, JSON 列表) ----
    def get_strategies(self):
        raw = self.get("strategies", "schemes")
        try:
            data = json.loads(raw) if raw else None
        except ValueError:
            data = None
        return data if isinstance(data, list) and data else [
            dict(s, params=dict(s["params"])) for s in DEFAULT_SCHEMES]

    def set_strategies(self, schemes):
        if not self.cp.has_section("strategies"):
            self.cp.add_section("strategies")
        self.cp.set("strategies", "schemes",
                    json.dumps(schemes, ensure_ascii=False))

    def set_general(self, **kwargs):
        if not self.cp.has_section("general"):
            self.cp.add_section("general")
        for k, v in kwargs.items():
            self.cp.set("general", k, str(v))

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            self.cp.write(f)
