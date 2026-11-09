"""离线冒烟测试(不消耗配额, 不启动GUI)。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_config import AppConfig
from data import store, roads
from mapsdk.manager import MapManager
from mapsdk.quota import QuotaLedger
from sim.taxi import Taxi
from sim.strategies import create

cfg = AppConfig()
store.init()
# 清理上次测试残留, 保证可重复执行
import sqlite3
_c = sqlite3.connect(store.DB_PATH)
_c.execute("DELETE FROM learned_quota WHERE provider LIKE 'testprov%'")
_c.execute("DELETE FROM quota_usage WHERE provider LIKE 'testprov%'")
_c.commit()
_c.close()
print('db init ok')

# 配置默认值: 班次/费率/策略方案
assert 0.1 <= cfg.shift_hours <= 24
assert cfg.fare_base > 0 and cfg.fare_base_km > 0 and cfg.fare_per_km > 0
_schemes = cfg.get_strategies()
assert isinstance(_schemes, list) and len(_schemes) >= 8 \
    and all('type' in s and 'params' in s for s in _schemes), _schemes
print('config defaults ok')

# 配额台账 + 自学习(用独立命名空间, 测试可重复)
ledger = QuotaLedger(defaults={('testprov', 'route'): 100})
ledger.record('testprov', 'route', 5)
assert ledger.remaining('testprov', 'route') == 95
ledger.mark_exhausted('testprov', 'route')
assert ledger.is_exhausted('testprov', 'route')
assert ledger.limit('testprov', 'route') == 5, ledger.limit('testprov', 'route')
# 今日无成功调用时触顶: 只置满当日台账, 不污染学习值(明日恢复后配额估计不变)
ledger2 = QuotaLedger(defaults={('testprov0', 'route'): 100})
ledger2.mark_exhausted('testprov0', 'route')
assert ledger2.is_exhausted('testprov0', 'route')
assert ledger2.limit('testprov0', 'route') == 100, ledger2.limit('testprov0', 'route')
print('quota ledger + self-learning ok')

# 出租车沿线推进
t = Taxi(0, (39.900, 116.300), None)
t.set_route([(39.900, 116.300), (39.910, 116.300)])  # ~1.1km
done = False
for _ in range(200):
    if t.advance(3):
        done = True
        break
assert done, 'taxi never arrived'
assert abs(t.position[0] - 39.910) < 1e-6, t.position
assert t.income == 0.0 and t.ride_income == 0.0
print('taxi movement ok')

# 地图气泡模板: 乘客/出租车信息框 + 收益文案
from pathlib import Path
for _f in ('amap', 'tencent', 'baidu'):
    _html = Path(f'mapsdk/html/{_f}.html').read_text(encoding='utf-8')
    assert 'paxContent' in _html and 'taxiContent' in _html, _f
    assert '今日收益' in _html and '"bx"' in _html.replace("'", '"'), _f
print('map bubble templates ok')

# 巡游策略库: 8 种策略基本行为 / 参数钳制 / ctx 传递 / 场站表
from sim.city import get_city
from sim.strategies import create, STRATEGY_DEFS, STATIONS, station_of

assert Taxi.TO_HOME == 'to_home' and Taxi.OFF_DUTY == 'off_duty'
t2 = Taxi(1, (39.9, 116.4), None)
assert t2.home == (39.9, 116.4) and t2.off_at == float('inf')

bj = get_city('beijing')
ctx = {'city': bj, 'history': {(4, 4): 5}}
pool = [(39.9, 116.4), (39.91, 116.41), (39.89, 116.39), (40.05, 116.6)]
for stype in STRATEGY_DEFS:
    strat = create(stype, 'beijing', taxi=t)
    if stype == 'standby':        # 无等待乘客: 原地等(仍可被派单)
        assert strat.choose_target(pool, [], ctx) is None, stype
    else:
        assert strat.choose_target(pool, [], ctx) in pool, stype
    assert strat.choose_target(pool, [(39.9, 116.4)], ctx) is not None, stype
# station: 默认场站=首都机场; radius 放大后应就近接客
st = create('station', 'beijing', params={'radius': 50.0})
assert st.choose_target(pool, [(40.08, 116.60)], ctx) is not None
# 参数钳制与未知类型退化
g = create('grid', 'beijing', params={'grid_n': 99})
assert g.params['grid_n'] == 6, g.params
assert create('unknown', 'beijing').name == 'random'
assert station_of('shanghai')[0].startswith('虹桥'), station_of('shanghai')
assert len(STATIONS) == 6 and all(STATIONS[c] for c in STATIONS)
print('strategy library ok')

# 完单计价: 起步价 + 超程单价
from sim.engine import calc_fare
assert calc_fare(2000, 13, 3, 2.3) == 13.0
assert calc_fare(5000, 13, 3, 2.3) == 17.6
assert calc_fare(0, 13, 3, 2.3) == 13.0
print('fare calc ok')

# 兜底切片(可达性保证)
seg = roads.fallback_route(
    'beijing', (39.900, 116.400), (39.905, 116.405),
    [[(39.900, 116.400), (39.905, 116.402), (39.905, 116.405)]])
assert seg and len(seg) >= 2
print('fallback route ok')

# 管理器无Key时应安全返回 None 且不发起任何网络请求(避免消耗真实配额)
class _NoKeyCfg:
    amap_web_key = ""
    amap_js_key = ""
    amap_js_code = ""
    tencent_key = ""
    tencent_sk = ""
    baidu_ak = ""
    baidu_sk = ""
    any_key = False


mgr = MapManager(_NoKeyCfg())
name, res = mgr.route_driving(39.9, 116.4, 39.91, 116.41)
assert name is None and res is None
print('manager no-key degrade ok')

# Key 无效的平台当日记住并跳过; 设置里改 Key (reload_config) 后恢复
from mapsdk.errors import InvalidKeyError  # noqa: E402


class _FailP:
    name = "testprov2"
    display_name = "FailP"
    api_ready = True
    calls = 0

    def route_driving(self, *a):
        _FailP.calls += 1
        raise InvalidKeyError("bad key")


class _OkP:
    name = "testprov3"
    display_name = "OkP"
    api_ready = True

    def __init__(self):
        self.calls = 0

    def route_driving(self, *a):
        self.calls += 1
        return {"points": [(39.9, 116.4), (39.91, 116.41)],
                "distance": 1000, "duration": 60}


mgr2 = MapManager(_NoKeyCfg())
okp = _OkP()
mgr2.providers = [_FailP(), okp]
assert mgr2.route_driving(1, 2, 3, 4)[0] == "testprov3"
assert mgr2.route_driving(1, 2, 3, 4)[0] == "testprov3" and okp.calls == 2
assert _FailP.calls == 1, "无效平台不应被再次调用"
assert "testprov2" in mgr2._invalid
mgr2.reload_config()
assert "testprov2" not in mgr2._invalid
print('invalid-key memory ok')

# i18n: 中英文取值/枚举/参数格式化/缺失key回退
from i18n import t, set_language
set_language('zh_CN')
assert t('city.beijing') == '北京'
assert t('strategy.random') == '随机游走'
assert t('engine.order_done', tid=7, dist=1234.6) == '出租车#7 完成一单 (1235m)'
set_language('en_US')
assert t('city.beijing') == 'Beijing'
assert t('engine.order_done', tid=7, dist=1234.6) == 'Taxi#7 completed an order (1235m)'
assert t('nonexistent.key') == 'nonexistent.key'
set_language('zh_CN')
print('i18n ok')

# 城市切换: 三个平台模板都应注入所选城市中心坐标, 且无残留占位符
from sim.city import get_city
from ui.map_bridge import build_html, pick_provider


class _FakeCfg:
    amap_js_key = "AMAP_JS_KEY"
    amap_js_code = "AMAP_SEC"
    tencent_key = "TENCENT_KEY"
    baidu_ak = "BAIDU_AK"
    baidu_sk = ""


sh = get_city('shanghai')
assert pick_provider(_FakeCfg()) == 'amap'          # 优先级: 高德 > 腾讯 > 百度
for provider in ("amap", "tencent", "baidu"):
    html = build_html(_FakeCfg(), sh, provider)
    for token in ("__KEY__", "__SEC__", "__LAT__", "__LNG__", "__ZOOM__"):
        assert token not in html, (provider, token)   # 占位符应全部替换
    assert "31.23" in html, provider
    assert "121.473" in html, provider
assert "AMAP_SEC" in build_html(_FakeCfg(), sh, "amap")
# 百度: 地图页面注入唯一 AK
_baidu_html = build_html(_FakeCfg(), sh, "baidu")
assert "BAIDU_AK" in _baidu_html
print('city switch html ok')

# 定位 → 城市匹配: 命中内置城市 / 远离城市回落临时城市
from sim.city import CURRENT, city_from_location
c1, hit1 = city_from_location(39.910, 116.400)
assert hit1 and c1.name == 'beijing', (hit1, c1.name)
c2, hit2 = city_from_location(0.0, 0.0)
assert (not hit2) and c2.name == CURRENT, (hit2, c2.name)
assert get_city(CURRENT, 1.0, 2.0).center == (1.0, 2.0)
print('city match ok')

# 定位降级: 免费源成功 / 全部失败返回 None(不触网, 用假源)
from data import locate as loc


def _fake_free():
    return 39.909, 116.397          # WGS-84


_orig_free, _orig_sdk = loc.FREE_SOURCES, loc.SDK_SOURCES
loc.FREE_SOURCES = (("fake", _fake_free),)
lat, lng, src = loc.locate(_NoKeyCfg())
assert src == "fake" and abs(lat - 39.909) < 0.01 and abs(lng - 116.397) < 0.01
loc.FREE_SOURCES, loc.SDK_SOURCES = (), ()
assert loc.locate(_NoKeyCfg()) is None
loc.FREE_SOURCES, loc.SDK_SOURCES = _orig_free, _orig_sdk
print('locate fallback ok')

# 腾讯签名校验: sig = md5(请求路径?参数按名排序 + SK), 未配置SK则不加sig
import hashlib

from mapsdk.errors import InvalidKeyError
from mapsdk.tencent import TencentProvider

_url = "https://apis.map.qq.com/ws/x"
signed = TencentProvider("KEY", "SK").sign(_url, {"b": 2, "a": 1})
assert signed["sig"] == hashlib.md5(b"/ws/x?a=1&b=2SK").hexdigest(), signed
assert "sig" not in TencentProvider("KEY", "").sign(_url, {"a": 1})
# 111 → 验签失败引导; 而非笼统的 Key 无效
p = TencentProvider("KEY", "SK")
try:
    p._check({"status": 111, "message": "sig error"})
    raise AssertionError("111 should raise")
except InvalidKeyError as e:
    assert "Secret Key" in str(e) and "111" in str(e), e
print('tencent sig ok')

# 百度 SN 校验: 官方文档样例向量(必须双重 urlencode), sn 放最后, 无 SK 不加 sn
from mapsdk.baidu import BaiduProvider

_bs = BaiduProvider("yourak", "yoursk").sign(
    "https://api.map.baidu.com/geocoder/v2/",
    {"address": "百度大厦", "output": "json", "ak": "yourak"})
assert _bs["sn"] == "7de5a22212ffaa9e326444c75a58f9a0", _bs["sn"]
assert list(_bs)[-1] == "sn"
assert "sn" not in BaiduProvider("yourak", "").sign(
    "https://api.map.baidu.com/geocoder/v2/", {"ak": "x"})
try:
    BaiduProvider("yourak", "yoursk")._check({"status": 211,
                                              "message": "SN error"})
    raise AssertionError("211 should raise")
except InvalidKeyError as e:
    assert "SK" in str(e), e
print('baidu sn ok')

# 百度 path 点串为 "lng,lat": 解析后必须是 (lat≈31.2, lng≈121.4) 的 GCJ-02
_bp = BaiduProvider("yourak", "yoursk")
_bp._get = lambda url, params: {"status": 0, "result": {"routes": [{
    "distance": 1000, "duration": 100, "steps": [
        {"path": "121.483382,31.236937;121.483211,31.237230;121.483131,31.237342"}]}]}}
_bres = _bp.route_driving(31.23, 121.47, 31.24, 121.48)
_pt = _bres["points"][0]
assert 30.9 < _pt[0] < 31.6 and 121.0 < _pt[1] < 121.9, _pt
assert len(_bres["points"]) == 3
print('baidu path order ok')

print('ALL SMOKE TESTS PASSED')
