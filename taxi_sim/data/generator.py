"""数据生成器:
- 本地优先: 数量不超过库内已有 → 直接随机抽样, 零配额;
- 差额补齐: 不足部分从"可达点池"采样; 点池不够则做种子采集(调SDK路径规划,
  成功折线全部入库+入池), 额度不足时种子任务挂起, 次日额度恢复自动补;
- 生成测试数据不要求实时, 仿真可用现有数据先跑起来。
"""
import logging
import random

from i18n import t
from data import roads, store
from sim.city import City, get_city


def _as_city(city):
    """兼容传入 City 对象或城市 key(含"当前位置"临时城市)。"""
    return city if isinstance(city, City) else get_city(city)

log = logging.getLogger(__name__)


class DataGenerator:
    def __init__(self, manager):
        self.manager = manager
        self._polylines = None

    def _load_polylines(self, city):
        if self._polylines is None:
            self._polylines = store.all_route_points(city)
        return self._polylines

    # ---------------- 路线获取(带缓存/兜底) ----------------

    def get_route(self, city, o, d):
        """返回 dict(points, distance, duration, provider) 或 None。"""
        key = store.route_key(city, o[0], o[1], d[0], d[1])
        cached = store.get_route_cached(key)
        if cached:
            return {**cached, "provider": "cache"}
        # o/d 均为 (lat,lng), route_driving 形参顺序即 (o_lat, o_lng, ...)
        provider, res = self.manager.route_driving(o[0], o[1], d[0], d[1])
        if res:
            store.put_route(key, city, o, d, provider, res["points"],
                            res["distance"], res["duration"])
            self._polylines = None
            return {**res, "provider": provider}
        seg = roads.fallback_route(city, o, d, self._load_polylines(city))
        if seg:
            return {"points": seg, "distance": roads.deg_to_m(seg[0], seg[-1]),
                    "duration": 0, "provider": "fallback"}
        return None

    # ---------------- 种子采集(冷启动) ----------------

    def seed_collect(self, city, target_pool=500, max_calls=30, log_cb=None):
        """调SDK规划随机点对, 成功的折线全部入库+入池。返回本次实际调用次数。"""
        city = _as_city(city)
        calls = 0
        fails = 0
        while store.pool_size(city.name) < target_pool and calls < max_calls:
            if calls and fails >= 5:
                break  # 连续无可用平台/规划失败, 挂起(次日额度恢复后重试)
            o = roads.random_point_near(city.center, city.span_deg)
            d = roads.random_point_near(city.center, city.span_deg)
            if roads.hav_deg(o, d) < 0.004:
                continue
            calls += 1
            provider, res = self.manager.route_driving(o[0], o[1], d[0], d[1])
            if res:
                key = store.route_key(city.name, o[0], o[1], d[0], d[1])
                store.put_route(key, city.name, o, d, provider,
                                res["points"], res["distance"], res["duration"])
                self._polylines = None
                fails = 0
                if log_cb:
                    log_cb(t("gen.seed_progress",
                             routes=store.cache_size(city.name),
                             pool=store.pool_size(city.name),
                             provider=provider))
            else:
                fails += 1
        return calls

    # ---------------- 实体生成(本地优先 → 点池 → 种子) ----------------

    def ensure_entities(self, city, n_pax, n_taxis, log_cb=None):
        city = _as_city(city)
        name = city.name
        rng = random.Random()
        deficit_p = max(0, n_pax - store.count_passengers(name))
        deficit_t = max(0, n_taxis - store.count_taxis(name))
        summary = {"added_pax": 0, "added_taxis": 0, "from_db": 0}

        # 已有数量大于请求数: 直接随机抽样即可(调用方 sample), 无需补
        if deficit_p == 0 and deficit_t == 0:
            summary["from_db"] = min(n_pax, store.count_passengers(name))
            return summary

        # 点池不足时先做少量种子采集(消耗配额, 不够则挂起)
        need = (deficit_p * 2 + deficit_t + 10) - store.pool_size(name)
        if need > 0:
            calls = self.seed_collect(
                city, target_pool=store.pool_size(name) + need * 3,
                max_calls=min(60, need * 2), log_cb=log_cb)
            if log_cb:
                log_cb(t("gen.seed_done", calls=calls))

        pool = store.sample_pool(name, max(20, (deficit_p * 2 + deficit_t) * 2))
        if not pool:
            if log_cb:
                log_cb(t("gen.pool_empty"))
            return summary

        # 乘客: 起终点均从点池采样(天然可达)
        used = []
        pax_rows = []
        for _ in range(deficit_p * 4):
            if len(pax_rows) >= deficit_p:
                break
            pair = roads.pick_pair(pool, rng=rng)
            if not pair:
                continue
            o, d = pair
            if any(roads.hav_deg(o, u) < 0.002 for u in used):
                continue
            used.extend([o, d])
            pax_rows.append((o[0], o[1], d[0], d[1], "pool"))
        if pax_rows:
            store.add_passengers(name, pax_rows)
            summary["added_pax"] = len(pax_rows)

        # 出租车: 从点池采样初始位置
        taxi_rows = []
        for p in store.sample_pool(name, deficit_t + len(used),
                                   exclude=used):
            taxi_rows.append((p[0], p[1], "pool"))
        taxi_rows = taxi_rows[:deficit_t]
        if taxi_rows:
            store.add_taxis(name, taxi_rows)
            summary["added_taxis"] = len(taxi_rows)

        if log_cb:
            log_cb(t("gen.entities_added", pax=summary["added_pax"],
                     taxis=summary["added_taxis"]))
        return summary
