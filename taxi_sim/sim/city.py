"""城市定义(中心为 GCJ-02 坐标, span 为仿真范围边长, 约度数)。
城市显示名走 i18n, 代码中只有稳定 key。
支持"当前位置"临时城市: 由定位坐标动态构造。
"""
import math

CURRENT = "current"      # 定位得到、但不在内置列表时使用的临时城市 key
MATCH_MAX_KM = 100.0     # 定位点与内置城市中心的匹配半径


class City:
    def __init__(self, name, lat, lng, span_deg=0.06):
        self.name = name
        self.center = (lat, lng)
        self.span_deg = span_deg

    @property
    def display_name(self):
        from i18n import t
        return t("city." + self.name)

    @property
    def is_temp(self):
        return self.name == CURRENT


CITIES = {
    "beijing":   City("beijing",   39.909, 116.397),
    "shanghai":  City("shanghai",  31.230, 121.473),
    "shenzhen":  City("shenzhen",  22.543, 114.057),
    "guangzhou": City("guangzhou", 23.129, 113.264),
    "chengdu":   City("chengdu",   30.659, 104.065),
    "hangzhou":  City("hangzhou",  30.287, 120.153),
}


def _km(a, b):
    """两点球面距离(km)。"""
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * \
        math.sin(dlng / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def city_from_location(lat, lng, max_km=MATCH_MAX_KM):
    """定位坐标 → (City, 是否命中内置城市)。
    超出匹配半径时返回以定位点为中心的临时城市。
    """
    best, best_km = None, float("inf")
    for city in CITIES.values():
        d = _km((lat, lng), city.center)
        if d < best_km:
            best, best_km = city, d
    if best is not None and best_km <= max_km:
        return best, True
    return City(CURRENT, lat, lng), False


def get_city(name, lat=None, lng=None):
    """按 key 取城市; name 为 CURRENT 时用定位坐标构造临时城市。"""
    if name == CURRENT:
        if lat is not None and lng is not None:
            return City(CURRENT, lat, lng)
        return CITIES["beijing"]
    return CITIES.get(name, CITIES["beijing"])
