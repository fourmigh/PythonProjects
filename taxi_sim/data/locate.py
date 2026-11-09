"""定位: 获取当前所在坐标(统一输出 GCJ-02)。
策略:
1. 免费 IP 定位服务(零配额, 不依赖 Key);
2. 已配置平台的 IP 定位接口(消耗少量配额, 记入台账);
3. 全部失败返回 None(调用方回落到默认城市)。
均为阻塞网络调用, 请放到后台线程执行。
"""
import logging

import requests

from mapsdk import coords
from mapsdk.quota import QuotaLedger

log = logging.getLogger(__name__)
TIMEOUT = 4


def _get_json(url, params=None):
    r = requests.get(url, params=params, timeout=TIMEOUT,
                     headers={"User-Agent": "taxi-sim/1.0"})
    r.raise_for_status()
    return r.json()


# ---------------- 免费源(WGS-84) ----------------

def _ipapi_co():
    d = _get_json("https://ipapi.co/json/")
    return float(d["latitude"]), float(d["longitude"])


def _ipwho_is():
    d = _get_json("https://ipwho.is/")
    if d.get("success") is False:
        raise ValueError("ipwho.is failed")
    return float(d["latitude"]), float(d["longitude"])


def _ip_api_com():
    d = _get_json("http://ip-api.com/json/?lang=zh-CN")
    if d.get("status") != "success":
        raise ValueError("ip-api.com failed")
    return float(d["lat"]), float(d["lon"])


FREE_SOURCES = (
    ("ipapi.co", _ipapi_co),
    ("ipwho.is", _ipwho_is),
    ("ip-api.com", _ip_api_com),
)


# ---------------- SDK 兜底(消耗配额, 记台账) ----------------

def _amap_ip(config):
    if not config.amap_web_key:
        return None
    d = _get_json("https://restapi.amap.com/v3/ip",
                  {"key": config.amap_web_key})
    QuotaLedger().record("amap", "ip")
    rect = d.get("rectangle")
    if isinstance(rect, str) and ";" in rect:
        a, b = rect.split(";")
        lng1, lat1 = (float(x) for x in a.split(","))
        lng2, lat2 = (float(x) for x in b.split(","))
        return (lat1 + lat2) / 2, (lng1 + lng2) / 2   # GCJ-02
    return None


def _tencent_ip(config):
    if not config.tencent_key:
        return None
    # 走 Provider 请求, 以便开启签名校验时自动附加 sig
    from mapsdk.tencent import TencentProvider
    provider = TencentProvider(config.tencent_key, config.tencent_sk)
    d = provider._get("https://apis.map.qq.com/ws/location/v1/ip",
                      {"key": config.tencent_key})
    provider._check(d)
    QuotaLedger().record("tencent", "ip")
    loc = d["result"]["location"]
    return float(loc["lat"]), float(loc["lng"])      # GCJ-02


def _baidu_ip(config):
    if not config.baidu_ak:
        return None
    # 走 Provider 请求, 以便 AK 选择 SN 校验时自动附加 sn
    from mapsdk.baidu import BaiduProvider
    provider = BaiduProvider(config.baidu_ak, config.baidu_sk)
    d = provider._get("https://api.map.baidu.com/location/ip",
                      {"ak": config.baidu_ak, "coor": "bd09ll"})
    provider._check(d)
    QuotaLedger().record("baidu", "ip")
    p = d["content"]["point"]
    lng, lat = coords.bd09_to_gcj02(float(p["x"]), float(p["y"]))
    return lat, lng                                  # 转 GCJ-02


SDK_SOURCES = (
    ("amap", _amap_ip),
    ("tencent", _tencent_ip),
    ("baidu", _baidu_ip),
)


def locate(config):
    """返回 (lat, lng, source) 或 None。坐标统一为 GCJ-02。"""
    for name, fn in FREE_SOURCES:
        try:
            lat, lng = fn()                          # WGS-84
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                continue
            g_lng, g_lat = coords.wgs84_to_gcj02(lng, lat)
            return g_lat, g_lng, name
        except Exception as e:
            log.debug("免费定位源 %s 失败: %s", name, e)

    for name, fn in SDK_SOURCES:
        try:
            res = fn(config)
            if res:
                return res[0], res[1], name
        except Exception as e:
            log.debug("SDK定位源 %s 失败: %s", name, e)
    return None
