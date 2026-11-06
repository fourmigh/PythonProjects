"""出租车巡游策略: 均返回目标点 (lat,lng), 由引擎负责规划路线。
- random_walk: 随机选一个可达点(点池);
- snake_scan: 全市可达点按蛇形序排列, 依次扫过(每辆车错开起点);
- hotspot_greedy: 驶向当前等待乘客密度最高的区域(直接扑向某等待乘客附近)。
"""
import random

from data import store


class Strategy:
    name = "random"

    def __init__(self, city_name, taxi=None):
        self.city_name = city_name
        self.taxi = taxi
        self._rng = random.Random()
        self._snake_i = None
        self._snake = None

    def choose_target(self, pool, waiting_positions):
        raise NotImplementedError


class RandomWalkStrategy(Strategy):
    name = "random"

    def choose_target(self, pool, waiting_positions):
        return self._rng.choice(pool) if pool else None


class SnakeScanStrategy(Strategy):
    name = "snake"

    def _ensure_snake(self, pool, tid):
        if not self._snake or len(self._snake) != len(pool):
            # 按纬度分行、行内按经度交替方向 → 蛇形扫描序
            pts = sorted(pool, key=lambda p: (round(p[0], 4), p[1]))
            rows = {}
            for p in pts:
                rows.setdefault(round(p[0], 4), []).append(p)
            seq = []
            for i, k in enumerate(sorted(rows)):
                seq.extend(rows[k] if i % 2 == 0 else rows[k][::-1])
            self._snake = seq or pool
            self._snake_i = tid % max(1, len(self._snake))

    def choose_target(self, pool, waiting_positions):
        if not pool:
            return None
        self._ensure_snake(pool, self.taxi.tid if self.taxi else 0)
        self._snake_i = (self._snake_i + 1) % len(self._snake)
        return self._snake[self._snake_i]


class HotspotGreedyStrategy(Strategy):
    name = "hotspot"

    def choose_target(self, pool, waiting_positions):
        if waiting_positions:
            # 直接驶向某个等待乘客的位置附近(点池中找最近的点)
            p = self._rng.choice(list(waiting_positions))
            if pool:
                return min(pool, key=lambda q: (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2)
            return p
        if pool:
            return self._rng.choice(pool)
        return None


STRATEGIES = {s.name: s for s in
              [RandomWalkStrategy, SnakeScanStrategy, HotspotGreedyStrategy]}


def create(name, city_name, taxi=None):
    cls = STRATEGIES.get(name, RandomWalkStrategy)
    return cls(city_name, taxi=taxi)
