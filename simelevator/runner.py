from __future__ import annotations

from core.models import Elevator, ElevatorPhase, SimConfig
from core.passenger import PassengerGenerator
from core.profile_generator import ProfileGenerator
from core.profiles import PassengerProfile
from core.simulator import Simulation
from algorithms import create_strategy

#: 有服务需求时单帧允许的最大楼层位移。速度越低这一帧的仿真时间越短，
#: 高帧率下几乎不会触发，作用是兜住卡顿时的瞬移。
MAX_FLOORS_PER_FRAME = 1.0
#: 无人且无任务时单帧推进的仿真秒数。
IDLE_MAX_STEP = 2.0
#: 空闲快进的倍率上限。60fps 下 2.0s/帧正好是 120 倍；高帧率下按此上限收敛，
#: 避免"帧越快、时间跑得越快"的失控放大。
MAX_IDLE_SCALE = 120.0
#: 无人时的子步长。没人等待，取整误差不影响任何统计指标。
IDLE_MAX_SUB_DT = 0.5

#: 这些阶段必然伴随有人上下梯或开关门，属于「有人看」的过程。
_DOOR_PHASES = (ElevatorPhase.OPENING, ElevatorPhase.OPEN, ElevatorPhase.CLOSING)


class ComparisonRunner:
    def __init__(self) -> None:
        self.config = SimConfig()
        self.keys: list[str] = []
        self.sims: dict[str, Simulation] = {}
        self.profiles: list[PassengerProfile] = []

    def configure(
        self,
        config: SimConfig,
        keys: list[str],
        profiles: list[PassengerProfile] | None = None,
    ) -> None:
        keys = list(dict.fromkeys(keys))
        profiles = profiles if profiles is not None else self.profiles
        if config == self.config and keys == self.keys and profiles == self.profiles:
            return
        self.config = config
        self.keys = keys
        self.profiles = list(profiles)
        self.reset()

    def _make_generator(self):
        if self.config.passenger_source == "profile":
            return ProfileGenerator(self.config, self.profiles)
        return PassengerGenerator(self.config)

    def reset(self) -> None:
        self.sims = {}
        for key in self.keys:
            self.sims[key] = Simulation(
                self.config, create_strategy(key), generator=self._make_generator()
            )

    def step(self, dt: float, max_sub_dt: float = 0.1) -> None:
        if dt <= 0.0 or not self.sims:
            return
        steps = max(1, int(dt / max_sub_dt) + 1)
        sub = dt / steps
        for _ in range(steps):
            for sim in self.sims.values():
                sim.step(sub)

    def is_busy(self) -> bool:
        """当前是否存在需要被观察的服务过程。

        空的轿厢在调度策略指挥下空驶回泊位不算忙——那种移动没有乘客在看，
        一旦算进去就永远触发不了快进。
        """
        for sim in self.sims.values():
            if sim.waiting_count() > 0:
                return True
            for e in sim.elevators:
                if e.passengers or e.calls or e.pickups:
                    return True
                if e.phase in _DOOR_PHASES:
                    return True
        return False

    def next_demand_time(self) -> float:
        """now 之后下一次出现乘客的时刻；无画像时返回无穷大。"""
        now = self.now
        times = [
            sim.generator.next_time(now)
            for sim in self.sims.values()
            if hasattr(sim.generator, "next_time")
        ]
        return min(times, default=float("inf"))

    def step_auto(self, real_dt: float, user_scale: float) -> float:
        """按忙闲状态自适应推进，返回本帧实际推进的仿真秒数。

        有人时把单帧楼层位移压到 MAX_FLOORS_PER_FRAME 以内，轿厢看起来是平滑
        移动的；没人时直接按 IDLE_MAX_STEP 快进，并不越过下一个乘客事件，
        因此乘客总是准时出现。这条分支不受 user_scale 限制：倍率选择框表达
        的是「有人时最多快到几倍」。
        """
        if real_dt <= 0.0 or not self.sims:
            return 0.0
        if self.is_busy():
            requested = real_dt * max(0.0, user_scale)
            if requested <= 0.0:
                return 0.0
            dt = min(requested, MAX_FLOORS_PER_FRAME / max(self.config.speed, 1e-9))
            self.step(dt, max_sub_dt=0.1)
            return dt
        until_event = self.next_demand_time() - self.now
        ceiling = min(IDLE_MAX_STEP, real_dt * MAX_IDLE_SCALE)
        if until_event > 0.0:
            dt = min(ceiling, until_event)
        else:
            dt = ceiling
        if dt <= 0.0:
            return 0.0
        self.step(dt, max_sub_dt=IDLE_MAX_SUB_DT)
        return dt

    def results(self) -> dict[str, dict[str, float]]:
        return {k: sim.metrics.snapshot() for k, sim in self.sims.items()}

    @property
    def now(self) -> float:
        if not self.sims:
            return 0.0
        return next(iter(self.sims.values())).now
