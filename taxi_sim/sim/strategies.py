"""巡游策略库: 注册表 + 参数 schema, 均返回目标点 (lat,lng), 由引擎规划路线。

- choose_target(pool, waiting_positions, ctx): ctx 由引擎传入:
    ctx["city"]    → City 对象(中心/范围, 供网格/象限划分)
    ctx["history"] → {(gi,gj): 完单起点计数} 本局热力网格(历史热点用)
  ctx 可为 None(离线测试/降级)。
- 策略实例参数来自 config.ini [strategies] 的方案 JSON, PARAMS 定义合法范围。
- 场站驻点内置各城市机场/火车站坐标(GCJ-02 近似值), 可在方案参数里手改。
"""
import random

# ---------------- 内置场站坐标表(GCJ-02 近似值, 单位度) ----------------
# (名称, 纬度, 经度); 首个为默认场站。"当前位置"临时城市无内置场站, 需手填。
STATIONS = {
    "beijing": [
        ("首都国际机场T3", 40.0799, 116.6031),
        ("大兴国际机场", 39.5094, 116.4105),
        ("北京南站", 39.8652, 116.3787),
        ("北京西站", 39.8952, 116.3217),
    ],
    "shanghai": [
        ("虹桥枢纽(机场+高铁)", 31.1946, 121.3363),
        ("浦东国际机场", 31.1507, 121.8052),
        ("上海站", 31.2494, 121.4559),
    ],
    "shenzhen": [
        ("宝安国际机场", 22.6393, 113.8107),
        ("深圳北站", 22.6104, 114.0297),
        ("罗湖火车站", 22.5285, 114.1174),
    ],
    "guangzhou": [
        ("白云国际机场", 23.3924, 113.2988),
        ("广州南站", 22.9892, 113.2700),
        ("广州东站", 23.1497, 113.3249),
    ],
    "chengdu": [
        ("双流国际机场", 30.5728, 103.9471),
        ("天府国际机场", 30.3130, 104.4417),
        ("成都东站", 30.6306, 104.1390),
    ],
    "hangzhou": [
        ("萧山国际机场", 30.2295, 120.4345),
        ("杭州东站", 30.2905, 120.2122),
    ],
}

GRID_MAX = 8              # 历史热力网格单边格数
EPS = 1e-9


def station_of(city_name):
    """城市 → (名称, lat, lng) 默认场站; 无内置则返回 None。"""
    st = STATIONS.get(city_name)
    return st[0] if st else None


def resolve_station(city_name, params):
    """方案参数里的场站 → (名称, lat, lng)。优先手填坐标, 其次内置表。"""
    try:
        lat = float(params.get("station_lat") or 0)
        lng = float(params.get("station_lng") or 0)
        if abs(lat) > EPS and abs(lng) > EPS:
            return (params.get("station_name") or "自定义场站", lat, lng)
    except (TypeError, ValueError):
        pass
    return station_of(city_name)


