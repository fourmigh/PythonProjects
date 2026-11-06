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
_c.execute("DELETE FROM learned_quota WHERE provider='testprov'")
_c.execute("DELETE FROM quota_usage WHERE provider='testprov'")
_c.commit()
_c.close()
print('db init ok')

# 配额台账 + 自学习(用独立命名空间, 测试可重复)
ledger = QuotaLedger(defaults={('testprov', 'route'): 100})
ledger.record('testprov', 'route', 5)
assert ledger.remaining('testprov', 'route') == 95
ledger.mark_exhausted('testprov', 'route')
assert ledger.is_exhausted('testprov', 'route')
assert ledger.limit('testprov', 'route') == 5, ledger.limit('testprov', 'route')
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
print('taxi movement ok')

# 巡游策略
s = create('snake', 'beijing', taxi=t)
assert s.choose_target([(39.9, 116.4), (39.91, 116.41), (39.89, 116.39)], [])
s2 = create('hotspot', 'beijing', taxi=t)
assert s2.choose_target([(39.9, 116.4)], [(39.9, 116.4)])
print('strategies ok')

# 兜底切片(可达性保证)
seg = roads.fallback_route(
    'beijing', (39.900, 116.400), (39.905, 116.405),
    [[(39.900, 116.400), (39.905, 116.402), (39.905, 116.405)]])
assert seg and len(seg) >= 2
print('fallback route ok')

# 管理器无Key时应安全返回 None 不抛异常
mgr = MapManager(cfg)
name, res = mgr.route_driving(39.9, 116.4, 39.91, 116.41)
assert res is None
print('manager no-key degrade ok')

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

print('ALL SMOKE TESTS PASSED')
