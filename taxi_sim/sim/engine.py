"""仿真引擎: QTimer 驱动的仿真时钟, 串联 乘客/出租车/巡游策略/派单/路线获取。"""
import logging
import threading

from PySide6.QtCore import QObject, QTimer, Signal

from i18n import t
from data import generator, store
from data import roads
from sim import dispatcher
from sim.city import get_city
from sim.passenger import Passenger
from sim.strategies import create as create_strategy
from sim.taxi import Taxi

log = logging.getLogger(__name__)

TICK_MS = 200          # 真实时钟帧间隔
MAX_ACTIVE_WAITING_FACTOR = 1.5   # 同时等待的乘客数上限(×出租车数)


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
        self._pax_queue = []       # 数据库预生成的乘客, 逐个投放
        self._pool = []
        self._next_pid = 1
        self._sim_time = 0.0
        self._spawn_acc = 0.0
        self._frame = 0
        self._pool_refresh_at = 0
        self._wait_total = 0.0
        self._wait_count = 0
        self._empty_seconds = 0.0
        self._loaded_seconds = 0.0
        self._seed_thread = None

    # ---------------- 生命周期 ----------------

    def start(self, n_taxis, strategies_mix):
        if not self.config.any_key:
            self.logMessage.emit(t("msg.config_incomplete"))
            return
        self.city = get_city(self.config.city)
        self._sim_time = 0.0
        self._spawn_acc = 0.0
        self._frame = 0
        self._wait_total = self._wait_count = 0
        self._empty_seconds = self._loaded_seconds = 0
        self.passengers.clear()

        # 立即用数据库已有数据生成出租车
        self._create_taxis(n_taxis, strategies_mix)

        # 差额补齐在后台线程进行(调SDK消耗配额, 不阻塞界面)
        self._seed_thread = threading.Thread(
            target=self._ensure_entities_bg,
            args=(self.config.passenger_count, n_taxis), daemon=True)
        self._seed_thread.start()

        self._refresh_pool()
        self._refill_queue()
        self.timer.start()
        self.logMessage.emit(t("engine.start", city=self.city.display_name,
                               n=len(self.taxis), strats=strategies_mix,
                               pax=self.config.passenger_count))

    def stop(self):
        self.timer.stop()

    def _create_taxis(self, n_taxis, strategies_mix):
        self.taxis.clear()
        rows = store.sample_taxis(self.city.name, n_taxis)
        while len(rows) < n_taxis:      # 库不足时用点池临时顶上
            p = store.random_pool_point(self.city.name)
            if not p:
                break
            rows.append((None, p[0], p[1]))
        for i, (_id, lat, lng) in enumerate(rows):
            strat_name = strategies_mix[i % len(strategies_mix)]
            t = Taxi(i, (lat, lng), None)
            t.strategy = create_strategy(strat_name, self.city.name, taxi=t)
            self.taxis.append(t)
        if not rows:
            self.logMessage.emit(t("engine.no_taxi_warn"))

    def _ensure_entities_bg(self, n_pax, n_taxis):
        def log_cb(msg):
            self.logMessage.emit(msg)
        try:
            self.gen.ensure_entities(self.city.name, n_pax, n_taxis, log_cb)
            self._refill_queue()
            self.logMessage.emit(t("engine.bg_done"))
        except Exception as e:  # 后台线程异常不能静默
            log.exception("后台实体生成失败")
            self.logMessage.emit(t("engine.bg_fail", err=e))

    # ---------------- 数据补充 ----------------

    def _refresh_pool(self):
        self._pool = store.sample_pool(self.city.name, 200)
        self._pool_refresh_at = self._sim_time

    def _refill_queue(self):
        rows = store.sample_passengers(self.city.name, 200)
        self._pax_queue = [(r[1], r[2], r[3], r[4]) for r in rows]  # lat,lng,dlat,dlng

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
            self.logMessage.emit(t("engine.passengers_expired", n=len(expired)))

        # 2. 投放新乘客
        self._spawn_acc += dt
        spawn_interval = max(0.5, self.config.spawn_interval)
        active_waiting = sum(1 for p in self.passengers
                             if p.state == Passenger.WAITING)
        while (self._spawn_acc >= spawn_interval
               and active_waiting < len(self.taxis) * MAX_ACTIVE_WAITING_FACTOR):
            self._spawn_acc -= spawn_interval
            if self._spawn_one_passenger():
                active_waiting += 1
            else:
                break

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

    def _spawn_one_passenger(self):
        if not self._pax_queue:
            self._refill_queue()
            if not self._pax_queue:
                return False
        lat, lng, dlat, dlng = self._pax_queue.pop()
        p = Passenger(self._next_pid, (lat, lng), (dlat, dlng),
                      self.config.passenger_patience)
        self._next_pid += 1
        self.passengers.append(p)
        return True

    def _step_taxi(self, t, dt, now):
        if t.state == Taxi.CRUISING:
            if t.route:
                self._empty_seconds += dt
                if t.advance(dt):
                    t.clear_route()
            else:
                # 选新巡游目标
                waiting_pos = [p.origin for p in self.passengers
                               if p.state == Passenger.WAITING]
                target = t.strategy.choose_target(self._pool, waiting_pos)
                if target:
                    route = self.gen.get_route(self.city.name, t.position, target)
                    if route:
                        t.set_route(route["points"], target=target)
        elif t.state == Taxi.TO_PASSENGER:
            self._empty_seconds += dt
            if t.advance(dt):
                p = t.passenger
                if p and p.state == Passenger.WAITING:
                    p.state = Passenger.ONBOARD
                    self._wait_total += p.wait_seconds(now)
                    self._wait_count += 1
                    t.state = Taxi.ONBOARD
                    route = self.gen.get_route(self.city.name, p.origin, p.dest)
                    if route:
                        t.set_route(route["points"], target=p.dest)
                    else:
                        t.clear_route()
                        self._finish_ride(t, p)
        elif t.state == Taxi.ONBOARD:
            self._loaded_seconds += dt
            if t.advance(dt) or not t.route:
                p = t.passenger
                if p:
                    self._finish_ride(t, p)

    def _finish_ride(self, t, p):
        if p in self.passengers:
            self.passengers.remove(p)
        t.passenger = None
        t.state = Taxi.CRUISING
        t.clear_route()
        t.idle_since = self._sim_time
        self.logMessage.emit(t("engine.order_done", tid=t.tid,
                               dist=roads.deg_to_m(p.origin, p.dest)))

    # ---------------- 状态输出(UI桥接) ----------------

    def snapshot_state(self):
        routes = {}
        for t in self.taxis:
            if t.state == Taxi.ONBOARD and t.route:
                # 折线抽稀, 控制消息体积
                routes[str(t.tid)] = t.route[::max(1, len(t.route) // 60)]
        return {
            "taxis": [{"id": t.tid, "lat": round(t.position[0], 6),
                       "lng": round(t.position[1], 6), "state": t.state}
                      for t in self.taxis],
            "passengers": [{"id": p.pid, "lat": round(p.position[0], 6),
                            "lng": round(p.position[1], 6),
                            "state": p.state}
                           for p in self.passengers
                           if p.state != Passenger.DELIVERED],
            "routes": routes,
        }

    def _stats(self):
        waiting = sum(1 for p in self.passengers if p.state == Passenger.WAITING)
        busy = sum(1 for t in self.taxis if t.state != Taxi.CRUISING)
        total = self._sim_time
        empty_ratio = (1 - (self._wait_count and 0 or 0)) if total == 0 else \
            max(0.0, 1 - (self._wait_count * 0))  # 占位, 真值在 busy ratio
        avg_wait = self._wait_total / self._wait_count if self._wait_count else 0
        drive_time = self._empty_seconds + self._loaded_seconds
        empty_ratio = self._empty_seconds / drive_time if drive_time > 0 else 0
        quota = self.manager.quota_snapshot()
        return {
            "sim_time": int(total),
            "taxis": len(self.taxis),
            "busy": busy,
            "waiting": waiting,
            "avg_wait": round(avg_wait, 1),
            "delivered": self._wait_count,
            "empty_ratio": round(empty_ratio, 2),
            "pool": store.pool_size(self.city.name),
            "quota": quota,
        }
