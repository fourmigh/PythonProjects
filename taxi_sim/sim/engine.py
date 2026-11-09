"""仿真引擎: QTimer 驱动的仿真时钟, 串联 乘客/出租车/巡游策略/派单/路线获取。"""
import logging
import threading

from PySide6.QtCore import QObject, QTimer, Signal

from i18n import t as translate   # 别名: 避免与出租车变量 t 遮蔽冲突
from data import generator, store
from data import roads
from sim import dispatcher
from sim.city import get_city
from sim.passenger import Passenger
from sim.strategies import create as create_strategy, GRID_MAX
from sim.taxi import Taxi

log = logging.getLogger(__name__)

TICK_MS = 200          # 真实时钟帧间隔
MAX_ACTIVE_WAITING_FACTOR = 1.5   # 同时等待的乘客数上限(×出租车数)
PREVIEW_WINDOW = 300.0  # 乘客预告时间窗(仿真秒)
PREVIEW_MAX = 80        # 同屏预告图标上限


def calc_fare(dist_m, base_fare, base_km, per_km):
    """简单计价: 起步价覆盖 base_km, 超出部分按 per_km/km 计费(元)。"""
    return round(base_fare + max(0.0, dist_m / 1000.0 - base_km) * per_km, 1)


class SimulationEngine(QObject):
    statsUpdated = Signal(dict)
    logMessage = Signal(str)

    def __init__(self, manager, config):
        super().__init__()
        self.manager = manager
        self.config = config
        self.gen = generator.DataGenerator(manager)
        self.city = get_city(config.city)
        self.timer = QTimer(self)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self._tick)

        self.taxis = []
        self.passengers = []
        self._scheduled = []       # [(spawn_at,uid,lat,lng,dlat,dlng)] 计划投放, 升序
        self._pax_raw = []         # 数据库原始乘客条目(后台线程只增, 主线程排程)
        self._sched_cursor = 0.0   # 排程时间游标(仿真秒)
        self._q_uid = 0
        self._next_pid = 1
        self._pool = []
        self._sim_time = 0.0
        self._frame = 0
        self._pool_refresh_at = 0
        self._strat_stats = {}     # {type: {...}} 按策略归集统计
        self._history = {}         # {(gi,gj): 上车点计数} 历史热力网格
        self._seed_thread = None

    # ---------------- 生命周期 ----------------

    def start(self, n_taxis, schemes, city=None):
        """schemes: 启用的策略方案列表 [{name, type, params}] (均分车队)。"""
        if not self.config.any_key:
            self.logMessage.emit(translate("msg.config_incomplete"))
            return
        self.city = city or get_city(self.config.city)
        self._sim_time = 0.0
        self._frame = 0
        self._sched_cursor = 0.0
        self._q_uid = 0
        self._next_pid = 1
        self._strat_stats = {}
        self._history = {}
        self._scheduled = []
        self.passengers.clear()

        # 立即用数据库已有数据生成出租车
        self._create_taxis(n_taxis, schemes)

        # 差额补齐在后台线程进行(调SDK消耗配额, 不阻塞界面)
        self._seed_thread = threading.Thread(
            target=self._ensure_entities_bg,
            args=(self.config.passenger_count, n_taxis), daemon=True)
        self._seed_thread.start()

        self._refresh_pool()
        self._refill_queue()
        self.timer.start()
        self.logMessage.emit(translate("engine.start", city=self.city.display_name,
                                       n=len(self.taxis),
                                       strats=[s["name"] for s in schemes],
                                       pax=self.config.passenger_count))

    def stop(self):
        self.timer.stop()

    def _create_taxis(self, n_taxis, schemes):
        self.taxis.clear()
        rows = store.sample_taxis(self.city.name, n_taxis)
        while len(rows) < n_taxis:      # 库不足时用点池临时顶上
            p = store.random_pool_point(self.city.name)
            if not p:
                break
            rows.append((None, p[0], p[1]))
        for i, (_id, lat, lng) in enumerate(rows):
            scheme = schemes[i % len(schemes)]     # 均分车队
            t = Taxi(i, (lat, lng), None)
            t.strategy = create_strategy(scheme["type"], self.city.name,
                                         params=scheme.get("params"), taxi=t)
            t.home = (lat, lng)
            t.off_at = max(60.0, self.config.shift_hours * 3600.0)
            self.taxis.append(t)
        if not rows:
            self.logMessage.emit(translate("engine.no_taxi_warn"))

    def _ensure_entities_bg(self, n_pax, n_taxis):
        def log_cb(msg):
            self.logMessage.emit(msg)
        try:
            self.gen.ensure_entities(self.city, n_pax, n_taxis, log_cb)
            self._refill_queue()
            self.logMessage.emit(translate("engine.bg_done"))
        except Exception as e:  # 后台线程异常不能静默
            log.exception("后台实体生成失败")
            self.logMessage.emit(translate("engine.bg_fail", err=e))

    # ---------------- 数据补充 ----------------

    def _refresh_pool(self):
        self._pool = store.sample_pool(self.city.name, 200)
        self._pool_refresh_at = self._sim_time

    def _refill_queue(self):
        """仅补充原始条目(后台线程可安全调用, 只增不改)。"""
        rows = store.sample_passengers(self.city.name, 200)
        for r in rows:
            self._pax_raw.append((r[1], r[2], r[3], r[4]))  # lat,lng,dlat,dlng

    # ---------------- 主循环 ----------------

    def _tick(self):
        dt = TICK_MS / 1000 * self.config.speed_multiplier
        self._sim_time += dt
        self._frame += 1
        now = self._sim_time

        if now >= self._pool_refresh_at + 60:
            self._refresh_pool()

        # 1. 乘客耐心超时 → 消失
        patience = self.config.passenger_patience
        expired = [p for p in self.passengers if p.is_expired(now, patience)]
        for p in expired:
            if p.assigned_taxi:
                t = p.assigned_taxi
                t.passenger = None
                t.state = Taxi.CRUISING
                t.clear_route()
            self.passengers.remove(p)
        if expired:
            self.logMessage.emit(translate("engine.passengers_expired", n=len(expired)))

        # 2. 排程与按计划时间投放乘客
        if self._pax_raw:
            self._schedule_raw()
        self._spawn_due(now)

        # 3. 派单
        for t, p in dispatcher.assign(self.taxis, self.passengers, now):
            route = self.gen.get_route(self.city.name, t.position, p.origin)
            if route:
                t.passenger = p
                p.assigned_taxi = t
                t.state = Taxi.TO_PASSENGER
                t.set_route(route["points"], target=p.origin)

        # 4. 推进出租车
        for t in self.taxis:
            self._step_taxi(t, dt, now)

        # 5. 统计
        if self._frame % 5 == 0:
            self.statsUpdated.emit(self._stats())

    def _schedule_raw(self):
        """主线程: 把原始条目按投放节奏排入计划队列(升序)。"""
        interval = max(0.5, self.config.spawn_interval)
        raw, self._pax_raw = self._pax_raw, []
        for lat, lng, dlat, dlng in raw:
            self._sched_cursor = max(self._sched_cursor, self._sim_time) + interval
            self._scheduled.append((self._sched_cursor, "q%d" % self._q_uid,
                                    lat, lng, dlat, dlng))
            self._q_uid += 1
        self._scheduled.sort(key=lambda e: e[0])

    def _spawn_due(self, now):
        cap = len(self.taxis) * MAX_ACTIVE_WAITING_FACTOR
        while (self._scheduled and self._scheduled[0][0] <= now
               and sum(1 for p in self.passengers
                       if p.state == Passenger.WAITING) < cap):
            _, _uid, lat, lng, dlat, dlng = self._scheduled.pop(0)
            p = Passenger(self._next_pid, (lat, lng), (dlat, dlng),
                          self.config.passenger_patience)
            self._next_pid += 1
            self.passengers.append(p)

    def _strat_for(self, t):
        """按策略类型归集统计; 不存在则建档。"""
        name = t.strategy.name if t.strategy else "none"
        if name not in self._strat_stats:
            self._strat_stats[name] = {"orders": 0, "income": 0.0,
                                       "empty": 0.0, "loaded": 0.0,
                                       "wait_total": 0.0, "wait_n": 0}
        return name

    def _ctx(self):
        return {"city": self.city, "history": self._history}

    def _history_cell(self, p):
        city = self.city
        gi = int((p[0] - (city.center[0] - city.span_deg / 2))
                 / city.span_deg * GRID_MAX)
        gj = int((p[1] - (city.center[1] - city.span_deg / 2))
                 / city.span_deg * GRID_MAX)
        if 0 <= gi < GRID_MAX and 0 <= gj < GRID_MAX:
            return (gi, gj)
        return None

    def _go_home(self, t):
        """下班收车: 规划回初始点路线, 取不到则原地停驻。"""
        route = self.gen.get_route(self.city.name, t.position, t.home)
        if route:
            t.state = Taxi.TO_HOME
            t.set_route(route["points"], target=t.home)
        else:
            t.clear_route()
            t.state = Taxi.OFF_DUTY
        s = self._strat_stats[self._strat_for(t)]
        self.logMessage.emit(translate("engine.clock_off", tid=t.tid))
        self.logMessage.emit(translate("engine.off_duty", tid=t.tid,
                                       orders=s["orders"], income=s["income"]))

    def _step_taxi(self, t, dt, now):
        s = self._strat_stats[self._strat_for(t)]
        if t.state == Taxi.CRUISING:
            if now >= t.off_at:              # 到下班时刻: 收车回家
                self._go_home(t)
            elif t.route:
                s["empty"] += dt             # 空驶巡游
                if t.advance(dt):
                    t.clear_route()
            else:
                # 选新巡游目标
                waiting_pos = [p.origin for p in self.passengers
                               if p.state == Passenger.WAITING]
                target = t.strategy.choose_target(self._pool, waiting_pos,
                                                  self._ctx())
                if target:
                    route = self.gen.get_route(self.city.name, t.position, target)
                    if route:
                        t.set_route(route["points"], target=target)
        elif t.state == Taxi.TO_PASSENGER:
            s["empty"] += dt                 # 接客空驶
            if t.advance(dt):
                p = t.passenger
                if p and p.state == Passenger.WAITING:
                    p.state = Passenger.ONBOARD
                    s["wait_total"] += p.wait_seconds(now)
                    s["wait_n"] += 1
                    t.state = Taxi.ONBOARD
                    # 上车即按起终点直线距离预估计价(显示"本单收益")
                    t.ride_income = calc_fare(
                        roads.deg_to_m(p.origin, p.dest),
                        self.config.fare_base, self.config.fare_base_km,
                        self.config.fare_per_km)
                    route = self.gen.get_route(self.city.name, p.origin, p.dest)
                    if route:
                        t.set_route(route["points"], target=p.dest)
                    else:
                        t.clear_route()
                        self._finish_ride(t, p)
        elif t.state == Taxi.ONBOARD:
            s["loaded"] += dt                # 载客
            if t.advance(dt) or not t.route:
                p = t.passenger
                if p:
                    self._finish_ride(t, p)
        elif t.state == Taxi.TO_HOME:        # 下班回程(不计入运营统计)
            if t.advance(dt):
                t.clear_route()
                t.state = Taxi.OFF_DUTY
                self.logMessage.emit(translate("engine.off_duty", tid=t.tid,
                                               orders=s["orders"],
                                               income=s["income"]))
        # OFF_DUTY: 停驻, 无动作

    def _finish_ride(self, t, p):
        if p in self.passengers:
            self.passengers.remove(p)
        t.passenger = None
        t.clear_route()
        dist_m = roads.deg_to_m(p.origin, p.dest)
        fare = calc_fare(dist_m, self.config.fare_base,
                         self.config.fare_base_km, self.config.fare_per_km)
        s = self._strat_stats[self._strat_for(t)]
        s["orders"] += 1
        s["income"] += fare
        t.income += fare
        t.ride_income = 0.0
        # 历史热力: 上车点网格计数(供 history 策略)
        cell = self._history_cell(p.origin)
        if cell:
            self._history[cell] = self._history.get(cell, 0) + 1
        t.idle_since = self._sim_time
        if self._sim_time >= t.off_at:   # 已到下班时刻: 送完这单就收车
            route = self.gen.get_route(self.city.name, t.position, t.home)
            if route:
                t.state = Taxi.TO_HOME
                t.set_route(route["points"], target=t.home)
            else:
                t.state = Taxi.OFF_DUTY
            self.logMessage.emit(translate("engine.clock_off", tid=t.tid))
            self.logMessage.emit(translate("engine.off_duty", tid=t.tid,
                                           orders=s["orders"], income=s["income"]))
        else:
            t.state = Taxi.CRUISING
        self.logMessage.emit(translate("engine.order_done", tid=t.tid,
                                       dist=dist_m))

    # ---------------- 状态输出(UI桥接) ----------------

    def snapshot_state(self):
        routes = {}
        for t in self.taxis:
            if t.route:
                # 任意状态都输出路线(巡游/接客/送客/回家), 折线抽稀控制体积
                routes[str(t.tid)] = t.route[::max(1, len(t.route) // 60)]
        # 乘客预告: 未来时间窗内的计划投放条目(灰色显示)
        now = self._sim_time
        pending = []
        for spawn_at, uid, lat, lng, dlat, dlng in self._scheduled:
            if spawn_at <= now:
                continue
            if spawn_at > now + PREVIEW_WINDOW or len(pending) >= PREVIEW_MAX:
                break
            pending.append({"id": uid, "lat": round(lat, 6),
                            "lng": round(lng, 6), "state": "pending",
                            "dest": [round(dlat, 6), round(dlng, 6)]})
        active = [{"id": p.pid, "lat": round(p.position[0], 6),
                   "lng": round(p.position[1], 6), "state": p.state,
                   "dest": [round(p.dest[0], 6), round(p.dest[1], 6)]}
                  for p in self.passengers if p.state != Passenger.DELIVERED]
        return {
            "taxis": [{"id": t.tid, "lat": round(t.position[0], 6),
                       "lng": round(t.position[1], 6), "state": t.state,
                       "income": round(t.income, 1),
                       "ride": round(t.ride_income, 1)}
                      for t in self.taxis],
            "passengers": pending + active,
            "routes": routes,
            "labels": {"today": translate("map.today"),
                       "ride": translate("map.ride")},
        }

    def _stats(self):
        waiting = sum(1 for p in self.passengers if p.state == Passenger.WAITING)
        busy = sum(1 for t in self.taxis
                   if t.state in (Taxi.TO_PASSENGER, Taxi.ONBOARD))
        strat_rows = []
        for name, s in self._strat_stats.items():
            taxis = sum(1 for t in self.taxis
                        if t.strategy and t.strategy.name == name)
            drive = s["empty"] + s["loaded"]
            strat_rows.append({
                "name": name, "taxis": taxis, "orders": s["orders"],
                "income": round(s["income"], 1),
                "empty_ratio": round(s["empty"] / drive, 2) if drive > 0 else 0.0,
                "avg_wait": round(s["wait_total"] / s["wait_n"], 1)
                if s["wait_n"] else 0.0,
            })
        empty_s = sum(s["empty"] for s in self._strat_stats.values())
        loaded_s = sum(s["loaded"] for s in self._strat_stats.values())
        wait_total = sum(s["wait_total"] for s in self._strat_stats.values())
        wait_count = sum(s["wait_n"] for s in self._strat_stats.values())
        drive_time = empty_s + loaded_s
        quota = self.manager.quota_snapshot()
        return {
            "sim_time": int(self._sim_time),
            "taxis": len(self.taxis),
            "busy": busy,
            "waiting": waiting,
            "avg_wait": round(wait_total / wait_count, 1) if wait_count else 0,
            "delivered": wait_count,
            "empty_ratio": round(empty_s / drive_time, 2) if drive_time > 0 else 0,
            "pool": store.pool_size(self.city.name),
            "strategies": strat_rows,
            "quota": quota,
        }
