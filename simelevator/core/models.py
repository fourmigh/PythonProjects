from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

#: 缺省人群分类。仿真内核不认识四类人群的差异（策略也不读它），
#: 这个值只用于无法判定时的兜底。
DEFAULT_PEOPLE_KIND = "male"


class PassengerState(Enum):
    WAITING = auto()
    RIDING = auto()
    DONE = auto()
    ABANDONED = auto()


@dataclass
class Passenger:
    pid: int
    origin: int
    dest: int
    arrive_time: float
    board_time: float | None = None
    done_time: float | None = None
    state: PassengerState = PassengerState.WAITING
    elevator_id: int | None = None
    deadline: float | None = None
    #: 男/女/儿童/轮椅。仅供界面画图，任何调度策略都不读它
    gender: str = DEFAULT_PEOPLE_KIND

    @property
    def dir(self) -> int:
        return 1 if self.dest > self.origin else -1

    @property
    def wait_time(self) -> float:
        if self.board_time is None:
            return 0.0
        return self.board_time - self.arrive_time


class ElevatorPhase(Enum):
    IDLE = auto()
    MOVING = auto()
    OPENING = auto()
    OPEN = auto()
    CLOSING = auto()


@dataclass
class Elevator:
    eid: int
    floor: float
    phase: ElevatorPhase = ElevatorPhase.IDLE
    direction: int = 0
    door: float = 0.0
    passengers: list[Passenger] = field(default_factory=list)
    calls: set[int] = field(default_factory=set)
    pickups: set[tuple[int, int]] = field(default_factory=set)
    park_target: int | None = None
    idle_time: float = 0.0
    open_elapsed: float = 0.0
    dwell_elapsed: float = 0.0
    board_cooldown: float = 0.0
    served_pickups: set[tuple[int, int]] = field(default_factory=set)

    @property
    def is_idle(self) -> bool:
        return (
            self.phase == ElevatorPhase.IDLE
            and not self.passengers
            and not self.calls
            and not self.pickups
        )

    @property
    def target_floor_int(self) -> int:
        return int(round(self.floor))


@dataclass
class HallCall:
    floor: int
    dir: int
    assigned_to: int | None = None


@dataclass
class SimConfig:
    floors: int = 12
    elevators: int = 3
    speed: float = 2.0
    door_time: float = 1.0
    boarding_time: float = 0.8
    alighting_time: float = 0.6
    min_door_open: float = 1.0
    arrival_rate: float = 6.0
    origin_mode: str = "uniform"
    dest_mode: str = "uniform"
    lobby_share: float = 0.6
    dest_lobby_share: float = 0.7
    custom_origin_weights: str = ""
    custom_dest_weights: str = ""
    seed: int = 42
    idle_park_delay: float = 1.0
    energy_weight: float = 0.3
    history_window: float = 300.0
    start_time_min: int = 7 * 60
    start_weekday: int = 1
    passenger_source: str = "random"
    allow_abandon: bool = True

    def normalized(self) -> SimConfig:
        cfg = SimConfig(**{k: v for k, v in self.__dict__.items()})
        cfg.floors = max(2, int(cfg.floors))
        cfg.elevators = max(1, int(cfg.elevators))
        cfg.speed = max(0.1, float(cfg.speed))
        cfg.door_time = max(0.0, float(cfg.door_time))
        cfg.boarding_time = max(0.0, float(cfg.boarding_time))
        cfg.alighting_time = max(0.0, float(cfg.alighting_time))
        cfg.min_door_open = max(0.0, float(cfg.min_door_open))
        cfg.arrival_rate = max(0.0, float(cfg.arrival_rate))
        cfg.lobby_share = min(0.95, max(0.0, float(cfg.lobby_share)))
        cfg.dest_lobby_share = min(0.95, max(0.0, float(cfg.dest_lobby_share)))
        cfg.idle_park_delay = max(0.0, float(cfg.idle_park_delay))
        cfg.energy_weight = min(1.0, max(0.0, float(cfg.energy_weight)))
        cfg.history_window = max(10.0, float(cfg.history_window))
        cfg.start_time_min = int(cfg.start_time_min) % 1440
        cfg.start_weekday = min(7, max(1, int(cfg.start_weekday)))
        return cfg
