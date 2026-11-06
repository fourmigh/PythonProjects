"""城市定义(中心为 GCJ-02 坐标, span 为仿真范围边长, 约度数)。
城市显示名走 i18n, 代码中只有稳定 key。
"""


class City:
    def __init__(self, name, lat, lng, span_deg=0.06):
        self.name = name
        self.center = (lat, lng)
        self.span_deg = span_deg

    @property
    def display_name(self):
        from i18n import t
        return t("city." + self.name)


CITIES = {
    "beijing":   City("beijing",   39.909, 116.397),
    "shanghai":  City("shanghai",  31.230, 121.473),
    "shenzhen":  City("shenzhen",  22.543, 114.057),
    "guangzhou": City("guangzhou", 23.129, 113.264),
    "chengdu":   City("chengdu",   30.659, 104.065),
    "hangzhou":  City("hangzhou",  30.287, 120.153),
}


def get_city(name):
    return CITIES.get(name, CITIES["beijing"])