class Strategy:
    """基类: name=类型key, PARAMS={key:(default,min,max)} 数值参数。"""
    name = "random"
    PARAMS = {}

    def __init__(self, city_name, params=None, taxi=None):
        self.city_name = city_name
        self.params = {k: v[0] for k, v in self.PARAMS.items()}
        for k, v in (params or {}).items():
            if k in self.PARAMS:
                try:
                    lo, hi = self.PARAMS[k][1], self.PARAMS[k][2]
                    self.params[k] = max(lo, min(hi, float(v)))
                except (TypeError, ValueError):
                    pass
        self.taxi = taxi
        self._rng = random.Random()
        self._snake = None
        self._snake_i = None

    # ---- 工具 ----
    def _nearest(self, pts, p):
        return min(pts, key=lambda q: (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2)

    def _cell(self, ctx, p):
        """ctx 城市范围 → 热力网格坐标 (gi,gj); 出界返回 None。"""
        city = ctx and ctx.get("city")
        if not city:
            return None
        gi = int((p[0] - (city.center[0] - city.span_deg / 2))
                 / city.span_deg * GRID_MAX)
        gj = int((p[1] - (city.center[1] - city.span_deg / 2))
                 / city.span_deg * GRID_MAX)
        if 0 <= gi < GRID_MAX and 0 <= gj < GRID_MAX:
            return (gi, gj)
        return None

    def choose_target(self, pool, waiting_positions, ctx=None):
        raise NotImplementedError


class RandomWalkStrategy(Strategy):
    name = "random"

    def choose_target(self, pool, waiting_positions, ctx=None):
        return self._rng.choice(pool) if pool else None


class SnakeScanStrategy(Strategy):
    name = "snake"

    def _ensure_snake(self, pool, tid):
        if not self._snake or len(self._snake) != len(pool):
            pts = sorted(pool, key=lambda p: (round(p[0], 4), p[1]))
            rows = {}
            for p in pts:
                rows.setdefault(round(p[0], 4), []).append(p)
            seq = []
            for i, k in enumerate(sorted(rows)):
                seq.extend(rows[k] if i % 2 == 0 else rows[k][::-1])
            self._snake = seq or pool
            self._snake_i = tid % max(1, len(self._snake))

    def choose_target(self, pool, waiting_positions, ctx=None):
        if not pool:
            return None
        self._ensure_snake(pool, self.taxi.tid if self.taxi else 0)
        self._snake_i = (self._snake_i + 1) % len(self._snake)
        return self._snake[self._snake_i]


class HotspotGreedyStrategy(Strategy):
    name = "hotspot"

    def choose_target(self, pool, waiting_positions, ctx=None):
        if waiting_positions:
            p = self._rng.choice(list(waiting_positions))
            return self._nearest(pool, p) if pool else p
        return self._rng.choice(pool) if pool else None


class GridPatrolStrategy(Strategy):
    """网格轮巡: 每车固定负责一个格子, 在格内点池点间按序轮转。"""
    name = "grid"
    PARAMS = {"grid_n": (4, 2, 6)}

    def choose_target(self, pool, waiting_positions, ctx=None):
        if not pool:
            return None
        city = ctx and ctx.get("city")
        n = int(self.params["grid_n"])
        tid = self.taxi.tid if self.taxi else 0
        if not city:                      # 无 ctx: 退化为按 tid 均分点池轮转
            mine = sorted(pool)[tid::n] or pool
            return mine[(tid // n) % len(mine)]
        # 自己负责的格子(按 tid 顺序分配)
        cells = [(i, j) for i in range(n) for j in range(n)]
        ci, cj = cells[tid % (n * n)]
        half = city.span_deg / 2
        lat0 = city.center[0] - half + ci * city.span_deg / n
        lng0 = city.center[1] - half + cj * city.span_deg / n
        mine = [p for p in pool
                if lat0 <= p[0] < lat0 + city.span_deg / n
                and lng0 <= p[1] < lng0 + city.span_deg / n]
        if not mine:                      # 自己格子没点, 退回全池
            mine = pool
        self._grid_pts = sorted(mine, key=lambda p: (p[0], p[1]))
        idx = getattr(self, "_grid_i", tid)
        self._grid_i = (idx + 1) % len(self._grid_pts)
        return self._grid_pts[self._grid_i]


class HotzoneStandbyStrategy(Strategy):
    """热区驻点: 蹲在等待乘客密集处附近, 原地等客(仍参与派单)。"""
    name = "standby"
    PARAMS = {"radius": (2.0, 0.5, 10.0)}     # km

    def choose_target(self, pool, waiting_positions, ctx=None):
        if not pool:
            return None
        if waiting_positions:
            wl = list(waiting_positions)
            rad2 = (self.params["radius"] / 111.32) ** 2
            best, votes = wl[0], -1
            for p in wl:
                v = sum(1 for q in wl
                        if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < rad2)
                if v > votes:
                    best, votes = p, v
            return self._nearest(pool, best)
        # 没有等待乘客: 原地等(返回 None, 引擎不派新目标), 仍可被派单
        return None


class AntiCrowdRoamStrategy(Strategy):
    """避堵漫游: 朝等待乘客稀疏的象限游走, 避免与同策略车辆扎堆。"""
    name = "roam"
    PARAMS = {"radius": (0.03, 0.005, 0.1)}   # 探索半径(度)

    def choose_target(self, pool, waiting_positions, ctx=None):
        if not pool:
            return None
        city = ctx and ctx.get("city")
        if city:
            clat, clng = city.center
            quads = [0, 0, 0, 0]
            for p in waiting_positions:
                di = 0 if p[0] >= clat else 1
                dj = 0 if p[1] >= clng else 1
                quads[di * 2 + dj] += 1
            qi = quads.index(min(quads))
            slat = 1 if qi < 2 else -1
            slng = 1 if qi % 2 == 0 else -1
            r = self.params["radius"]
            near = [p for p in pool
                    if slat * (p[0] - clat) > 0 and slng * (p[1] - clng) > 0
                    and abs(p[0] - clat) < r * 2 and abs(p[1] - clng) < r * 2]
            if near:
                return self._rng.choice(near)
        return self._rng.choice(pool)


class HistoryHotspotStrategy(Strategy):
    """历史热点: 根据本局完单上车点热力网格, 驶向最热格子内的点池点。"""
    name = "history"
    PARAMS = {"top_n": (3, 1, 10)}

    def choose_target(self, pool, waiting_positions, ctx=None):
        if not pool:
            return None
        hist = (ctx or {}).get("history") or {}
        if not hist:
            return self._rng.choice(pool)
        top = sorted(hist.items(),
                     key=lambda kv: -kv[1])[:int(self.params["top_n"])]
        cells = {c for c, _ in top}
        in_hot = [p for p in pool if self._cell(ctx, p) in cells]
        return self._rng.choice(in_hot) if in_hot else self._rng.choice(pool)


class StationStandbyStrategy(Strategy):
    """场站驻点: 空驶→驶向机场/火车站等待区排队(仍参与派单, 等于顺路接单);
    完单后引擎回到 CRUISING, 本策略再次驶向场站排队。"""
    name = "station"
    PARAMS = {"radius": (2.0, 0.5, 10.0)}     # 排队等待区半径(km)

    def _station(self, ctx):
        city = ctx and ctx.get("city")
        return resolve_station(self.city_name, self.params) \
            or (station_of(city.name) if city else None)

    def choose_target(self, pool, waiting_positions, ctx=None):
        if not pool:
            return None
        st = self._station(ctx)
        if not st:                        # 无场站(临时城市未手填): 退化为热点
            if waiting_positions:
                return self._nearest(pool, self._rng.choice(list(waiting_positions)))
            return self._rng.choice(pool)
        _, slat, slng = st
        rad_deg = self.params["radius"] / 111.32
        # 场站半径内有等待乘客 → 直接就近接客(场站自然客流)
        near_wait = [p for p in waiting_positions
                     if (p[0] - slat) ** 2 + (p[1] - slng) ** 2 < rad_deg ** 2]
        if near_wait:
            return self._nearest(pool, self._rng.choice(near_wait))
        # 否则去场站等待区最近的点池点排队
        return self._nearest(pool, (slat, slng))


# ---------------- 注册表 ----------------
STRATEGY_DEFS = {s.name: s for s in
                 [RandomWalkStrategy, SnakeScanStrategy, HotspotGreedyStrategy,
                  GridPatrolStrategy, HotzoneStandbyStrategy,
                  AntiCrowdRoamStrategy, HistoryHotspotStrategy,
                  StationStandbyStrategy]}


def create(stype, city_name, params=None, taxi=None):
    """按类型+参数创建策略实例; 未知类型退化为随机游走。"""
    cls = STRATEGY_DEFS.get(stype, RandomWalkStrategy)
    return cls(city_name, params=params, taxi=taxi)
